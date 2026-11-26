# -*- coding: utf-8 -*-
"""Pack the 2D expression/action cards into one GPU-friendly atlas.

This is the first, renderer-independent half of the 2D asset bridge:
- use the 1x assets only (skip @2x and *_sleep previews);
- trim transparent borders, scale to a 150px visual height;
- pack into a fixed 1024x512 RGBA sheet (6 x 3 slots of 160px);
- write a manifest that a future sprite layer can consume without decoding
  individual PNGs at runtime.

The script deliberately does not touch the 3D executable or the wiring.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUT_DIR = ASSETS / "2d_bridge"
ATLAS_W, ATLAS_H = 1024, 512
SLOT = 160
MARGIN = 4


def collect() -> list[tuple[str, str, Path]]:
    cards: list[tuple[str, str, Path]] = []
    for group, folder in (("expression", "expressions"), ("action", "actions")):
        for path in sorted((ASSETS / folder).glob("*.png")):
            stem = path.stem
            if "@2x" in stem or stem.endswith("_sleep"):
                continue
            cards.append((group, stem, path))
    return cards


def trim_alpha(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


def fit_slot(image: Image.Image) -> Image.Image:
    image = trim_alpha(image.convert("RGBA"))
    max_h = SLOT - MARGIN * 2
    max_w = SLOT - MARGIN * 2
    scale = min(max_w / image.width, max_h / image.height, 1.0)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = collect()
    if len(cards) > (ATLAS_W // SLOT) * (ATLAS_H // SLOT):
        raise SystemExit(f"too many cards: {len(cards)}")

    atlas = Image.new("RGBA", (ATLAS_W, ATLAS_H), (0, 0, 0, 0))
    entries = []
    for index, (group, name, path) in enumerate(cards):
        slot_x = (index % (ATLAS_W // SLOT)) * SLOT
        slot_y = (index // (ATLAS_W // SLOT)) * SLOT
        card = fit_slot(Image.open(path))
        x = slot_x + (SLOT - card.width) // 2
        y = slot_y + (SLOT - card.height) // 2
        atlas.alpha_composite(card, (x, y))
        entries.append({
            "id": f"{group}/{name}",
            "group": group,
            "name": name,
            "source": path.relative_to(ROOT).as_posix(),
            "rect": [x, y, card.width, card.height],
            "slot": [slot_x, slot_y, SLOT, SLOT],
        })

    atlas_path = out_dir / "atlas.png"
    atlas.save(atlas_path, optimize=True)
    manifest = {
        "version": 1,
        "sheet": atlas_path.relative_to(ROOT).as_posix(),
        "sheet_size": [ATLAS_W, ATLAS_H],
        "slot_size": SLOT,
        "cards": entries,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"cards={len(entries)} atlas={atlas_path} bytes={atlas_path.stat().st_size}")
    print(f"manifest={manifest_path} bytes={manifest_path.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
