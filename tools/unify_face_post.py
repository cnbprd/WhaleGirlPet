# -*- coding: utf-8 -*-
"""把 image_edit 输出的白底立绘处理成透明底素材，并生成对比图。"""
import io
import os
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet"
OUT = os.path.join(ROOT, "assets", "_matting", "face-unify")
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("dance", os.path.join(ROOT, "assets", "actions", "dance.png"),
     "https://aka.doubaocdn.com/s/2bJUnWCOSn"),
    ("sleep", os.path.join(ROOT, "assets", "expressions", "sleep.png"),
     "https://aka.doubaocdn.com/s/4N48vOYhAW"),
]


def fetch(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def cut_white(im: Image.Image, thresh: int = 232) -> Image.Image:
    """从四边 flood fill 掉与边缘连通的白底，保留被深色包围的白色（如围裙）。"""
    arr = np.asarray(im).astype(np.int16)
    near_white = (arr.min(axis=2) >= thresh).astype(np.uint8) * 255
    mask = Image.fromarray(near_white, "L")
    w, h = mask.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
             (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    for s in seeds:
        if mask.getpixel(s) == 255:
            ImageDraw.floodfill(mask, s, 128, thresh=0)
    alpha = Image.fromarray(np.where(np.asarray(mask) == 128, 0, 255).astype(np.uint8), "L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    out = im.copy().convert("RGBA")
    out.putalpha(alpha)
    return out


def board(size, cell=16):
    w, h = size
    b = Image.new("RGB", (w, h), (238, 238, 238))
    d = ImageDraw.Draw(b)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(210, 210, 210))
    return b


def compose(left: Image.Image, right: Image.Image, path: str):
    h = max(left.height, right.height)
    w = left.width + right.width + 24
    canvas = board((w, h + 28), 16)
    canvas.paste((255, 255, 255), (0, 0, w, h + 28))
    canvas = board((w, h + 28), 16)
    canvas.paste(left, (0, 14), left)
    canvas.paste(right, (left.width + 24, 14), right)
    d = ImageDraw.Draw(canvas)
    d.text((6, 2), "BEFORE", fill=(40, 40, 40))
    d.text((left.width + 30, 2), "AFTER", fill=(200, 40, 40))
    canvas.save(path)
    print("saved", path, canvas.size)


for name, src, url in JOBS:
    base = Image.open(src).convert("RGBA")
    sz = base.size
    raw = fetch(url).resize(sz, Image.LANCZOS)
    cut = cut_white(raw, 234)
    bbox = cut.getbbox()
    print(name, "size", sz, "bbox", bbox)
    raw.save(os.path.join(OUT, f"{name}-raw.png"))
    cut.save(os.path.join(OUT, f"{name}-cut.png"))
    compose(base, cut, os.path.join(OUT, f"cmp-{name}.png"))
