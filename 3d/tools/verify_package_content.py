#!/usr/bin/env python3
"""Verify the package-layout content.json inside a stage dir or ZIP."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

PACKAGE_SCHEMA = "whale3d-content-package-v1"
EXPECTED_IDS = {
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat",
    "action/wave", "action/dance", "action/type", "action/balloon",
    "action/fireworks", "action/lion", "action/change",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_member(reader, path: str) -> bytes:
    return reader(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--stage", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    checks: list[dict] = []
    close_zip = None
    try:
        if args.zip:
            zf = zipfile.ZipFile(args.zip)
            close_zip = zf

            def reader(path: str) -> bytes:
                return zf.read(path)
        elif args.stage:
            stage = args.stage

            def reader(path: str) -> bytes:
                return (stage / path).read_bytes()
        else:
            print("one of --zip or --stage is required")
            return 2

        content = json.loads(reader("content.json").decode("utf-8"))
        if content.get("schema") != PACKAGE_SCHEMA:
            errors.append(f"schema {content.get('schema')!r} != {PACKAGE_SCHEMA}")

        files = content.get("files", [])
        if not isinstance(files, list) or not files:
            errors.append("files missing")
            files = []
        seen = set()
        for item in files:
            path = str(item.get("path", ""))
            if not path or path.startswith("/") or ".." in path.split("/"):
                errors.append(f"unsafe file path: {path!r}")
                continue
            if path in seen:
                errors.append(f"duplicate file path: {path}")
                continue
            seen.add(path)
            try:
                data = reader(path)
            except (KeyError, FileNotFoundError, OSError):
                errors.append(f"file missing: {path}")
                checks.append({"path": path, "ok": False})
                continue
            actual_size = len(data)
            actual_hash = sha256(data)
            ok = actual_size == item.get("bytes") and actual_hash == item.get("sha256")
            if not ok:
                errors.append(f"file mismatch: {path}")
            checks.append({"path": path, "ok": ok, "bytes": actual_size, "sha256": actual_hash})

        cards = content.get("cards", {})
        ids = cards.get("ids", [])
        if set(ids) != EXPECTED_IDS:
            errors.append("card ids mismatch")
        if cards.get("count") != len(EXPECTED_IDS):
            errors.append(f"card count {cards.get('count')} != {len(EXPECTED_IDS)}")
        if cards.get("atlas") not in seen or cards.get("manifest") not in seen:
            errors.append("cards manifest/atlas not listed in files")
        if content.get("model", {}).get("path") not in seen:
            errors.append("model not listed in files")
        if content.get("cook_schema") != "whale3d-content-v1":
            errors.append(f"cook_schema {content.get('cook_schema')!r} != whale3d-content-v1")
    finally:
        if close_zip is not None:
            close_zip.close()

    report = {"ok": not errors, "errors": errors, "checks": checks}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                          sort_keys=True) + "\n", encoding="utf-8")
    print(f"ok={not errors} errors={len(errors)} files={len(checks)}")
    for error in errors:
        print("ERROR:", error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
