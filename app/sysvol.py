# -*- coding: utf-8 -*-
"""读 Windows 主音量（0.0–1.0），供桌宠把自己的音量跟系统音量对齐。

用 pycaw（WASAPI）读一次约 10ms；结果缓存 3 秒，避免每帧都去问系统。
拿不到时返回 1.0（表示"不额外压低"），不影响播放。
"""
import threading
import time

_lock = threading.Lock()
_cache = {"t": 0.0, "v": 1.0, "ok": False}


def master_volume() -> float:
    """系统主音量 0.0–1.0；静音时返回 0.0；读不到返回 1.0。"""
    now = time.time()
    with _lock:
        if now - _cache["t"] < 3.0:
            return _cache["v"]
        v, ok = 1.0, False
        try:
            from pycaw.pycaw import AudioUtilities  # noqa: PLC0415

            iface = AudioUtilities.GetSpeakers().EndpointVolume
            muted = bool(iface.GetMute())
            v = 0.0 if muted else round(float(iface.GetMasterVolumeLevelScalar()), 3)
            ok = True
        except Exception:  # noqa: BLE001
            v, ok = 1.0, False
        _cache.update({"t": now, "v": v, "ok": ok})
        return v


def last_ok() -> bool:
    return bool(_cache["ok"])
