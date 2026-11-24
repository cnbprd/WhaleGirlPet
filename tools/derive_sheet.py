# -*- coding: utf-8 -*-
"""把母版派生的立绘裁成 267x512 透明底素材，并与原 default 立绘对比。"""
import io
import os
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet"
OUT = os.path.join(ROOT, "assets", "_matting")
URL = "https://aka.doubaocdn.com/s/mro6Saqmih"
TARGET = (267, 512)
SUFFIX = "-v2"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read()))


def cut_white(im, thresh=232):
    arr = np.asarray(im.convert("RGB")).astype(np.int16)
    near = (arr.min(axis=2) >= thresh).astype(np.uint8) * 255
    mask = Image.fromarray(near, "L")
    w, h = mask.size
    for s in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
              (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if mask.getpixel(s) == 255:
            ImageDraw.floodfill(mask, s, 128, thresh=0)
    alpha = Image.fromarray(np.where(np.asarray(mask) == 128, 0, 255).astype(np.uint8), "L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.5))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out


def board(size, cell=16):
    b = Image.new("RGB", size, (238, 238, 238))
    d = ImageDraw.Draw(b)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(205, 205, 205))
    return b


raw = fetch(URL)
print("mode:", raw.mode, "size:", raw.size, "has_alpha:", raw.mode in ("RGBA", "LA"))
has_alpha = raw.mode in ("RGBA", "LA") and np.asarray(raw.convert("RGBA"))[..., 3].min() < 250

if has_alpha:
    canvas = raw.convert("RGBA")
else:
    canvas = cut_white(raw)

bbox = canvas.getbbox()
print("bbox:", bbox)
crop = canvas.crop(bbox)
scale = TARGET[1] / crop.height
new_w = max(1, int(round(crop.width * scale)))
tw = min(TARGET[0], new_w)
resized = crop.resize((new_w, TARGET[1]), Image.LANCZOS)
sheet = Image.new("RGBA", (TARGET[0], TARGET[1]), (0, 0, 0, 0))
ox = (TARGET[0] - new_w) // 2
sheet.alpha_composite(resized, (max(0, ox), 0))
sheet.save(os.path.join(OUT, "derived-default" + SUFFIX + ".png"))
print("derived:", sheet.size, "alpha_min:", np.asarray(sheet)[..., 3].min())

base = Image.open(os.path.join(ROOT, "assets", "skins", "default.png")).convert("RGBA")
h = TARGET[1]
w = base.width + TARGET[0] + 24
cmp = board((w, h + 28))
cmp.paste(base, (0, 14), base)
cmp.paste(sheet, (base.width + 24, 14), sheet)
d = ImageDraw.Draw(cmp)
d.text((6, 2), "OLD", fill=(40, 40, 40))
d.text((base.width + 30, 2), "SHEET-DERIVED", fill=(200, 40, 40))
cmp.save(os.path.join(OUT, "cmp-derived.png"))
print("cmp:", cmp.size)
