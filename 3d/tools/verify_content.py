#!/usr/bin/env python3
"""Read-only verifier for the stage-3 content.json.

This does not load the renderer or replace runtime validation. It catches a
tampered/missing cooked file, a stale source hash, a wrong card count, or a
schema mismatch before packaging.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTENT = ROOT / "build/content/content.json"
DEFAULT_REPORT = ROOT / "docs/content-verify.json"
SCHEMA = "whale3d-content-v1"
EXPECTED_IDS = {
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat",
    "action/wave", "action/dance", "action/type", "action/balloon",
    "action/fireworks", "action/lion", "action/change",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    content_path = args.content.resolve()
    report_path = args.report.resolve()
    errors: list[str] = []
    checks: list[dict] = []

    if not content_path.exists():
        print(f"content missing: {content_path}")
        return 2
    try:
        content = json.loads(content_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"content read failed: {exc}")
        return 2

    if content.get("schema") != SCHEMA:
        errors.append(f"schema {content.get('schema')!r} != {SCHEMA}")

    model = content.get("model", {})
    model_source = ROOT / str(model.get("source", ""))
    if not model_source.exists():
        errors.append(f"model source missing: {model.get('source')}")
    elif model.get("sha256") != sha256(model_source):
        errors.append("model sha256 mismatch")

    cards = content.get("cards", {})
    manifest = ROOT / str(cards.get("manifest", ""))
    atlas = ROOT / str(cards.get("atlas", ""))
    if not manifest.exists():
        errors.append(f"manifest missing: {cards.get('manifest')}")
    elif cards.get("manifest_sha256") != sha256(manifest):
        errors.append("manifest sha256 mismatch")
    if not atlas.exists():
        errors.append(f"atlas missing: {cards.get('atlas')}")
    elif cards.get("atlas_sha256") != sha256(atlas):
        errors.append("atlas sha256 mismatch")
    ids = cards.get("ids", [])
    if not isinstance(ids, list):
        errors.append("card ids not an array")
        ids = []
    if set(ids) != EXPECTED_IDS:
        errors.append(f"card ids mismatch: missing={sorted(EXPECTED_IDS - set(ids))} "
                      f"extra={sorted(set(ids) - EXPECTED_IDS)}")
    if cards.get("count") != len(EXPECTED_IDS) or len(ids) != len(EXPECTED_IDS):
        errors.append(f"card count {cards.get('count')} ids {len(ids)} != {len(EXPECTED_IDS)}")
    if cards.get("sheet_size") != [1024, 512]:
        errors.append(f"sheet_size {cards.get('sheet_size')} != [1024, 512]")
    if cards.get("slot_size") != 160:
        errors.append(f"slot_size {cards.get('slot_size')} != 160")

    cooked = content.get("cooked", {})
    cooked_dir = ROOT / str(cooked.get("dir", ""))
    if not cooked_dir.is_dir():
        errors.append(f"cooked dir missing: {cooked.get('dir')}")
    for item in cooked.get("files", []):
        path = ROOT / str(item.get("path", ""))
        if not path.exists():
            errors.append(f"cooked file missing: {item.get('path')}")
            checks.append({"path": item.get("path"), "ok": False})
            continue
        actual_hash = sha256(path)
        actual_size = path.stat().st_size
        ok = actual_hash == item.get("sha256") and actual_size == item.get("bytes")
        if not ok:
            errors.append(f"cooked file mismatch: {item.get('path')}")
        checks.append({
            "path": item.get("path"),
            "ok": ok,
            "sha256": actual_hash,
            "bytes": actual_size,
        })

    for item in content.get("sources", []):
        path = ROOT / str(item.get("path", ""))
        if not path.exists():
            errors.append(f"source missing: {item.get('path')}")
        elif sha256(path) != item.get("sha256"):
            errors.append(f"source sha256 mismatch: {item.get('path')}")

    report = {
        "content": str(content_path),
        "ok": not errors,
        "errors": errors,
        "checks": checks,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                     sort_keys=True) + "\n", encoding="utf-8")
    print(f"ok={not errors} errors={len(errors)} cooked={len(checks)}")
    for error in errors:
        print("ERROR:", error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
