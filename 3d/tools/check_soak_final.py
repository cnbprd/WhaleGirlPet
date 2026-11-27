#!/usr/bin/env python3
"""Validate a finished 24h soak checkpoint. Read-only: never launches or stops whale3d.

Exit codes:
  0  finished and valid
  1  finished but invalid
  2  checkpoint missing
  3  still running / not finished
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAG = "soak_24h_sprite_task"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def fps_stats(path: Path) -> dict[str, float] | None:
    values: list[float] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "fps=" in line:
                try:
                    values.append(float(line.split("fps=")[1].split()[0]))
                except (IndexError, ValueError):
                    pass
    if not values:
        return None
    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(statistics.fmean(values), 2),
        "last": values[-1],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    summary_path = ROOT / f"longrun_{args.tag}.json"
    log_path = ROOT / f"longrun_{args.tag}.log"
    if not summary_path.exists():
        print(f"missing checkpoint: {summary_path}")
        return 2

    data = json.loads(summary_path.read_text(encoding="utf-8"))
    samples = data.get("samples") or []
    status = data.get("status")
    duration = float(data.get("duration_s") or 0)
    interval = float(data.get("sample_interval_s") or 0)
    expected = int(duration / interval) + 1 if interval > 0 else None
    sample_count = int(data.get("sample_count") or len(samples))
    fps = fps_stats(log_path)

    issues: list[str] = []
    if status != "done":
        issues.append(f"status is {status!r}, not 'done'")
    if status == "done" and data.get("alive_after_soak") is not True:
        issues.append("alive_after_soak is not true")
    if status == "done" and not data.get("finished_at"):
        issues.append("finished_at missing")
    if data.get("error"):
        issues.append(f"error: {data['error']}")
    if sample_count != len(samples):
        issues.append(f"sample_count {sample_count} != samples length {len(samples)}")
    if expected is not None and len(samples) < expected - 2:
        issues.append(f"sample count {len(samples)} < expected {expected} - 2")
    if samples:
        last_elapsed = float(samples[-1][0])
        if duration > 0 and last_elapsed < duration - max(interval * 2, 60):
            issues.append(f"last elapsed {last_elapsed:.1f}s is short of {duration:.0f}s")

    started = parse_time(data.get("started_at"))
    finished = parse_time(data.get("finished_at"))
    rss_start = float(samples[0][1]) / (1024 * 1024) if samples else None
    rss_end = float(samples[-1][1]) / (1024 * 1024) if samples else None
    rss_delta = (rss_end - rss_start) if rss_start is not None and rss_end is not None else None
    report = {
        "tag": args.tag,
        "status": status,
        "finished": status == "done",
        "valid": status == "done" and not issues,
        "issues": issues,
        "samples": len(samples),
        "expected_samples": expected,
        "sample_count_field": data.get("sample_count"),
        "duration_s": duration,
        "elapsed_s": float(samples[-1][0]) if samples else None,
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "wall_clock_s": (round((finished - started).total_seconds(), 1)
                          if started and finished else None),
        "alive_after_soak": data.get("alive_after_soak"),
        "rss_start_mb": round(rss_start, 1) if rss_start is not None else None,
        "rss_end_mb": round(rss_end, 1) if rss_end is not None else None,
        "rss_delta_mb": round(rss_delta, 1) if rss_delta is not None else None,
        "fps": fps,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
        if status != "done":
            print("\nNOT FINISHED: this is a progress check, not a 24h conclusion.")

    if status != "done":
        return 3
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
