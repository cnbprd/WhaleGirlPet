#!/usr/bin/env python3
r"""Read the JSON checkpoint and log from emotion_longrun.py.

Example:
  .\.venv\Scripts\python.exe 3d\tools\soak_report.py --tag 24h
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent / "docs"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def fps_stats(path: Path) -> tuple[float, float, float, float]:
    values = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "fps=" in line:
                try:
                    values.append(float(line.split("fps=")[1].split()[0]))
                except (IndexError, ValueError):
                    pass
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    return min(values), max(values), statistics.fmean(values), values[-1]


def rss_trend(samples: list[list[float]]) -> tuple[float | None, float | None]:
    if len(samples) < 2:
        return None, None
    xs = [float(s[0]) for s in samples]
    ys = [float(s[1]) / (1024 * 1024) for s in samples]
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return None, None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
    return slope * 3600.0, ys[-1] - ys[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="", help="WHALE3D_LONGRUN_TAG value")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    summary = ROOT / (f"longrun_{args.tag}.json" if args.tag else "longrun.json")
    log_path = ROOT / (f"longrun_{args.tag}.log" if args.tag else "longrun.log")
    if not summary.exists():
        print(f"missing checkpoint: {summary}")
        return 2
    data = json.loads(summary.read_text(encoding="utf-8"))
    samples = data.get("samples") or []
    fps = fps_stats(log_path)
    rss_slope, rss_delta = rss_trend(samples)
    updated = parse_time(data.get("updated_at"))
    stale_s = None if updated is None else (datetime.now(updated.tzinfo) - updated).total_seconds()
    interval = float(data.get("sample_interval_s") or 0)
    checkpoint_interval = float(data.get("checkpoint_interval_s") or interval * 10)
    stale_window = max(interval * 2.5, checkpoint_interval * 2.5)
    stale = bool(data.get("status") == "running" and stale_s is not None
                 and stale_window > 0 and stale_s > stale_window)
    report = {
        "tag": data.get("tag"),
        "status": data.get("status"),
        "mode": data.get("mode"),
        "duration_s": data.get("duration_s"),
        "elapsed_s": samples[-1][0] if samples else None,
        "remaining_s": (max(0.0, float(data.get("duration_s", 0)) - float(samples[-1][0]))
                        if samples else data.get("duration_s")),
        "samples": len(samples),
        "expected_samples": (int(float(data.get("duration_s", 0)) / interval) + 1
                            if interval else None),
        "rss_mb_start": round(float(samples[0][1]) / (1024 * 1024), 1) if samples else None,
        "rss_mb_last": round(float(samples[-1][1]) / (1024 * 1024), 1) if samples else None,
        "rss_mb_delta": round(rss_delta, 1) if rss_delta is not None else None,
        "rss_mb_per_hour": round(rss_slope, 3) if rss_slope is not None else None,
        "cpu_avg": (round(statistics.fmean([s[2] for s in samples if s[2] > 0]), 1)
                    if any(s[2] > 0 for s in samples) else None),
        "cpu_max": round(max(s[2] for s in samples), 1) if samples else None,
        "fps_min": round(fps[0], 2),
        "fps_max": round(fps[1], 2),
        "fps_avg": round(fps[2], 2),
        "fps_last": round(fps[3], 2),
        "updated_at": data.get("updated_at"),
        "stale_s": round(stale_s, 1) if stale_s is not None else None,
        "stale": stale,
        "error": data.get("error"),
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    if report["status"] == "error" or stale:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
