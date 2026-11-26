"""Frame-level acceptance for the VRM spring-bone prototype.

Run with the repo's local Python (Pillow is already used by the 3D tests):
    python 3d/spring_accept.py

It launches two otherwise identical runs, one with WHALE3D_SPRING=0 and one
with springs enabled, both with the base clip frozen at t=0. The saved
screenshots are the evidence; the printed mean RGB delta is only a sanity
signal (a pixel-identical result means the spring layer did not reach the
screen).
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageGrab

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"
user32 = ctypes.windll.user32
WM_CLOSE = 0x0010


def find_window(timeout: float = 12.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = user32.FindWindowW(None, "WhaleGirl 3D Placeholder")
        if hwnd:
            return hwnd
        time.sleep(0.15)
    return 0


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def capture(hwnd: int, path: Path) -> Image.Image:
    left, top, right, bottom = window_rect(hwnd)
    image = ImageGrab.grab(bbox=(left, top, right, bottom)).convert("RGB")
    image.save(path)
    return image


def run_one(spring: int) -> tuple[int, list[Image.Image]]:
    env = os.environ.copy()
    env["WHALE3D_FACE"] = "open"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_SPRING"] = str(spring)
    env["WHALE3D_FREEZE"] = "1"
    log_path = ROOT / f"spring_{'on' if spring else 'off'}.err.log"
    log = open(log_path, "w", encoding="utf-8", buffering=1)
    proc = subprocess.Popen(
        [str(ROOT / "whale3d.exe")],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=log,
    )
    hwnd = find_window()
    if not hwnd:
        proc.terminate()
        log.close()
        raise SystemExit(f"window not found for spring={spring}")
    frames = []
    for index in range(3):
        time.sleep(0.55)
        frames.append(capture(hwnd, DOCS / f"_3d_spring_{'on' if spring else 'off'}_{index}.png"))
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    try:
        proc.wait(timeout=6)
    except subprocess.TimeoutExpired:
        proc.terminate()
    log.close()
    return proc.returncode, frames


def mean_delta(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    histogram = diff.histogram()
    total = sum(value * count for value, count in enumerate(histogram[:256]))
    total += sum(value * count for value, count in enumerate(histogram[256:512]))
    total += sum(value * count for value, count in enumerate(histogram[512:768]))
    return total / (a.width * a.height * 3)


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    rc_off, off = run_one(0)
    rc_on, on = run_one(1)
    print(f"exit off={rc_off} on={rc_on}")
    print("mean RGB delta per frame:",
          [round(mean_delta(a, b), 3) for a, b in zip(off, on)])
    # A nonzero delta on all three frames is the minimum screen-level proof.
    deltas = [mean_delta(a, b) for a, b in zip(off, on)]
    ok = all(delta > 0.5 for delta in deltas)
    print("spring visible on screen:", "YES" if ok else "NO/TOO SMALL")
    return 0 if ok and rc_off == 0 and rc_on == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
