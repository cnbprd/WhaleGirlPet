#!/usr/bin/env python3
"""Compare stage-4 render output against the stage-2 golden capture set.

The 3D window is transparent, so the desktop behind the pet is part of every
screen capture.  A raw main-window pixel diff is therefore not stable.  This
checker compares the parts that must be invariant:

* client size 420x620
* all 17 card ids and their client-space rects
* all 17 card crop byte dimensions
* per-card crop difference (bounded, catches gross regressions)
* corner transparency sanity (an opaque black window fails)
* click-through result (card transparent, model client)

It writes a JSON report and returns non-zero if a hard check fails.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURRENT = ROOT.parent / "build" / "stage4-cards"
DEFAULT_GOLDEN = ROOT.parent / "build" / "stage2-crossfade-cards"
DEFAULT_OUT = ROOT.parent / "docs" / "render-golden.json"
DEFAULT_CLICK = ROOT.parent / "build" / "stage4-click.json"


def load_qa(path: Path) -> dict:
    qa_path = path / "2d-card-visible-qa.json"
    if not qa_path.exists():
        raise RuntimeError(f"missing QA JSON: {qa_path}")
    return json.loads(qa_path.read_text(encoding="utf-8"))


def mean_abs_diff(a_path: Path, b_path: Path) -> float:
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        raise ValueError(f"size mismatch: {a.size} vs {b.size}")
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    total = sum(i * n for i, n in enumerate(hist[:256]))
    total += sum(i * n for i, n in enumerate(hist[256:512]))
    total += sum(i * n for i, n in enumerate(hist[512:768]))
    pixels = a.size[0] * a.size[1] * 3
    return round(total / pixels, 3)


def corner_brightness(path: Path) -> dict:
    image = Image.open(path).convert("RGB")
    width, height = image.size
    patches = {
        "top_left": image.crop((0, 0, 24, 24)),
        "top_right": image.crop((width - 24, 0, width, 24)),
        "bottom_left": image.crop((0, height - 24, 24, height)),
        "bottom_right": image.crop((width - 24, height - 24, width, height)),
    }
    result = {}
    for name, patch in patches.items():
        histogram = patch.convert("L").histogram()
        pixels = sum(histogram)
        result[name] = round(sum(i * n for i, n in enumerate(histogram)) / pixels, 2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--click", type=Path, default=DEFAULT_CLICK)
    args = parser.parse_args()

    current = load_qa(args.current)
    golden = load_qa(args.golden)
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    cur_client = current.get("window", {})
    gold_client = golden.get("window", {})
    check(
        "client_420x620",
        cur_client.get("client_w") == 420 and cur_client.get("client_h") == 620,
        f"current={cur_client.get('client_w')}x{cur_client.get('client_h')} "
        f"golden={gold_client.get('client_w')}x{gold_client.get('client_h')}",
    )

    cur_cards = {item["card"]: item for item in current.get("cards", [])}
    gold_cards = {item["card"]: item for item in golden.get("cards", [])}
    check(
        "17_cards",
        len(cur_cards) == 17 and len(gold_cards) == 17 and set(cur_cards) == set(gold_cards),
        f"current={len(cur_cards)} golden={len(gold_cards)}",
    )

    rect_mismatches = []
    crop_mismatches = []
    diffs = []
    for card_id in sorted(gold_cards):
        if card_id not in cur_cards:
            rect_mismatches.append(f"{card_id}: missing")
            continue
        cur = cur_cards[card_id]
        gold = gold_cards[card_id]
        if cur.get("client_rect") != gold.get("client_rect"):
            rect_mismatches.append(f"{card_id}: {cur.get('client_rect')} != {gold.get('client_rect')}")
        cur_crop = args.current / Path(cur["crop"]).name
        gold_crop = args.golden / Path(gold["crop"]).name
        if not cur_crop.exists() or not gold_crop.exists():
            crop_mismatches.append(f"{card_id}: crop missing")
            continue
        cur_size = Image.open(cur_crop).size
        gold_size = Image.open(gold_crop).size
        if cur_size != gold_size:
            crop_mismatches.append(f"{card_id}: {cur_size} != {gold_size}")
            continue
        diff = mean_abs_diff(cur_crop, gold_crop)
        diffs.append({"card": card_id, "mean_abs_diff": diff})
        if diff > 20.0:
            crop_mismatches.append(f"{card_id}: mean_abs_diff {diff} > 20")

    check("card_rects_exact", not rect_mismatches, "; ".join(rect_mismatches) or "all exact")
    check("card_crop_sizes_exact", not crop_mismatches, "; ".join(crop_mismatches) or "all exact")
    check(
        "card_crop_diff_bounded",
        all(item["mean_abs_diff"] <= 20.0 for item in diffs),
        f"max_mean_abs_diff={max((item['mean_abs_diff'] for item in diffs), default=0)}",
    )

    current_baseline = args.current / "_3d_visible_baseline.png"
    brightness = corner_brightness(current_baseline) if current_baseline.exists() else {}
    check(
        "transparent_corner_not_opaque_black",
        bool(brightness) and min(brightness.values()) > 10.0,
        json.dumps(brightness, ensure_ascii=False),
    )

    if args.click.exists():
        click = json.loads(args.click.read_text(encoding="utf-8"))
        check(
            "click_through",
            bool(click.get("ok"))
            and click.get("card_hit_test") == -1
            and click.get("model_hit_test") == 1
            and click.get("target", {}).get("received") is True,
            f"card={click.get('card_hit_test')} model={click.get('model_hit_test')} "
            f"received={click.get('target', {}).get('received')}",
        )
    else:
        check("click_through", False, f"missing {args.click}")

    result = {
        "current": str(args.current),
        "golden": str(args.golden),
        "checks": checks,
        "card_diffs": diffs,
        "ok": all(item["ok"] for item in checks),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
