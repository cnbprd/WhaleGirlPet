#!/usr/bin/env python3
"""Read-only schema/geometry check for the 2D card manifest.

Catches the manifest failures the C++ sprite loader assumes away:
missing fields, duplicate ids, rect outside atlas or outside its slot,
source files missing, and sheet_size not matching the actual PNG.

Never launches or stops the 3D renderer.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "assets/2d_bridge/manifest.json"
DEFAULT_OUT = ROOT / "docs/2d-manifest-qa.json"
EXPECTED_IDS = {
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat",
    "action/wave", "action/dance", "action/type", "action/balloon",
    "action/fireworks", "action/lion", "action/change",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"manifest read failed: {exc}")
        return 2

    if manifest.get("version") != 1:
        errors.append(f"version is {manifest.get('version')!r}, expected 1")
    sheet_rel = manifest.get("sheet")
    if not isinstance(sheet_rel, str) or not sheet_rel:
        errors.append("sheet missing or not a string")
        sheet_rel = ""
    sheet_path = ROOT / sheet_rel
    if not sheet_path.exists():
        errors.append(f"sheet missing: {sheet_rel}")
        sheet_size = None
    else:
        with Image.open(sheet_path) as im:
            sheet_size = list(im.size)
    declared = manifest.get("sheet_size")
    if not (isinstance(declared, list) and len(declared) == 2
            and all(isinstance(v, int) and v > 0 for v in declared)):
        errors.append("sheet_size must be two positive integers")
    elif sheet_size is not None and declared != sheet_size:
        errors.append(f"sheet_size {declared} != actual {sheet_size}")

    slot_size = manifest.get("slot_size")
    if not isinstance(slot_size, int) or slot_size <= 0:
        errors.append("slot_size must be a positive integer")
        slot_size = 0
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        errors.append("cards must be an array")
        cards = []

    ids: list[str] = []
    rows = []
    for index, entry in enumerate(cards):
        prefix = f"cards[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: not an object")
            continue
        cid = entry.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append(f"{prefix}: missing id")
            cid = ""
        ids.append(cid)
        group = entry.get("group")
        name = entry.get("name")
        source = entry.get("source")
        rect = entry.get("rect")
        slot = entry.get("slot")
        if not isinstance(group, str) or group not in ("expression", "action"):
            errors.append(f"{prefix}: bad group {group!r}")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}: missing name")
        if not isinstance(source, str) or not source:
            errors.append(f"{prefix}: missing source")
        elif not (ROOT / source).exists():
            errors.append(f"{prefix}: source missing {source}")
        if not (isinstance(rect, list) and len(rect) == 4
                and all(isinstance(v, int) for v in rect)):
            errors.append(f"{prefix}: rect must be four integers")
            rect = None
        elif rect[2] <= 0 or rect[3] <= 0:
            errors.append(f"{prefix}: rect width/height must be positive")
        if not (isinstance(slot, list) and len(slot) == 4
                and all(isinstance(v, int) for v in slot)):
            errors.append(f"{prefix}: slot must be four integers")
            slot = None
        if sheet_size is not None and rect:
            x, y, w, h = rect
            if x < 0 or y < 0 or x + w > sheet_size[0] or y + h > sheet_size[1]:
                errors.append(f"{prefix}: rect outside atlas {rect}")
        if slot_size and slot:
            sx, sy, sw, sh = slot
            if sw != slot_size or sh != slot_size:
                errors.append(f"{prefix}: slot size {sw}x{sh} != {slot_size}")
            if sx % slot_size or sy % slot_size:
                warnings.append(f"{prefix}: slot not aligned to {slot_size}: {slot}")
            if sheet_size is not None and (sx < 0 or sy < 0
                                           or sx + sw > sheet_size[0]
                                           or sy + sh > sheet_size[1]):
                errors.append(f"{prefix}: slot outside atlas {slot}")
        if rect and slot:
            x, y, w, h = rect
            sx, sy, sw, sh = slot
            if not (sx <= x and sy <= y and x + w <= sx + sw and y + h <= sy + sh):
                warnings.append(f"{prefix}: rect is not contained by slot")
        rows.append({
            "id": cid, "group": group, "name": name, "source": source,
            "rect": rect, "slot": slot,
        })

    duplicate_ids = sorted({x for x in ids if ids.count(x) > 1 and x})
    if duplicate_ids:
        errors.append(f"duplicate ids: {duplicate_ids}")
    missing = sorted(EXPECTED_IDS - set(ids))
    extra = sorted(set(ids) - EXPECTED_IDS)
    if missing:
        errors.append(f"missing expected ids: {missing}")
    if extra:
        errors.append(f"unexpected ids: {extra}")
    if len(cards) != len(EXPECTED_IDS):
        errors.append(f"card count {len(cards)} != expected {len(EXPECTED_IDS)}")

    result = {
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "atlas": sheet_rel,
        "sheet_size": sheet_size,
        "slot_size": slot_size,
        "cards": len(cards),
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
        "ids": sorted(ids),
        "rows": rows,
    }
    Path(args.json_out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
    print(f"cards={len(cards)} errors={len(errors)} warnings={len(warnings)} ok={result['ok']}")
    for error in errors:
        print("ERROR:", error)
    for warning in warnings:
        print("WARN:", warning)
    print("json=", args.json_out)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
