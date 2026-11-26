#!/usr/bin/env python3
"""v3.2 normal-animation + long-run acceptance.

Unlike emotion_accept.py this does NOT set WHALE3D_FREEZE. It runs the real
idle animation, cycles intensity envelopes for 90 s, samples RSS/CPU and
writes two "animation is alive" frames plus a final frame.
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

import psutil
from PIL import Image, ImageChops, ImageGrab

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent / "docs"
user32 = ctypes.windll.user32
WM_CLOSE = 0x0010
DURATION = 90.0
CYCLE = 8.0


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


def send(emotion: str, intensity: float) -> None:
    payload = {
        "emotion": emotion,
        "intensity": intensity,
        "source": "longrun",
        "curve": {"attack_ms": 180, "release_ms": 420},
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", 47832))
    finally:
        sock.close()
    print(f"sent {emotion} {intensity}")


def mean_delta(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    total = sum(value * count for value, count in enumerate(hist[:256]))
    return total / (a.width * a.height * 3)


def fps_range(path: Path) -> tuple[float, float, float]:
    values = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "fps=" in line:
                try:
                    values.append(float(line.split("fps=")[1].split()[0]))
                except (IndexError, ValueError):
                    pass
    if not values:
        return 0.0, 0.0, 0.0
    return min(values), max(values), sum(values) / len(values)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.pop("WHALE3D_FREEZE", None)
    env["WHALE3D_FACE"] = "auto"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_EMOTION_TRACE"] = "1"
    log_path = ROOT / "longrun.log"
    env["WHALE3D_LOG"] = str(log_path)
    err_path = ROOT / "longrun.err.log"
    err = open(err_path, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [str(ROOT / "whale3d.exe")],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=err,
    )
    ps = psutil.Process(proc.pid)
    samples = []
    try:
        hwnd = find_window()
        if not hwnd:
            raise RuntimeError("3D window not found")
        time.sleep(2.0)
        anim_a = capture(hwnd, DOCS / "_3d_longrun_anim_a.png")
        time.sleep(1.2)
        anim_b = capture(hwnd, DOCS / "_3d_longrun_anim_b.png")

        start = time.monotonic()
        next_cycle = start
        next_sample = start
        while time.monotonic() - start < DURATION:
            now = time.monotonic()
            if now >= next_cycle:
                send("happy", 0.8)
                time.sleep(0.9)
                send("neutral", 0.0)
                next_cycle += CYCLE
            if now >= next_sample:
                samples.append((round(now - start, 1), ps.memory_info().rss,
                                ps.cpu_percent(interval=None)))
                next_sample += 10.0
            time.sleep(0.2)
        send("neutral", 0.0)
        time.sleep(2.0)
        final = capture(hwnd, DOCS / "_3d_longrun_final.png")

        rss_mb = [round(r / (1024 * 1024), 1) for _, r, _ in samples]
        cpu = [c for _, _, c in samples]
        print("alive_after_90s:", proc.poll() is None)
        print("animation_mean_delta:", round(mean_delta(anim_a, anim_b), 3))
        print("rss_mb:", rss_mb)
        print("cpu_percent_samples:", [round(c, 1) for c in cpu])
        print("fps_min_max_avg:", tuple(round(x, 2) for x in fps_range(log_path)))
        for name in ("_3d_longrun_anim_a.png", "_3d_longrun_anim_b.png",
                     "_3d_longrun_final.png"):
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
        err.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
