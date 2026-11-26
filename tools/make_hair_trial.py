# -*- coding: utf-8 -*-
"""最小素材试拆：default 皮肤左右外侧发束 → 独立 alpha 层 + A/B 预览。

不进入运行时，不引入 See-through / Stretchy / Spine。
目的：先看“多一条发梢 spring”是否真的比 v3.0.26 的裙摆/尾巴两层更有活物感。

输出：
  assets/skins/layers_trial/default_base_cut.png
  assets/skins/layers_trial/default_hair_l.png
  assets/skins/layers_trial/default_hair_r.png
  assets/skins/layers_trial/hair_trial.json
  docs/_hair_trial_ab.png
"""
from __future__ import annotations

import json
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "skins", "default.png")
LAYERS = os.path.join(ROOT, "assets", "skins", "layers")
OUT = os.path.join(ROOT, "assets", "skins", "layers_trial")
DOCS = os.path.join(ROOT, "docs")

# 归一化多边形，只覆盖左右外侧发束；中间脸/身体不碰。
SPECS = {
    "hair_l": {
        "poly": [(0.03, 0.26), (0.08, 0.22), (0.14, 0.22), (0.20, 0.25),
                 (0.22, 0.31), (0.20, 0.38), (0.18, 0.46), (0.14, 0.53),
                 (0.10, 0.57), (0.06, 0.55), (0.03, 0.48), (0.01, 0.38)],
        "pivot": (0.14, 0.23),
    },
    "hair_r": {
        "poly": [(0.72, 0.26), (0.77, 0.22), (0.81, 0.22), (0.84, 0.26),
                 (0.85, 0.33), (0.84, 0.41), (0.82, 0.49), (0.79, 0.54),
                 (0.76, 0.53), (0.74, 0.47), (0.72, 0.38), (0.71, 0.32)],
        "pivot": (0.78, 0.23),
    },
}


def _poly_mask(size, pts, blur=1.0):
    w, h = size
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon(
        [(int(x * w), int(y * h)) for x, y in pts], fill=255)
    return m.filter(ImageFilter.GaussianBlur(blur))


def _hair_gate(src):
    """蓝/紫发色：B 明显高于 R；白蕾丝、皮肤、黑裙都不会过。"""
    r, g, b, a = src.split()
    diff = ImageChops.subtract(b, r)
    blue = diff.point(lambda v: 255 if v >= 12 else 0)
    dark = b.point(lambda v: 255 if v >= 45 else 0)
    return ImageChops.multiply(a, ImageChops.multiply(blue, dark))


def _compose(src, mask):
    out = src.copy()
    out.putalpha(ImageChops.multiply(src.getchannel("A"), mask))
    return out


def _rotate(layer, pivot, angle):
    return layer.rotate(angle, resample=Image.BICUBIC,
                        center=pivot, fillcolor=(0, 0, 0, 0))


def build():
    os.makedirs(OUT, exist_ok=True)
    src = Image.open(SRC).convert("RGBA")
    size = src.size
    gate = _hair_gate(src)
    base_full = Image.open(os.path.join(LAYERS, "default_base.png")).convert("RGBA")
    masks = {}
    for part, spec in SPECS.items():
        m = ImageChops.multiply(_poly_mask(size, spec["poly"]), gate)
        m = m.filter(ImageFilter.GaussianBlur(0.6))
        masks[part] = m
        _compose(src, m).save(os.path.join(OUT, f"default_{part}.png"))

    union = ImageChops.lighter(masks["hair_l"], masks["hair_r"])
    cut = base_full.copy()
    cut.putalpha(ImageChops.multiply(base_full.getchannel("A"),
                                     ImageChops.invert(union)))
    cut.save(os.path.join(OUT, "default_base_cut.png"))

    # 静止位校验：cut + tail + skirt + hair == 原图？
    tail = Image.open(os.path.join(LAYERS, "default_tail.png")).convert("RGBA")
    skirt = Image.open(os.path.join(LAYERS, "default_skirt.png")).convert("RGBA")
    hair_l = Image.open(os.path.join(OUT, "default_hair_l.png")).convert("RGBA")
    hair_r = Image.open(os.path.join(OUT, "default_hair_r.png")).convert("RGBA")
    rest = cut.copy()
    for layer in (tail, skirt, hair_l, hair_r):
        rest.alpha_composite(layer)
    diff = ImageChops.difference(rest, src)
    bbox = diff.getbbox()
    mean = sum(diff.convert("L").getdata()) / (size[0] * size[1])

    meta = {
        "skin": "default",
        "base": "default_base_cut.png",
        "parts": {
            k: {"file": f"default_{k}.png", "pivot": list(v["pivot"]),
                "mode": "rotate", "max_deg": 8.0, "stiffness": 34.0,
                "damping": 10.0, "gain": 1.35}
            for k, v in SPECS.items()
        },
    }
    with open(os.path.join(OUT, "hair_trial.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("size", size, "mask_px", {k: sum(1 for p in v.getdata() if p > 100)
                                   for k, v in masks.items()})
    print("rest_diff_bbox", bbox, "mean_abs", round(mean, 4))
    return src, base_full, cut, tail, skirt, hair_l, hair_r, meta


def preview(src, base_full, cut, tail, skirt, hair_l, hair_r, meta):
    W, H = src.size
    crop_y0, crop_y1 = 80, 380
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 14)
    except OSError:
        font = None

    def cell(base, label, angle=None, hair=False):
        canvas = base.copy()
        for layer in (tail, skirt):
            canvas.alpha_composite(layer)
        if hair:
            for part in ("hair_l", "hair_r"):
                pv = meta["parts"][part]["pivot"]
                p = (int(pv[0] * W), int(pv[1] * H))
                canvas.alpha_composite(_rotate(hair_l if part == "hair_l" else hair_r,
                                               p, angle))
        bg = Image.new("RGBA", (W, crop_y1 - crop_y0), (244, 246, 250, 255))
        bg.alpha_composite(canvas.crop((0, crop_y0, W, crop_y1)))
        return bg, label

    rows = [
        [cell(src, "原图"), cell(base_full, "v3.0.26：裙摆+尾巴")],
        [cell(cut, "+发束 静位", 0, True), cell(cut, "+发束 -9°", -9, True)],
        [cell(cut, "+发束 +9°", 9, True), (Image.new("RGBA", (W, crop_y1 - crop_y0),
                                                    (255, 255, 255, 255)), "")],
    ]

    pad = 14
    cw = W
    ch = crop_y1 - crop_y0
    out = Image.new("RGBA", (cw * 2 + pad * 3, ch * len(rows) + pad * (len(rows) + 1)),
                    (255, 255, 255, 255))
    d = ImageDraw.Draw(out)
    for r, items in enumerate(rows):
        y = pad + r * (ch + pad)
        for c, (im, label) in enumerate(items):
            x = pad + c * (cw + pad)
            out.alpha_composite(im, (x, y))
            d.text((x, y - 14), label, fill=(40, 55, 80, 255), font=font)
    out.convert("RGB").save(os.path.join(DOCS, "_hair_trial_ab.png"))
    print("preview", os.path.join(DOCS, "_hair_trial_ab.png"))


def main():
    src, base_full, cut, tail, skirt, hair_l, hair_r, meta = build()
    preview(src, base_full, cut, tail, skirt, hair_l, hair_r, meta)


if __name__ == "__main__":
    main()
