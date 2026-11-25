# -*- coding: utf-8 -*-
"""v3.0.26 第三阶段：把裙摆/尾巴按 alpha 遮罩拆成独立层，供运行时 Verlet spring 摆动。

输出（每套皮肤）：
  assets/skins/layers/<skin>_base.png    去掉裙摆/尾巴的底图
  assets/skins/layers/<skin>_skirt.png   裙摆层（含透明画布）
  assets/skins/layers/<skin>_tail.png    尾巴层（含透明画布）
  assets/skins/layers/layers.json        枢轴点与层参数
  assets/skins/layers/<name>@2x.png      2x 版本

约束：
- 裙摆层优先；尾巴与裙摆重叠的地方归裙摆（视觉上尾巴在裙子后面），
  尾巴层从重叠区扣除，避免同一像素被画两次。
- 三层在静止位重新相加 == 原图；运行时只移动层，不重画身体。
"""
from __future__ import annotations

import json
import os
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "skins", "layers")
DOCS = os.path.join(ROOT, "docs")

# 归一化多边形，按 512 高立绘目检标定。只覆盖布料/尾巴，不碰手臂和脸。
SPECS = {
    "default": {
        "skirt": [(0.27, 0.44), (0.33, 0.42), (0.40, 0.42), (0.48, 0.41),
                  (0.56, 0.42), (0.64, 0.42), (0.69, 0.44), (0.72, 0.48),
                  (0.72, 0.54), (0.69, 0.58), (0.62, 0.60), (0.54, 0.59),
                  (0.46, 0.60), (0.38, 0.60), (0.30, 0.59), (0.25, 0.55),
                  (0.24, 0.50), (0.25, 0.46)],
        "tail": [(0.60, 0.53), (0.67, 0.52), (0.74, 0.53), (0.80, 0.52),
                 (0.86, 0.54), (0.92, 0.53), (0.98, 0.56), (1.00, 0.60),
                 (0.97, 0.63), (0.90, 0.64), (0.83, 0.62), (0.76, 0.61),
                 (0.69, 0.59), (0.63, 0.57), (0.60, 0.55)],
        "skirt_pivot": (0.50, 0.43),
        "tail_pivot": (0.63, 0.55),
    },
    "jk": {
        "skirt": [(0.28, 0.44), (0.34, 0.42), (0.41, 0.43), (0.48, 0.42),
                  (0.56, 0.42), (0.64, 0.43), (0.69, 0.45), (0.72, 0.49),
                  (0.72, 0.54), (0.69, 0.58), (0.62, 0.59), (0.54, 0.60),
                  (0.46, 0.60), (0.38, 0.60), (0.31, 0.58), (0.27, 0.54),
                  (0.26, 0.49)],
        "tail": [(0.71, 0.45), (0.77, 0.44), (0.83, 0.46), (0.89, 0.45),
                 (0.95, 0.47), (1.00, 0.51), (0.99, 0.56), (0.94, 0.59),
                 (0.87, 0.60), (0.81, 0.57), (0.75, 0.55), (0.71, 0.50)],
        "skirt_pivot": (0.50, 0.43),
        "tail_pivot": (0.71, 0.46),
    },
}


def _poly_mask(size, pts, blur=1.4):
    w, h = size
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.polygon([(int(x * w), int(y * h)) for x, y in pts], fill=255)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return m


def _color_gate(src, kind):
    """只保留布料/尾巴像素，避免把同色区域的头发、手臂当成布料切走。

    - 深色布料：max(rgb) < 150 且 g < 120（藏青裙、黑裙、深色尾巴）
    - 纯白荷叶边/围裙：min(rgb) > 225（皮肤最亮处通常达不到三道 225）
    - 尾巴只取深色，不取高光蓝发。
    """
    rgb = src.convert("RGB")
    r, g, b = rgb.split()
    dark = ImageChops.multiply(
        r.point(lambda v: 255 if v < 150 else 0),
        ImageChops.multiply(
            g.point(lambda v: 255 if v < 120 else 0),
            b.point(lambda v: 255 if v < 175 else 0),
        ),
    )
    if kind == "tail":
        return dark
    white = ImageChops.multiply(
        r.point(lambda v: 255 if v > 225 else 0),
        ImageChops.multiply(
            g.point(lambda v: 255 if v > 225 else 0),
            b.point(lambda v: 255 if v > 225 else 0),
        ),
    )
    return ImageChops.lighter(dark, white)


def _compose(src, mask):
    out = src.copy()
    a = ImageChops.multiply(src.getchannel("A"), mask)
    out.putalpha(a)
    return out


