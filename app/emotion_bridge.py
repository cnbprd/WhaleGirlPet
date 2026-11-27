# -*- coding: utf-8 -*-
"""v3.2 step 2: Python-side emotion signals -> 3D UDP bus.

The 3D renderer only understands a small vocabulary (happy/sad/angry/tired/
curious/neutral). This module keeps the production and arbitration policy in
the Python process so the renderer stays a dumb, local consumer.

Priority:
    P_USER  3  explicit user wording ("笑一个", "别难过")
    P_LLM   2  an emotion tag emitted by the chat model, or a conservative
               fallback read from the final reply text
    P_AUTO  1  the existing EmotionState / expression hint

A higher-priority signal masks lower ones until its TTL expires. When the
current signal changes, a single UDP datagram is sent; lower-priority packets
are not allowed to overwrite an active higher-priority face.
"""
from __future__ import annotations

import json
import os
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Optional

P_USER = 3
P_LLM = 2
P_AUTO = 1

DEFAULT_PORT = 47832
DEFAULT_HOST = "127.0.0.1"
# v3.2 step 4: renderer-side intensity envelope. Python only sends the
# parameters; the 3D process owns the actual interpolation.
ATTACK_MS = 180
RELEASE_MS = 420

# v3.2 asset bridge: keep the old renderer compatible. The 3D process may
# ignore `card`; the sprite layer can consume it later.
CARD_FOR_EMOTION = {
    "happy": "expression/happy",
    "angry": "expression/angry",
    "curious": "expression/curious",
    "shy": "expression/shy",
    "tired": "expression/sleepy",
    "neutral": "expression/idle",
}

# These are renderer-side names, not the eight EmotionState dimensions.
RENDER_EMOTIONS = {
    "happy", "joy", "excited", "smile", "laugh",
    "curious", "thinking", "interested",
    "neutral", "calm", "idle",
    "sad", "angry", "tired", "sleepy", "bored",
}

TAG_RE = re.compile(
    r"\[\[\s*emo(?:tion)?\s*:\s*([a-zA-Z_]+)\s*(?::\s*([0-9]*\.?[0-9]+))?\s*\]\]",
    re.I,
)


@dataclass
class Signal:
    emotion: str
    intensity: float
    source: str
    priority: int
    ttl: float
    expires_at: float = field(default=0.0)
    # Optional 2D card. Empty means emotion-only; the renderer must not
    # require this field.
    card: str = ""
    card_ttl_ms: int = 1800


