# -*- coding: utf-8 -*-
"""Check the 2D card atlas against its source PNGs.

This is CPU-only: it does not compile or launch the 3D renderer.  It catches
the failures that would otherwise show up as wrong/missing cards after the
sprite layer is wired:
- manifest rect outside the sheet;
- alpha content clipped by the slot;
- atlas card differing from the source after the documented trim/scale;
- a card that is empty or entirely transparent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "assets/2d_bridge/manifest.json"
ATLAS = ROOT / "assets/2d_bridge/atlas.png"
OUT_JSON = ROOT / "docs/2d-atlas-qa.json"
OUT_SHEET = ROOT / "docs/_2d_bridge_contact.png"
SLOT = 160
MARGIN = 4


def trim_alpha(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


def alpha_mae(a: Image.Image, b: Image.Image) -> float:
    a_bytes = a.tobytes()
    b_bytes = b.tobytes()
    if len(a_bytes) != len(b_bytes):
        return 255.0
    total = sum(abs(x - y) for x, y in zip(a_bytes, b_bytes))
    return total / max(1, len(a_bytes))


def rgb_mae(a: Image.Image, b: Image.Image) -> float:
    a_bytes = a.convert("RGB").tobytes()
    b_bytes = b.convert("RGB").tobytes()
    if len(a_bytes) != len(b_bytes):
        return 255.0
    total = sum(abs(x - y) for x, y in zip(a_bytes, b_bytes))
    return total / max(1, len(a_bytes))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default=str(OUT_JSON))
    parser.add_argument("--sheet-out", default=str(OUT_SHEET))
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    atlas = Image.open(ATLAS).convert("RGBA")
    sheet_w, sheet_h = atlas.size
    results = []
    failures = 0

    for entry in manifest["cards"]:
        x, y, w, h = (int(v) for v in entry["rect"])
        cid = entry["id"]
        source = Image.open(ROOT / entry["source"]).convert("RGBA")
        source = trim_alpha(source)
        source = source.resize((w, h), Image.Resampling.LANCZOS)
        region = atlas.crop((x, y, x + w, y + h))
        a_mae = alpha_mae(region.getchannel("A"), source.getchannel("A"))
        c_mae = rgb_mae(region, source)
        coverage_a = sum(1 for v in region.getchannel("A").tobytes() if v > 8)
        coverage_s = sum(1 for v in source.getchannel("A").tobytes() if v > 8)
        coverage_delta = abs(coverage_a - coverage_s) / max(1, coverage_s)
        alpha_bbox = region.getchannel("A").getbbox()
        inside = (0 <= x and 0 <= y and x + w <= sheet_w and y + h <= sheet_h)
        empty = alpha_bbox is None
        ok = inside and not empty and a_mae <= 4.0 and c_mae <= 8.0
        if not ok:
            failures += 1
        results.append({
            "id": cid,
            "source": entry["source"],
            "rect": [x, y, w, h],
            "inside": inside,
            "empty": empty,
            "alpha_mae": round(a_mae, 3),
            "rgb_mae": round(c_mae, 3),
            "coverage_delta": round(coverage_delta, 4),
            "ok": ok,
        })

    summary = {
        "atlas": str(ATLAS.relative_to(ROOT)),
        "sheet_size": [sheet_w, sheet_h],
        "cards": len(results),
        "failures": failures,
        "max_alpha_mae": max(r["alpha_mae"] for r in results),
        "max_rgb_mae": max(r["rgb_mae"] for r in results),
        "max_coverage_delta": max(r["coverage_delta"] for r in results),
        "results": results,
    }
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")

    cols, rows = 6, 3
    cell_w, cell_h = SLOT, SLOT + 20
    sheet = Image.new("RGBA", (cols * cell_w, rows * cell_h), (26, 26, 26, 255))
    draw = ImageDraw.Draw(sheet)
    for index, entry in enumerate(results):
        col = index % cols
        row = index // cols
        card = atlas.crop((entry["rect"][0], entry["rect"][1],
                           entry["rect"][0] + entry["rect"][2],
                           entry["rect"][1] + entry["rect"][3]))
        px = col * cell_w + (cell_w - card.width) // 2
        py = row * cell_h + 20 + (SLOT - card.height) // 2
        sheet.alpha_composite(card, (px, py))
        draw.text((col * cell_w + 4, row * cell_h + 3), entry["id"],
                  fill=(255, 255, 255, 255))
    sheet_path = Path(args.sheet_out)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(sheet_path, optimize=True)

    print(f"cards={len(results)} failures={failures}")
    print(f"max_alpha_mae={summary['max_alpha_mae']} max_rgb_mae={summary['max_rgb_mae']} "
          f"max_coverage_delta={summary['max_coverage_delta']}")
    print(f"json={json_out} bytes={json_out.stat().st_size}")
    print(f"sheet={sheet_path} bytes={sheet_path.stat().st_size}")
    if failures:
        for r in results:
            if not r["ok"]:
                print(f"FAIL {r['id']} alpha={r['alpha_mae']} rgb={r['rgb_mae']} "
                      f"cov={r['coverage_delta']} inside={r['inside']} empty={r['empty']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