def _rotate_layer(layer, pivot, angle):
    # PIL 的正角是逆时针；仅用于预览，不出运行时资产
    return layer.rotate(angle, resample=Image.BICUBIC, center=pivot, fillcolor=(0, 0, 0, 0))


def build_one(skin, spec, factor=1):
    src_path = os.path.join(ROOT, "assets", "skins", skin + ".png")
    if factor == 2:
        p2 = os.path.join(ROOT, "assets", "skins", skin + "@2x.png")
        if os.path.exists(p2):
            src_path = p2
    src = Image.open(src_path).convert("RGBA")
    size = src.size
    skirt_m = ImageChops.multiply(_poly_mask(size, spec["skirt"], blur=0.8),
                                  _color_gate(src, "skirt"))
    tail_m = ImageChops.multiply(_poly_mask(size, spec["tail"], blur=0.8),
                                 _color_gate(src, "tail"))
    skirt_m = skirt_m.filter(ImageFilter.GaussianBlur(1.2 * factor))
    tail_m = tail_m.filter(ImageFilter.GaussianBlur(1.2 * factor))
    # 裙摆优先：尾巴层扣掉裙摆区域
    tail_m = ImageChops.subtract(tail_m, skirt_m)
    union = ImageChops.lighter(skirt_m, tail_m)
    base = src.copy()
    base.putalpha(ImageChops.multiply(src.getchannel("A"), ImageChops.invert(union)))
    skirt = _compose(src, skirt_m)
    tail = _compose(src, tail_m)
    suffix = "@2x" if factor == 2 else ""
    base.save(os.path.join(OUT, f"{skin}_base{suffix}.png"))
    skirt.save(os.path.join(OUT, f"{skin}_skirt{suffix}.png"))
    tail.save(os.path.join(OUT, f"{skin}_tail{suffix}.png"))
    return base, skirt, tail


def preview(default_base, default_skirt, default_tail, jk_base, jk_skirt, jk_tail):
    rows = []
    for base, skirt, tail, piv in [
        (default_base, default_skirt, default_tail, SPECS["default"]),
        (jk_base, jk_skirt, jk_tail, SPECS["jk"]),
    ]:
        cells = []
        w, h = base.size
        for angle in (-7, 0, 7):
            canvas = base.copy()
            sp = (int(piv["skirt_pivot"][0] * w), int(piv["skirt_pivot"][1] * h))
            tp = (int(piv["tail_pivot"][0] * w), int(piv["tail_pivot"][1] * h))
            t = _rotate_layer(tail, tp, angle * 1.3)
            s = _rotate_layer(skirt, sp, angle)
            canvas.alpha_composite(t)
            canvas.alpha_composite(s)
            crop = canvas.crop((0, 180, w, 350))
            bg = Image.new("RGBA", crop.size, (242, 244, 248, 255))
            bg.alpha_composite(crop)
            cells.append(bg)
        row = Image.new("RGBA", (sum(c.width for c in cells) + 20, max(c.height for c in cells)),
                        (255, 255, 255, 255))
        x = 0
        for c in cells:
            row.alpha_composite(c, (x, 0))
            x += c.width + 10
        rows.append(row)
    out = Image.new("RGBA", (max(r.width for r in rows), sum(r.height for r in rows) + 10),
                    (255, 255, 255, 255))
    y = 0
    for r in rows:
        out.alpha_composite(r, (0, y))
        y += r.height + 10
    out.save(os.path.join(DOCS, "_v326_layers_preview.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {"skins": {}}
    previews = {}
    for skin, spec in SPECS.items():
        b1, s1, t1 = build_one(skin, spec, 1)
        b2, s2, t2 = build_one(skin, spec, 2)
        # 2x 预览只用 1x 资产
        previews[skin] = (b1, s1, t1)
        meta["skins"][skin] = {
            "skirt_pivot": list(spec["skirt_pivot"]),
            "tail_pivot": list(spec["tail_pivot"]),
            "base": f"{skin}_base.png",
            "skirt": f"{skin}_skirt.png",
            "tail": f"{skin}_tail.png",
            "base_2x": f"{skin}_base@2x.png",
            "skirt_2x": f"{skin}_skirt@2x.png",
            "tail_2x": f"{skin}_tail@2x.png",
        }
        print("built", skin, b1.size, b2.size)
    with open(os.path.join(OUT, "layers.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    preview(previews["default"][0], previews["default"][1], previews["default"][2],
            previews["jk"][0], previews["jk"][1], previews["jk"][2])
    print("preview", os.path.join(DOCS, "_v326_layers_preview.png"))


if __name__ == "__main__":
    main()
