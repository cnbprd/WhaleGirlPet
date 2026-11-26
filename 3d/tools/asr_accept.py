#!/usr/bin/env python3
"""ASR -> emotion bridge -> 3D 真实窗口验收。

先识别一段 SAPI 合成 WAV，再把识别文本喂给 `EmotionBridge.user_text`，
由它发 UDP 给运行中的 3D 窗口，截 neutral / happy 两帧算全窗 RGB 差。
不验证声学模型准确率，只验证“文本进来后 3D 表情动了”。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT.parent / "app"
BUILD = ROOT.parent / "build"
DOCS = ROOT.parent / "docs"
WAV = BUILD / "asr_emotion.wav"
LOG = ROOT / "asr_accept.err.log"
TRACE = ROOT / "asr_accept_trace.log"
user32 = ctypes.windll.user32
WM_CLOSE = 0x0010

sys.path.insert(0, str(APP))
import emotion_bridge as eb  # noqa: E402
import voice_cmd  # noqa: E402


def find_window(timeout: float = 12.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = user32.FindWindowW(None, "鲸鱼娘")
        if hwnd:
            return hwnd
        time.sleep(0.15)
    return 0


def capture(hwnd: int, path: Path) -> Image.Image:
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    image = ImageGrab.grab(
        bbox=(rect.left, rect.top, rect.right, rect.bottom)
    ).convert("RGB")
    image.save(path)
    return image


def mean_delta(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    total = sum(value * count for value, count in enumerate(hist[:256]))
    return total / (a.width * a.height * 3)


def main() -> int:
    if not WAV.exists():
        raise RuntimeError(f"missing WAV: {WAV}")
    rec = voice_cmd.recognize(wav_path=str(WAV), wait_s=1, timeout_s=20)
    print("asr:", rec)
    if not rec.get("ok") or not rec.get("text"):
        raise RuntimeError(f"ASR failed: {rec}")

    env = os.environ.copy()
    env["WHALE3D_FACE"] = "auto"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_FREEZE"] = "1"
    env["WHALE3D_EMOTION_TRACE"] = "1"
    env["WHALE3D_LOG"] = str(TRACE)
    log = open(LOG, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [str(ROOT / "whale3d.exe")],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=log,
    )
    bridge = eb.EmotionBridge(enabled=True)
    try:
        hwnd = find_window()
        if not hwnd:
            raise RuntimeError("3D window not found")
        time.sleep(1.0)
        neutral = capture(hwnd, DOCS / "_3d_asr_neutral.png")
        sig = bridge.user_text(rec["text"])
        print("bridge_signal:", sig)
        if sig is None:
            raise RuntimeError("ASR text did not map to an emotion")
        time.sleep(0.8)
        happy = capture(hwnd, DOCS / "_3d_asr_happy.png")
        delta = mean_delta(neutral, happy)
        print("mean_rgb_neutral_to_happy:", round(delta, 3))
        if delta < 0.1:
            raise RuntimeError(f"3D face did not visibly change: {delta}")
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=3)
        print("asr_3d_ok text=%r emotion=%s delta=%.3f" % (
            rec["text"], sig.emotion, delta))
    finally:
        bridge.close()
        if proc.poll() is None:
            proc.terminate()
        log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
