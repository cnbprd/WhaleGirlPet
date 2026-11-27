# -*- coding: utf-8 -*-
"""v3.2 2D asset bridge: manifest lookup + localhost card packets.

The 3D core already has a localhost UDP bus for emotion parameters.  This
module adds one backward-compatible field pair:

    "card": "expression/happy"
    "card_ttl_ms": 1800

A renderer that does not know about cards ignores the extra keys.  The future
sprite layer reads the atlas manifest and draws the named rect.  No file path
from the wire is ever opened; `card` must match a manifest id.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import emotion_bridge as emo

P_ACTION = 3
P_EXPRESSION = 2
P_UI = 1

# Group mapping is deliberately small.  The renderer owns the actual visual
# card; this layer only translates 2D semantic names to manifest ids.
EMOTION_FOR_CARD = {
    "expression/idle": "neutral",
    "expression/eat": "happy",
    "expression/happy": "happy",
    "expression/walk": "neutral",
    "expression/sleep": "tired",
    "expression/sleepy": "tired",
    "expression/shy": "shy",
    "expression/angry": "angry",
    "expression/curious": "curious",
    "expression/pat": "happy",
}


@dataclass(frozen=True)
class Card:
    id: str
    group: str
    name: str
    source: str
    rect: tuple[int, int, int, int]
    slot: tuple[int, int, int, int]


@dataclass
class CardSignal:
    card: str
    priority: int
    ttl_ms: int
    source: str
    expires_at: float


class CardArbiter:
    """Small local arbiter so an auto expression cannot cut off a user action.

    The renderer still owns TTL display; this only prevents lower-priority
    packets from overwriting the active higher-priority card.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._current: Optional[CardSignal] = None

    def clear(self):
        self._current = None

    def current(self) -> Optional[CardSignal]:
        if self._current is not None and self._current.expires_at <= self._clock():
            self._current = None
        return self._current

    def submit(self, card: str, priority: int, ttl_ms: int, source: str) -> bool:
        now = self._clock()
        current = self.current()
        if current is not None and priority < current.priority:
            return False
        self._current = CardSignal(
            card=card,
            priority=max(0, min(9, int(priority))),
            ttl_ms=max(200, min(10000, int(ttl_ms))),
            source=source,
            expires_at=now + max(0.2, min(10.0, ttl_ms / 1000.0)),
        )
        return True



def _default_manifest() -> Path:
    try:
        import paths  # type: ignore

        return Path(paths.asset_path("2d_bridge/manifest.json"))
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[1] / "assets/2d_bridge/manifest.json"


def load_cards(manifest_path: Optional[Path] = None) -> dict[str, Card]:
    path = Path(manifest_path) if manifest_path else _default_manifest()
    data = json.loads(path.read_text(encoding="utf-8"))
    sheet_w, sheet_h = (int(v) for v in data["sheet_size"])
    cards: dict[str, Card] = {}
    for entry in data.get("cards", []):
        cid = str(entry["id"])
        rect = tuple(int(v) for v in entry["rect"])
        slot = tuple(int(v) for v in entry["slot"])
        if len(rect) != 4 or len(slot) != 4:
            raise ValueError(f"bad rect for {cid}")
        if rect[0] < 0 or rect[1] < 0 or rect[0] + rect[2] > sheet_w or rect[1] + rect[3] > sheet_h:
            raise ValueError(f"card outside atlas: {cid} {rect}")
        if cid in cards:
            raise ValueError(f"duplicate card id: {cid}")
        cards[cid] = Card(cid, str(entry.get("group", "")), str(entry.get("name", "")),
                          str(entry.get("source", "")), rect, slot)
    if not cards:
        raise ValueError("atlas manifest has no cards")
    return cards


class AssetBridge:
    """Best-effort sender; a missing 3D process costs one sendto."""

    def __init__(self, host: str = emo.DEFAULT_HOST, port: Optional[int] = None,
                 enabled: Optional[bool] = None, manifest_path: Optional[Path] = None,
                 clock=time.monotonic):
        if enabled is None:
            enabled = os.environ.get("WHALE3D_ASSET_BRIDGE", "1").lower() not in (
                "0", "false", "no", "off")
        self.manifest_error = ""
        try:
            self.cards = load_cards(manifest_path)
        except Exception as exc:  # noqa: BLE001
            self.cards = {}
            self.manifest_error = f"{type(exc).__name__}: {exc}"
            enabled = False
        self.enabled = bool(enabled)
        self.arbiter = CardArbiter(clock=clock)
        self.sender = emo.UdpSender(
            host=host,
            port=port or int(os.environ.get("WHALE3D_EMOTION_PORT", emo.DEFAULT_PORT)),
            enabled=self.enabled,
        )
        self.last_card: Optional[str] = None

    def close(self):
        self.sender.close()

    def send_card(self, card_id: str, ttl_ms: int = 1800,
                  source: str = "P_2D", emotion: Optional[str] = None,
                  priority: int = P_EXPRESSION) -> bool:
        if card_id not in self.cards:
            return False
        ttl = max(200, min(10000, int(ttl_ms)))
        if not self.arbiter.submit(card_id, priority, ttl, source):
            return False
        payload = {
            "emotion": emotion or EMOTION_FOR_CARD.get(card_id, "neutral"),
            "intensity": 0.7,
            "source": source,
            "card": card_id,
            "card_ttl_ms": ttl,
        }
        if not self.sender.send_payload(payload):
            return False
        self.last_card = card_id
        return True

    def expression(self, name: str, ttl_ms: int = 1800,
                   source: str = "P_2D") -> bool:
        return self.send_card(f"expression/{name}", ttl_ms=ttl_ms, source=source,
                              priority=P_EXPRESSION)

    def action(self, name: str, ttl_ms: int = 2600,
               source: str = "P_2D", priority: int = P_ACTION) -> bool:
        return self.send_card(f"action/{name}", ttl_ms=ttl_ms, source=source,
                              priority=priority)

    def describe(self) -> dict:
        current = self.arbiter.current()
        return {
            "enabled": self.enabled,
            "cards": len(self.cards),
            "groups": sorted({c.group for c in self.cards.values()}),
            "last_card": self.last_card,
            "current": current.card if current else None,
            "error": self.manifest_error,
        }
