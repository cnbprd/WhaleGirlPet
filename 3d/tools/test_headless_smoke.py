#!/usr/bin/env python3
"""Headless smoke for whale3d.

Runs N fixed-dt frames, then validates:
- exit code 0
- log has "headless done frames=N gl_error=0x0"
- summary JSON has mode=headless and frames=N
- trace JSONL parses and contains one summary line

Usage:
  python 3d/tools/test_headless_smoke.py --frames 60
  python 3d/tools/test_headless_smoke.py --frames 600
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def fail(message: str, log_tail: str = "") -> None:
    print(f"FAIL: {message}")
    if log_tail:
        print(log_tail)
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=str(Path("3d/whale3d-headless.exe")))
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--fixed-dt", default="1/60")
    parser.add_argument("--no-render", action="store_true")
    parser.add_argument("--out-dir", default=str(Path("build/headless-smoke")))
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    if not exe.is_file():
        fail(f"missing exe: {exe}")
    if args.frames <= 0:
        fail(f"invalid frames: {args.frames}")

    outdir = Path(args.out_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    log_path = outdir / f"headless-{args.frames}.log"
    summary_path = outdir / f"headless-{args.frames}-summary.json"
    trace_path = outdir / f"headless-{args.frames}-trace.jsonl"
    for path in (log_path, summary_path, trace_path):
        path.unlink(missing_ok=True)

    env = os.environ.copy()
    env["WHALE3D_LOG"] = str(log_path)
    env["WHALE3D_TRACE"] = str(trace_path)
    cmd = [
        str(exe),
        "--headless",
        "--no-render" if args.no_render else "",
        f"--frames={args.frames}",
        f"--fixed-dt={args.fixed_dt}",
        f"--summary={summary_path}",
    ]
    cmd = [part for part in cmd if part]
    print("RUN:", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(exe.parent),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    if proc.returncode != 0:
        fail(f"exit={proc.returncode}", log_text[-4000:])

    match = re.search(
        r"headless done frames=(\d+) gl_error=0x([0-9a-fA-F]+) center_alpha=(\d+) render=(\d)",
        log_text,
    )
    if not match:
        fail("missing 'headless done' line", log_text[-4000:])
    done_frames = int(match.group(1))
    gl_error = int(match.group(2), 16)
    center_alpha = int(match.group(3))
    did_render = int(match.group(4))
    if done_frames != args.frames:
        fail(f"done frames={done_frames}, expected {args.frames}", log_text[-4000:])
    if gl_error != 0:
        fail(f"GL error 0x{gl_error:x}", log_text[-4000:])
    if args.no_render:
        if did_render != 0:
            fail("expected no-render path", log_text[-4000:])
    else:
        if did_render != 1:
            fail("expected render path", log_text[-4000:])
        if center_alpha <= 0:
            fail(f"center_alpha={center_alpha}, model not rendered", log_text[-4000:])

    if not summary_path.is_file():
        fail(f"missing summary: {summary_path}", log_text[-4000:])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_mode = "headless-cpu" if args.no_render else "headless"
    if summary.get("mode") != expected_mode:
        fail(f"summary mode={summary.get('mode')!r}, expected {expected_mode!r}")
    if summary.get("frames") != args.frames:
        fail(f"summary frames={summary.get('frames')}, expected {args.frames}")
    for key in ("fps", "p50_ms", "p95_ms", "p99_ms", "work_ms", "hitch"):
        if key not in summary:
            fail(f"summary missing {key}")

    if not trace_path.is_file():
        fail(f"missing trace: {trace_path}")
    trace_lines = [
        line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not trace_lines:
        fail("empty trace")
    parsed = [json.loads(line) for line in trace_lines]
    if not any(item.get("mode") in ("headless", "headless-cpu") for item in parsed):
        fail("trace has no headless summary")

    print(
        "PASS:",
        f"frames={done_frames}",
        f"center_alpha={center_alpha}",
        f"fps={summary['fps']}",
        f"p50={summary['p50_ms']}ms",
        f"p99={summary['p99_ms']}ms",
        f"work={summary['work_ms']}ms",
    )
    print(f"summary={summary_path}")
    print(f"trace={trace_path}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired:
        print("FAIL: headless timeout")
        sys.exit(1)
