#!/usr/bin/env python3
"""Synthetic regression tests for check_soak_final.py.

Every case uses a unique temporary tag under 3d/, writes one checkpoint JSON,
runs the production validator as a subprocess, and removes the fixture in a
finally block. No real soak checkpoint and no whale3d process is touched.
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "check_soak_final.py"
BASE = {
    "status": "done",
    "duration_s": 60.0,
    "sample_interval_s": 30.0,
    "checkpoint_interval_s": 30.0,
    "mode": "visible",
    "updated_at": "2026-11-27T13:52:03+0800",
    "pid": 12345,
    "started_at": "2026-11-27T13:51:03+0800",
    "finished_at": "2026-11-27T13:52:03+0800",
    "elapsed_s": 60.0,
    "alive_after_soak": True,
    "samples": [
        [0.0, 72_851_456, 0.0],
        [30.0, 25_000_000, 5.2],
        [60.0, 24_000_000, 5.1],
    ],
}


def make_case(name: str, **changes) -> dict:
    data = json.loads(json.dumps(BASE))
    data.update(changes)
    return data


def run_case(case_name: str, data: dict | None, expected: int,
             issue_fragment: str | None = None) -> str:
    tag = f"__gate_test_{uuid.uuid4().hex[:8]}_{case_name}"
    path = ROOT / f"longrun_{tag}.json"
    try:
        if data is not None:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--tag", tag],
            text=True,
            capture_output=True,
            timeout=10,
        )
        assert proc.returncode == expected, (
            f"{case_name}: expected exit {expected}, got {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
        if issue_fragment:
            assert issue_fragment in proc.stdout, (
                f"{case_name}: missing issue fragment {issue_fragment!r}\n"
                f"stdout:\n{proc.stdout}"
            )
        return f"PASS {case_name}: exit {proc.returncode}"
    finally:
        path.unlink(missing_ok=True)


def main() -> int:
    cases = [
        ("valid_done", make_case("valid_done"), 0, None),
        ("alive_false", make_case("alive_false", alive_after_soak=False), 1,
         "alive_after_soak is not true"),
        ("error_field", make_case("error_field", error="synthetic failure"), 1,
         "error: synthetic failure"),
        ("finished_missing", make_case("finished_missing", finished_at=""), 1,
         "finished_at missing"),
        ("sample_count_mismatch",
         make_case("sample_count_mismatch", sample_count=4), 1,
         "sample_count 4 != samples length 3"),
        ("short_samples",
         make_case("short_samples", duration_s=86400.0, sample_interval_s=30.0,
                   samples=[[0.0, 1, 0], [30.0, 1, 0], [60.0, 1, 0]]), 1,
         "sample count 3 < expected 2881"),
        ("running", make_case("running", status="running"), 3, None),
        ("missing_checkpoint", None, 2, "missing checkpoint"),
    ]
    failures = 0
    for name, data, expected, fragment in cases:
        try:
            print(run_case(name, data, expected, fragment))
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    print(f"\n{len(cases) - failures}/{len(cases)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
