# -*- coding: utf-8 -*-
"""方言语音合成：Edge TTS 联网合成 -> 落盘缓存 -> 本地播放。

缓存目录在账号目录下 tts_cache/，以「音色+语速+音调+文本」的哈希命名，
同一句话第二次说就直接用本地文件，不再联网。
"""
import asyncio
import hashlib
import os

from PySide6.QtCore import QThread, Signal, QTimer

from paths import account_dir

_CACHE_EXT = ".mp3"


def cache_dir() -> str:
    d = os.path.join(account_dir(), "tts_cache")
    os.makedirs(d, exist_ok=True)
    return d


def cache_key(text: str, voice: str, rate: int, pitch: int) -> str:
    raw = f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:24] + _CACHE_EXT


def cached_path(text: str, voice: str, rate: int, pitch: int) -> str:
    p = os.path.join(cache_dir(), cache_key(text, voice, rate, pitch))
    return p if os.path.exists(p) and os.path.getsize(p) > 2000 else ""


async def _synth(text: str, voice: str, rate: int, pitch: int, dst: str):
    import edge_tts
    # 音量不交给 Edge：同一句话用 100/70/40 三种 volume 合成，返回的 mp3 字节数完全一致
    # （实测 23616 三次相同），看不出幅度差别，所以音量统一改由播放端 QAudioOutput 控制。
    communicate = edge_tts.Communicate(
        text, voice, rate=f"{rate:+d}%", pitch=f"{pitch:+d}Hz")
    await communicate.save(dst)


def synth(text: str, voice: str, rate: int = 0, pitch: int = 0) -> str:
    """同步合成（需在非 GUI 线程或独立事件循环中调用），返回文件路径。"""
    hit = cached_path(text, voice, rate, pitch)
    if hit:
        return hit
    dst = os.path.join(cache_dir(), cache_key(text, voice, rate, pitch))
    tmp = dst + ".part"
    try:
        asyncio.run(_synth(text, voice, rate, pitch, tmp))
        if os.path.getsize(tmp) < 2000:
            raise RuntimeError("audio too small")
        os.replace(tmp, dst)
        return dst
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


class SynthWorker(QThread):
    """后台合成，避免阻塞界面。"""
    done = Signal(str, str)      # (play_id, 文件路径)
    failed = Signal(str, str)    # (play_id, 原因)

    def __init__(self, text: str, voice: str, rate: int, pitch: int, play_id: str):
        super().__init__()
        self.text = text
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.play_id = play_id
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if self._stop:
            return
        try:
            path = synth(self.text, self.voice, self.rate, self.pitch)
            self.done.emit(self.play_id, path)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(self.play_id, str(e)[:120])


class TTSService:
    """串行合成：同一时刻只保留最新的一条待合成，旧的直接丢弃。"""

    def __init__(self, config: dict, audio):
        self.config = config
        self.audio = audio
        self._worker = None
        self._pending = []
        self._prios = {}
        self._vols = {}
        self._seq = 0
        self.last_error = ""
        self.speak_count = 0

    # ---------- 配置 ----------
    def is_enabled(self) -> bool:
        return bool(self.config.get("tts_on", True)) and bool(self.config.get("tts_online", True))

    def set_enabled(self, on: bool):
        self.config["tts_on"] = bool(on)

    # ---------- 主入口 ----------
    def say(self, text: str, persona: dict, emotion_hint: dict = None, force: bool = False,
            priority: int = 1) -> bool:
        """priority：喂食/拍拍 2 > 对话回复 1 > 闲聊/自主 0（高优先级可打断低优先级）。"""
        text = (text or "").strip()
        if not text:
            return False
        if not force and not self.is_enabled():
            return False
        hint = emotion_hint or {}
        voice = persona.get("voice", "zh-CN-XiaoxiaoNeural")
        rate = int(persona.get("rate", 0)) + int(hint.get("rate_pct", 0))
        # 真人音色提炼：config["voice_profile"] 为 jingjing/linluo 时，pitch 由映射表直接
        # 反解（以目标基频为准），不再叠加人设自带的 pitch —— 叠加会过冲（实测 +38 冲到 400Hz）
        prof = str(self.config.get("voice_profile", "") or "")
        pitch = int(persona.get("pitch", 0)) + int(hint.get("pitch_hz", 0))
        if prof and prof != "off":
            try:
                import voice_profile
                pitch = voice_profile.pitch_for(voice, prof)[0] + int(hint.get("pitch_hz", 0))
            except Exception:
                pass
        rate = max(-40, min(40, rate))
        # Edge 的 pitch 名义值上限约 ±150，实测饱和点在 +60~+90，这里放宽到 ±120
        pitch = max(-120, min(120, pitch))
        volume = max(10, min(100, int(persona.get("volume", 100) or 100)))

        hit = cached_path(text, voice, rate, pitch)
        if hit:
            return self.audio.play_file(hit, priority, volume, speech=True)

        self._seq += 1
        play_id = str(self._seq)
        if self._worker is not None and self._worker.isRunning():
            # 排队而不是覆盖：覆盖会让连续说话时中间那句永远不出声
            self._pending.append((text, voice, rate, pitch, play_id, priority, volume))
            return True
        self._start(text, voice, rate, pitch, play_id, priority, volume)
        return True

    def _start(self, text, voice, rate, pitch, play_id, priority=1, volume=100):
        self._prios[play_id] = priority
        self._vols[play_id] = volume
        self._worker = SynthWorker(text, voice, rate, pitch, play_id)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_done(self, play_id: str, path: str):
        # 先播这一句（旧逻辑在这里丢弃当前音频，只留 pending，结果连续说话只有第一句有声音）
        prio = self._prios.pop(play_id, 1)
        vol = self._vols.pop(play_id, 100)
        if self.audio.play_file(path, prio, vol, speech=True):
            self.speak_count += 1
        if self._pending:
            nxt = self._pending.pop(0)
            # 等这句播完再合成下一句，避免 play_file 的 stop() 把它掐断
            ms = int(420 + 260 * len(nxt[0]))
            QTimer.singleShot(ms, lambda: self._start(*nxt))

    def _on_failed(self, play_id: str, reason: str):
        self.last_error = reason
        if self._pending:
            nxt = self._pending.pop(0)
            self._start(*nxt)

    # ---------- 管理 ----------
    def clear_cache(self) -> int:
        n = 0
        for name in os.listdir(cache_dir()):
            p = os.path.join(cache_dir(), name)
            try:
                if os.path.isfile(p):
                    os.remove(p)
                    n += 1
            except OSError:
                pass
        return n
