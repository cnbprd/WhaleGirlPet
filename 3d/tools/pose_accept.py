#!/usr/bin/env python3
"""Visual acceptance for v3.2 gaze / body lean.

Run with the repo venv:
    python 3d/tools/pose_accept.py

It launches the 3D shell with the animation frozen, captures neutral, sends
gaze and lean offsets over the localhost UDP bus, and captures the result and
the released pose. The window title is the real "鲸鱼娘" title.
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


def send(emotion: str = "neutral", intensity: float = 0.0,
         gaze=None, lean=None, source: str = "pose_acceptance") -> None:
    payload = {
        "emotion": emotion,
        "intensity": intensity,
        "source": source,
        "curve": {"attack_ms": 180, "release_ms": 420},
    }
    if gaze is not None:
        payload["gaze"] = gaze
    if lean is not None:
        payload["lean"] = lean
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", 47832))
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
    env["WHALE3D_LOG"] = str(ROOT / "pose_accept.log")
    log_path = ROOT / "pose_accept.err.log"
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
        neutral = capture(hwnd, DOCS / "_3d_pose_neutral.png")

        send(gaze={"x": 0.8, "y": -0.1, "weight": 1.0})
        time.sleep(0.35)
        gaze = capture(hwnd, DOCS / "_3d_pose_gaze.png")

        send(lean={"x": 0.8, "y": 0.0, "weight": 0.8})
        time.sleep(0.35)
        lean = capture(hwnd, DOCS / "_3d_pose_lean.png")

        send()
        time.sleep(0.25)
        reset = capture(hwnd, DOCS / "_3d_pose_reset.png")

        print("mean neutral->gaze delta:", round(mean_delta(neutral, gaze), 3))
        print("mean gaze->lean delta:", round(mean_delta(gaze, lean), 3))
        print("mean neutral->lean delta:", round(mean_delta(neutral, lean), 3))
        print("mean neutral->reset delta:", round(mean_delta(neutral, reset), 3))
        for name in ("_3d_pose_neutral.png", "_3d_pose_gaze.png",
                     "_3d_pose_lean.png", "_3d_pose_reset.png"):
            print("saved:", DOCS / name)

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
