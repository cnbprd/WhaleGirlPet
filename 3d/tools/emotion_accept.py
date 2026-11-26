#!/usr/bin/env python3
"""Visual acceptance for v3.2 step 1/1b/4 (emotion bus -> face -> envelope).

Run with the repo venv:
    python 3d/tools/emotion_accept.py

It launches the 3D shell with a forced open face, captures neutral, sends
{"emotion":"happy","intensity":0.8,"curve":{"attack_ms":180,"release_ms":420}}
to 127.0.0.1:47832, captures the 60 ms cross-fade, full smile, release and
return-to-neutral frames, and writes them under docs/.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import socket
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent / "docs"
user32 = ctypes.windll.user32
WM_CLOSE = 0x0010


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


def send(emotion: str, intensity: float, source: str = "acceptance",
         attack_ms: int = 180, release_ms: int = 420) -> None:
    payload = {
        "emotion": emotion,
        "intensity": intensity,
        "source": source,
        "curve": {"attack_ms": attack_ms, "release_ms": release_ms},
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(
            json.dumps(payload).encode("utf-8"), ("127.0.0.1", 47832)
        )
    finally:
        sock.close()
    print("sent", payload)


def mean_delta(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    total = sum(value * count for value, count in enumerate(hist[:256]))
    return total / (a.width * a.height * 3)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["WHALE3D_FACE"] = "open"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_FREEZE"] = "1"
    env["WHALE3D_EMOTION_TRACE"] = "1"
    env["WHALE3D_LOG"] = str(ROOT / "emotion_accept_trace.log")
    log_path = ROOT / "emotion_accept.err.log"
    log = open(log_path, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [str(ROOT / "whale3d.exe")],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=log,
    )
    try:
        hwnd = find_window()
        if not hwnd:
            raise RuntimeError("3D window not found")
        time.sleep(0.8)
        neutral = capture(hwnd, DOCS / "_3d_emotion_neutral.png")
        send("happy", 0.8)
        # v3.2 step 1b: the face atlas now cross-fades over 0.16 s. Sample
        # mid-transition as evidence that this is not a hard frame swap.
        time.sleep(0.06)
        mid = capture(hwnd, DOCS / "_3d_emotion_crossfade.png")
        time.sleep(0.6)
        happy = capture(hwnd, DOCS / "_3d_emotion_happy.png")
        print("mean neutral->mid delta:", round(mean_delta(neutral, mid), 3))
        print("mean mid->happy delta:", round(mean_delta(mid, happy), 3))
        print("mean RGB delta:", round(mean_delta(neutral, happy), 3))
        # v3.2 step 4: release envelope. Send neutral and sample during/after
        # the 420 ms release; the final image should return to neutral.
        send("neutral", 0.0)
        time.sleep(0.12)
        release = capture(hwnd, DOCS / "_3d_emotion_release.png")
        time.sleep(0.6)
        after = capture(hwnd, DOCS / "_3d_emotion_after.png")
        print("mean happy->release delta:", round(mean_delta(happy, release), 3))
        print("mean happy->after delta:", round(mean_delta(happy, after), 3))
        print("saved:", DOCS / "_3d_emotion_neutral.png")
        print("saved:", DOCS / "_3d_emotion_happy.png")
        print("saved:", DOCS / "_3d_emotion_release.png")
        print("saved:", DOCS / "_3d_emotion_after.png")
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=3)
    finally:
        if proc.poll() is None:
            proc.terminate()
        log.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
