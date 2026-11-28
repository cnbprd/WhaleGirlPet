#!/usr/bin/env python3
"""Real-window drag QA for the 3D shell.

The test presses the left button in the middle of the client area, moves in
ten steps, and verifies the window follows by roughly the same delta. It uses
the real desktop cursor, not a synthetic hit-test message.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_click_through as ct  # noqa: E402

ROOT = HERE.parent
DEFAULT_EXE = ROOT / "whale3d-stage2-queue.exe"
DEFAULT_OUT = ROOT.parent / "build" / "stage2-queue" / "drag-test.json"


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if not ct.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect failed")
    return rect.left, rect.top, rect.right, rect.bottom


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--target-x", type=int, default=100)
    parser.add_argument("--target-y", type=int, default=50)
    parser.add_argument("--tolerance", type=int, default=20)
    args = parser.parse_args()

    exe = args.exe.resolve()
    out = args.out.resolve()
    log = (args.log if args.log else out.with_suffix(".log")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    if log.exists():
        log.unlink()

    proc = None
    try:
        env = os.environ.copy()
        env.pop("WHALE3D_CARD", None)
        env["WHALE3D_LOG"] = str(log)
        proc = subprocess.Popen(
            [str(exe)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        hwnd = ct.wait_for_window(proc.pid, 12.0)
        time.sleep(1.0)

        client_x, client_y, client_w, client_h = ct.client_geometry(hwnd)
        start = window_rect(hwnd)
        px, py = client_x + client_w // 2, client_y + client_h // 2
        old = wintypes.POINT()
        ct.user32.GetCursorPos(ctypes.byref(old))
        ct.user32.SetCursorPos(px, py)
        time.sleep(0.15)
        ct.user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
        for index in range(1, 11):
            ct.user32.SetCursorPos(
                px + index * args.target_x // 10,
                py + index * args.target_y // 10,
            )
            time.sleep(0.04)
        ct.user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
        time.sleep(1.0)
        end = window_rect(hwnd)
        ct.user32.SetCursorPos(old.x, old.y)

        delta = (end[0] - start[0], end[1] - start[1])
        result = {
            "ok": (
                abs(delta[0] - args.target_x) <= args.tolerance
                and abs(delta[1] - args.target_y) <= args.tolerance
            ),
            "hwnd": int(hwnd),
            "pid": proc.pid,
            "start": start[:2],
            "end": end[:2],
            "delta": delta,
            "target": [args.target_x, args.target_y],
            "tolerance": args.tolerance,
            "log": str(log),
        }
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    finally:
        ct.stop_process(proc)


if __name__ == "__main__":
    raise SystemExit(main())
