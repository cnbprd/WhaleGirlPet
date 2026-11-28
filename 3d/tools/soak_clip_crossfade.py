#!/usr/bin/env python3
"""Short real-window soak for the idle/walk clip crossfade.

Toggles W faster than the 180 ms fade window, records one-core CPU, and fails
if the process exits or no fade log appears. This is a stability probe, not a
replacement for the 10-minute idle baseline.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_cards_visible as qa  # noqa: E402

ROOT = HERE.parent


def key(hwnd: int, down: bool) -> None:
    qa.user32.PostMessageW(hwnd, 0x0100 if down else 0x0101, 0x57, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=ROOT / "whale3d-stage2-crossfade.exe")
    parser.add_argument("--out-dir", type=Path, default=ROOT.parent / "build" / "stage2-crossfade-soak")
    parser.add_argument("--seconds", type=float, default=90.0)
    parser.add_argument("--toggle-ms", type=int, default=600)
    args = parser.parse_args()

    exe = args.exe.resolve()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = out / "crossfade-soak.log"
    proc = None
    try:
        proc = qa.launch_3d(exe, log)
        hwnd = qa.wait_for_window(proc.pid, 12.0)
        if not qa.wait_log(log, "AnimationController ready", 8.0):
            raise RuntimeError("controller not ready")

        import psutil
        ps = psutil.Process(proc.pid)
        last_cpu = sum(ps.cpu_times()[:2])
        last_time = time.monotonic()
        samples: list[dict[str, float]] = []
        start = time.monotonic()
        next_cpu = start + 5.0

        while time.monotonic() - start < args.seconds:
            key(hwnd, True)
            key(hwnd, False)
            time.sleep(args.toggle_ms / 1000.0)
            if proc.poll() is not None:
                raise RuntimeError(f"process exited early: {proc.returncode}")
            if time.monotonic() >= next_cpu:
                now = time.monotonic()
                cpu = sum(ps.cpu_times()[:2])
                elapsed = max(0.001, now - last_time)
                samples.append({
                    "t_s": round(now - start, 1),
                    "cpu_pct_one_core": round((cpu - last_cpu) / elapsed * 100.0, 2),
                })
                last_cpu = cpu
                last_time = now
                next_cpu += 5.0

        fades = sum(
            1 for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.startswith("clip fade:")
        ) if log.exists() else 0

        result = {
            "ok": proc.poll() is None and fades > 0,
            "exe": str(exe),
            "seconds": args.seconds,
            "toggle_ms": args.toggle_ms,
            "fade_count": fades,
            "cpu_avg_one_core": round(
                sum(item["cpu_pct_one_core"] for item in samples) / len(samples), 2
            ) if samples else None,
            "cpu_max_one_core": max(
                (item["cpu_pct_one_core"] for item in samples), default=None
            ),
            "samples": samples,
            "log": str(log),
        }
        (out / "crossfade-soak.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    finally:
        qa.stop_process(proc)


if __name__ == "__main__":
    raise SystemExit(main())
