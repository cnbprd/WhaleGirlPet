# -*- coding: utf-8 -*-
"""批量：把母版派生的立绘/表情处理成原素材尺寸的透明底 PNG，并出对比图。

用法：改 JOBS 里的 (名称, 目标原图路径, 新图URL) 即可复用。
"""
import io
import os
import urllib.request

import numpy as np
from PIL import Image, ImageDraw

from bg_cut import clear_bg

ROOT = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet"
OUT = os.path.join(ROOT, "assets", "_matting", "derived")
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("longmaid", os.path.join(ROOT, "assets", "skins", "longmaid.png"),
     "https://aka.doubaocdn.com/s/EdBvU9sqdk"),
    ("hanfu", os.path.join(ROOT, "assets", "skins", "hanfu.png"),
     "https://aka.doubaocdn.com/s/6bqrY2EC6y"),
    ("sleep", os.path.join(ROOT, "assets", "expressions", "sleep.png"),
     "https://aka.doubaocdn.com/s/gKNBZOKV4r"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return Image.open(io.BytesIO(r.read()))


def _unused():
    return None


def board(size, cell=16):
    b = Image.new("RGB", size, (238, 238, 238))
    d = ImageDraw.Draw(b)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(205, 205, 205))
    return b


def fit(src: Image.Image, target: tuple) -> Image.Image:
    """按高度对齐缩放到目标尺寸，水平居中，真透明底。"""
    canvas = src.convert("RGBA")
    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)
    scale = target[1] / canvas.height
    w = max(1, int(round(canvas.width * scale)))
    resized = canvas.resize((w, target[1]), Image.LANCZOS)
    sheet = Image.new("RGBA", target, (0, 0, 0, 0))
    sheet.alpha_composite(resized, (max(0, (target[0] - w) // 2), 0))
    return sheet


for name, src_path, url in JOBS:
    base = Image.open(src_path).convert("RGBA")
    sz = base.size
    raw = fetch(url)
    alpha_ok = raw.mode in ("RGBA", "LA") and np.asarray(raw.convert("RGBA"))[..., 3].min() < 250
    if not alpha_ok:
        raw = clear_bg(raw)
        alpha_ok = True
    print(f"{name}: src={raw.size} alpha={alpha_ok} target={sz}")
    new = fit(raw, sz)
    p = os.path.join(OUT, f"{name}-v2.png")
    new.save(p)
    print("  saved", p, "alpha_min", np.asarray(new)[..., 3].min())

    h = sz[1]
    w = sz[0] * 2 + 24
    cmp = board((w, h + 28))
    cmp.paste(base, (0, 14), base)
    cmp.paste(new, (sz[0] + 24, 14), new)
    d = ImageDraw.Draw(cmp)
    d.text((6, 2), "OLD", fill=(40, 40, 40))
    d.text((sz[0] + 30, 2), "NEW", fill=(200, 40, 40))
    cmp.save(os.path.join(OUT, f"cmp-{name}.png"))
print("done")
