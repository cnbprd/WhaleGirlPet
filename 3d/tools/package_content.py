#!/usr/bin/env python3
"""Build the package-layout content.json from the stage-3 cook output.

The cook content uses repository/build paths. The portable ZIP and installer
use a package root with assets/models and assets/2d_bridge. This tool verifies
that the actual stage files match the cook hashes, then writes a package
manifest with package-relative paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COOK = ROOT / "build/content/content.json"
DEFAULT_STAGE = ROOT / "ci-package"
PACKAGE_SCHEMA = "whale3d-content-package-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def package_path(source: str) -> str:
    if source.startswith("3d/"):
        return source[3:]
    return source


def cooked_to_package(path: str) -> str:
    prefix = "build/content/"
    if not path.startswith(prefix):
        raise ValueError(f"unexpected cooked path: {path}")
    value = path[len(prefix):]
    if value.startswith("3d/"):
        value = value[3:]
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cook", type=Path, default=DEFAULT_COOK)
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    cook_path = args.cook.resolve()
    stage = args.stage.resolve()
    out_path = (args.out if args.out else stage / "content.json").resolve()
    errors: list[str] = []

    if not cook_path.exists():
        print(f"cook content missing: {cook_path}")
        return 2
    try:
        cook = json.loads(cook_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"cook content read failed: {exc}")
        return 2
    if cook.get("schema") != "whale3d-content-v1":
        errors.append(f"cook schema {cook.get('schema')!r} != whale3d-content-v1")
    if not stage.is_dir():
        errors.append(f"stage missing: {stage}")

    model = cook.get("model", {})
    cards = cook.get("cards", {})
    model_pkg = package_path(str(model.get("source", "")))
    manifest_pkg = package_path(str(cards.get("manifest", "")))
    atlas_pkg = package_path(str(cards.get("atlas", "")))
    files = []
    for item in cook.get("cooked", {}).get("files", []):
        try:
            rel = cooked_to_package(str(item.get("path", "")))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        path = stage / rel
        if not path.exists():
            errors.append(f"stage file missing: {rel}")
            continue
        size = path.stat().st_size
        digest = sha256(path)
        if size != item.get("bytes") or digest != item.get("sha256"):
            errors.append(f"stage file mismatch: {rel}")
        files.append({
            "path": rel,
            "bytes": size,
            "sha256": digest,
        })

    package = {
        "schema": PACKAGE_SCHEMA,
        "cook_schema": cook.get("schema"),
        "cook_sha256": sha256(cook_path),
        "model": {
            "path": model_pkg,
            "bytes": model.get("bytes"),
            "sha256": model.get("sha256"),
        },
        "cards": {
            "manifest": manifest_pkg,
            "manifest_sha256": cards.get("manifest_sha256"),
            "atlas": atlas_pkg,
            "atlas_sha256": cards.get("atlas_sha256"),
            "count": cards.get("count"),
            "ids": cards.get("ids", []),
        },
        "files": files,
    }
    if not errors:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"ok={not errors} files={len(files)} errors={len(errors)}")
    for error in errors:
        print("ERROR:", error)
    if not errors:
        print(f"content={out_path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
