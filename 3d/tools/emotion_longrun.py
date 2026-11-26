#!/usr/bin/env python3
"""v3.2 normal-animation + long-run acceptance.

Unlike emotion_accept.py this does NOT set WHALE3D_FREEZE. It runs the real
idle animation, cycles emotion and gaze/lean envelopes, samples RSS/CPU/FPS,
and writes "animation is alive" frames plus a final frame.

Default duration is 10 minutes. Override with WHALE3D_LONGRUN_SECONDS.
This is still not a 24-hour soak by default; it is a bounded leak/stability probe.
Long-run helpers: WHALE3D_LONGRUN_TAG isolates logs/images/JSON,
WHALE3D_LONGRUN_SAMPLE sets the sampling interval, and
WHALE3D_LONGRUN_OFFSCREEN=1 moves the window offscreen (still renders at ~28 fps,
but avoids occupying the desktop) for a multi-hour run.
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
DURATION = float(os.environ.get("WHALE3D_LONGRUN_SECONDS", "600"))
CYCLE = 20.0
SAMPLE_INTERVAL = float(os.environ.get("WHALE3D_LONGRUN_SAMPLE", "10"))
TAG = os.environ.get("WHALE3D_LONGRUN_TAG", "").strip().strip("_")
if any(ch in TAG for ch in ("/", "\\", ":", "..")):
    raise SystemExit("WHALE3D_LONGRUN_TAG must be a simple filename token")
OFFSCREEN = os.environ.get("WHALE3D_LONGRUN_OFFSCREEN", "") == "1"
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
user32.SetWindowPos.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND,
                                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = ctypes.wintypes.BOOL


def output_path(stem: str) -> Path:
    if TAG:
        return DOCS / f"_3d_longrun_{TAG}_{stem}.png"
    if stem == "mid":
        return DOCS / "_3d_longrun_10m_mid.png"
    return DOCS / f"_3d_longrun_{stem}.png"


def summary_path() -> Path:
    return ROOT / f"longrun_{TAG}.json" if TAG else ROOT / "longrun.json"


def write_summary(status: str, **fields) -> None:
    payload = {
        "status": status,
        "tag": TAG,
        "duration_s": DURATION,
        "sample_interval_s": SAMPLE_INTERVAL,
        "checkpoint_interval_s": SAMPLE_INTERVAL * 10,
        "mode": "offscreen" if OFFSCREEN else "visible",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "pid": fields.pop("pid", None),
        "started_at": fields.pop("started_at", None),
        **fields,
    }
    summary_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                              encoding="utf-8")


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


def send(emotion: str, intensity: float, gaze=None, lean=None) -> None:
    payload = {
        "emotion": emotion,
        "intensity": intensity,
        "source": "longrun",
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
    print(f"sent {emotion} {intensity} gaze={gaze is not None} lean={lean is not None}")


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
    log_path = ROOT / (f"longrun_{TAG}.log" if TAG else "longrun.log")
    env["WHALE3D_LOG"] = str(log_path)
    err_path = ROOT / (f"longrun_{TAG}.err.log" if TAG else "longrun.err.log")
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
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    write_summary("running", pid=proc.pid, started_at=started_at, samples=[])
    try:
        hwnd = find_window()
        if not hwnd:
            raise RuntimeError("3D window not found")
        if OFFSCREEN:
            if not user32.SetWindowPos(hwnd, 0, -6000, -6000, 0, 0,
                                       SWP_NOSIZE | SWP_NOZORDER):
                raise RuntimeError("SetWindowPos failed")
        time.sleep(2.0)
        if OFFSCREEN:
            anim_a = anim_b = None
        else:
            anim_a = capture(hwnd, output_path("anim_a"))
            time.sleep(1.2)
            anim_b = capture(hwnd, output_path("anim_b"))

        start = time.monotonic()
        next_sample = start
        next_pose = start
        cycle_index = -1
        phase = 0
        mid = None
        while time.monotonic() - start < DURATION:
            now = time.monotonic()
            elapsed = now - start
            idx = int(elapsed // CYCLE)
            if idx != cycle_index:
                cycle_index = idx
                phase = 0
                next_pose = start + idx * CYCLE
            if phase >= 4:
                if next_pose < start + (idx + 1) * CYCLE:
                    next_pose = start + (idx + 1) * CYCLE
            elif now >= next_pose:
                if phase == 0:
                    send("happy", 0.8, gaze={"x": 0.8, "y": -0.1, "weight": 1.0})
                elif phase == 1:
                    send("neutral", 0.0, lean={"x": 0.8, "y": 0.0, "weight": 0.8})
                else:
                    send("neutral", 0.0)
                phase += 1
                if phase < 4:
                    next_pose = start + idx * CYCLE + (6.0 if phase == 1 else
                                                      12.0 if phase == 2 else 16.0)
            if now >= next_sample:
                samples.append((round(elapsed, 1), ps.memory_info().rss,
                                ps.cpu_percent(interval=None)))
                next_sample += SAMPLE_INTERVAL
                if len(samples) % 10 == 0:
                    write_summary("running", pid=proc.pid, started_at=started_at,
                                  elapsed_s=round(elapsed, 1), samples=samples)
            if not OFFSCREEN and mid is None and elapsed >= DURATION / 2:
                mid = capture(hwnd, output_path("mid"))
            time.sleep(0.2)
        send("neutral", 0.0)
        time.sleep(2.0)
        final = None if OFFSCREEN else capture(hwnd, output_path("final"))

        rss_mb = [round(r / (1024 * 1024), 1) for _, r, _ in samples]
        cpu = [c for _, _, c in samples]
        fps_min, fps_max, fps_avg = fps_range(log_path)
        metrics = {
            "alive_after_soak": proc.poll() is None,
            "animation_mean_delta": (None if OFFSCREEN
                                     else round(mean_delta(anim_a, anim_b), 3)),
            "rss_start_mb": rss_mb[0] if rss_mb else None,
            "rss_end_mb": rss_mb[-1] if rss_mb else None,
            "rss_min_max_mb": (min(rss_mb), max(rss_mb)) if rss_mb else None,
            "cpu_percent_avg_max": ((round(sum(cpu) / len(cpu), 1), round(max(cpu), 1))
                                    if cpu else None),
            "fps_min_max_avg": (round(fps_min, 2), round(fps_max, 2), round(fps_avg, 2)),
            "sample_count": len(samples),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        write_summary("done", pid=proc.pid, started_at=started_at,
                      samples=samples, **metrics)
        print("duration_s:", DURATION)
        for key, value in metrics.items():
            print(f"{key}:", value)
        if not OFFSCREEN:
            for stem in ("anim_a", "anim_b", "mid", "final"):
                print("saved:", output_path(stem))

        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=3)
    except Exception as exc:
        write_summary("error", pid=proc.pid, started_at=started_at,
                      error=repr(exc), samples=samples)
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
        err.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