class Arbiter:
    """Small deterministic priority arbiter; no threads, no external deps."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._signals: list[Signal] = []

    def clear(self):
        self._signals.clear()

    def submit(self, emotion: str, intensity: float, source: str,
               priority: int, ttl: float) -> Optional[Signal]:
        emotion = (emotion or "").strip().lower()
        if emotion not in RENDER_EMOTIONS:
            return None
        intensity = max(0.0, min(1.0, float(intensity)))
        now = self._clock()
        self._signals = [s for s in self._signals if s.expires_at > now]
        signal = Signal(emotion, intensity, source, priority, max(0.05, ttl),
                        now + max(0.05, ttl))
        # Same source: newer wins. Different source: keep both until expiry.
        self._signals = [s for s in self._signals if s.source != source]
        self._signals.append(signal)
        return signal

    def current(self) -> Optional[Signal]:
        now = self._clock()
        self._signals = [s for s in self._signals if s.expires_at > now]
        if not self._signals:
            return None
        # Highest priority wins; among equals, the newest submission wins.
        return max(self._signals, key=lambda s: (s.priority, s.expires_at))


def payload_for(signal: Signal) -> dict:
    """Wire payload shared by the real sender and tests."""
    payload = {
        "emotion": signal.emotion,
        "intensity": round(signal.intensity, 3),
        "source": signal.source,
        "curve": {"attack_ms": ATTACK_MS, "release_ms": RELEASE_MS},
    }
    if signal.card:
        payload["card"] = signal.card
        payload["card_ttl_ms"] = int(signal.card_ttl_ms)
    return payload


class UdpSender:
    """Best-effort localhost sender. A missing 3D process costs one sendto."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 enabled: Optional[bool] = None):
        if enabled is None:
            enabled = os.environ.get("WHALE3D_EMOTION_BRIDGE", "1").lower() not in (
                "0", "false", "no", "off")
        self.host = host
        self.port = int(port)
        self.enabled = bool(enabled)
        self._sock: Optional[socket.socket] = None
        if self.enabled:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except OSError:
                self.enabled = False
                self._sock = None

    def send_payload(self, payload: dict) -> bool:
        if not self.enabled or self._sock is None:
            return False
        data = json.dumps(payload, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
        try:
            self._sock.sendto(data, (self.host, self.port))
            return True
        except OSError:
            return False

    def send(self, signal: Signal) -> bool:
        return self.send_payload(payload_for(signal))

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


def parse_tag(text: str) -> Optional[tuple[str, float]]:
    """Read the optional [[emo:happy:0.7]] marker emitted by the model."""
    m = TAG_RE.search(text or "")
    if not m:
        return None
    emotion = m.group(1).lower()
    if emotion not in RENDER_EMOTIONS:
        return None
    try:
        intensity = float(m.group(2)) if m.group(2) else 0.7
    except ValueError:
        intensity = 0.7
    return emotion, max(0.0, min(1.0, intensity))


def strip_tag(text: str) -> str:
    """Remove the hidden marker before the reply reaches bubble/TTS."""
    return TAG_RE.sub("", text or "").strip()


# Conservative keyword fallback. It is only P_LLM-level evidence, never used
# to override an explicit user request.
_LLM_CUES = (
    ("happy", ("开心", "高兴", "笑", "喜欢", "太棒", "好棒", "哈哈", "嘿嘿", "亲亲", "抱抱")),
    ("sad", ("难过", "伤心", "失落", "委屈", "想哭", "唉")),
    ("angry", ("生气", "气死", "讨厌", "烦", "哼", "坏蛋")),
    ("tired", ("累", "困", "没力气", "想睡")),
    ("curious", ("好奇", "想知道", "为什么", "看看")),
)


def infer_from_text(text: str) -> Optional[tuple[str, float]]:
    t = str(text or "")
    for emotion, cues in _LLM_CUES:
        if any(cue in t for cue in cues):
            return emotion, 0.65
    return None


# Explicit user wording gets P_USER. Keep this small and predictable: it is a
# command layer, not a general sentiment classifier.
_USER_CUES = (
    ("happy", 0.90, ("笑一个", "笑一下", "开心点", "开心一点", "高兴点", "高兴一点",
                     "别难过", "乐一个")),
    ("sad", 0.80, ("难过", "伤心", "失落", "委屈", "想哭")),
    ("angry", 0.80, ("生气", "气死", "哼", "讨厌")),
    ("tired", 0.75, ("好累", "困了", "没力气", "想睡")),
    ("neutral", 0.00, ("别笑", "正常点", "冷静点", "严肃点")),
)


def infer_user(text: str) -> Optional[tuple[str, float]]:
    t = str(text or "")
    for emotion, intensity, cues in _USER_CUES:
        if any(cue in t for cue in cues):
            return emotion, intensity
    return None


# State hint -> renderer vocabulary. This is the P_AUTO layer.
_AUTO_MAP = {
    "happy": "happy",
    "sleepy": "tired",
    "curious": "curious",
    "shy": "shy",
    "sleep": "tired",
    "idle": "neutral",
}


class EmotionBridge:
    """Connects the existing EmotionState and chat pipeline to the 3D bus."""

    def __init__(self, enabled: Optional[bool] = None, port: Optional[int] = None,
                 clock=time.monotonic):
        if enabled is None:
            enabled = os.environ.get("WHALE3D_EMOTION_BRIDGE", "1").lower() not in (
                "0", "false", "no", "off")
        self.enabled = bool(enabled)
        self._clock = clock
        self.arbiter = Arbiter(clock=clock)
        self.sender = UdpSender(port=port or int(os.environ.get("WHALE3D_EMOTION_PORT", DEFAULT_PORT)),
                                enabled=self.enabled)
        self.last_emitted: Optional[Signal] = None
        self.last_llm: Optional[Signal] = None
        self.card_hold_until = 0.0

    def close(self):
        self.sender.close()

    def hold_cards(self, seconds: float):
        """Suppress auto emotion cards while a user/action card owns the layer."""
        self.card_hold_until = max(
            self.card_hold_until,
            self._clock() + max(0.0, min(10.0, float(seconds))),
        )

    def _submit_and_emit(self, emotion: str, intensity: float, source: str,
                         priority: int, ttl: float) -> Optional[Signal]:
        if not self.enabled:
            return None
        before = self.arbiter.current()
        submitted = self.arbiter.submit(emotion, intensity, source, priority, ttl)
        if submitted is None:
            return None
        after = self.arbiter.current()
        if after is None:
            return None
        changed = (before is None or before.source != after.source or
                   before.emotion != after.emotion or
                   abs(before.intensity - after.intensity) >= 0.05)
        if changed:
            if not after.card and self._clock() >= self.card_hold_until:
                after.card = CARD_FOR_EMOTION.get(after.emotion, "")
            self.sender.send(after)
            self.last_emitted = after
        return after

    def user_text(self, text: str) -> Optional[Signal]:
        """Explicit user wording -> P_USER, 8 s."""
        found = infer_user(text)
        if found is None:
            return None
        return self._submit_and_emit(found[0], found[1], "P_USER", P_USER, 8.0)

    def llm_reply(self, text: str) -> Optional[Signal]:
        """Model tag first; fallback to reply text -> P_LLM, 4 s."""
        found = parse_tag(text)
        if found is None:
            found = infer_from_text(text)
        if found is None:
            return None
        signal = self._submit_and_emit(found[0], found[1], "P_LLM", P_LLM, 4.0)
        if signal is not None:
            self.last_llm = signal
        return signal

    def tts_active(self, active: bool) -> Optional[Signal]:
        """Keep the reply emotion alive while TTS is actually speaking.

        The normal P_LLM TTL is 4 s; a spoken reply can easily be longer. The
        audio layer calls this on real playback start/stop, so the face does
        not fall back to P_AUTO halfway through a sentence. This is a TTL
        extension, not a new priority level.
        """
        if not self.enabled or self.last_llm is None:
            return None
        ttl = 30.0 if active else 4.0
        return self._submit_and_emit(
            self.last_llm.emotion, self.last_llm.intensity, "P_LLM", P_LLM, ttl)

    def auto_state(self, emotion_state) -> Optional[Signal]:
        """Existing expression hint -> P_AUTO, 12 s."""
        if emotion_state is None:
            return None
        try:
            hint = emotion_state.expression_hint()
            mood = float(emotion_state.mood_score())
        except Exception:  # noqa: BLE001
            return None
        emotion = _AUTO_MAP.get(hint)
        if emotion is None:
            return None
        intensity = max(0.15, min(0.85, 0.25 + mood / 100.0 * 0.5))
        return self._submit_and_emit(emotion, intensity, "P_AUTO", P_AUTO, 12.0)
