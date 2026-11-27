#!/usr/bin/env python3
"""Structural lint for the P1 sprite manifest fixtures.

This does NOT execute the C++ parser. It only confirms that the fixture table
is complete, uniquely named, valid JSON where intended, and that every case
declares either an exact error or an error prefix. The real parser regression
must run after the P1 branch is built.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Lint sprite manifest fixtures")
    parser.add_argument("--cases", default=str(repo_root / "3d/tests/fixtures/sprite_manifest/cases.json"))
    args = parser.parse_args()

    cases_path = Path(args.cases)
    if not cases_path.is_file():
        print(f"FAIL missing cases file: {cases_path}")
        return 1
    try:
        data = json.loads(cases_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL cases JSON: {exc}")
        return 1

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        print("FAIL cases must be a non-empty array")
        return 1

    errors = []
    names = []
    success_count = 0
    failure_count = 0
    for index, case in enumerate(cases):
        name = case.get("name") if isinstance(case, dict) else None
        if not isinstance(name, str) or not name:
            errors.append(f"case[{index}] missing name")
            continue
        if name in names:
            errors.append(f"duplicate case name: {name}")
        names.append(name)

        expect = case.get("expect")
        if not isinstance(expect, dict) or not isinstance(expect.get("ok"), bool):
            errors.append(f"{name}: expect.ok must be boolean")
            continue
        if expect["ok"]:
            success_count += 1
            if "error" in expect or "error_prefix" in expect:
                errors.append(f"{name}: success case must not declare error")
        else:
            failure_count += 1
            if not (expect.get("error") or expect.get("error_prefix")):
                errors.append(f"{name}: failure case needs error or error_prefix")

        if "raw_manifest" in case:
            if "manifest" in case:
                errors.append(f"{name}: use manifest or raw_manifest, not both")
            try:
                json.loads(case["raw_manifest"])
            except (TypeError, json.JSONDecodeError):
                pass
            else:
                errors.append(f"{name}: raw_manifest is valid JSON, expected malformed")
        elif "manifest" in case:
            if not isinstance(case["manifest"], dict):
                errors.append(f"{name}: manifest must be an object")
        else:
            errors.append(f"{name}: missing manifest/raw_manifest")

    if success_count != 1:
        errors.append(f"expected exactly 1 success case, got {success_count}")
    if failure_count != len(cases) - 1:
        errors.append(f"failure count mismatch: {failure_count}")

    print(f"cases={len(cases)} success={success_count} failure={failure_count}")
    for error in errors:
        print(f"ERROR {error}")
    print("fixture lint: PASS" if not errors else "fixture lint: FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
