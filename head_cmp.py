# -*- coding: utf-8 -*-
"""把基准立绘与新生成的成熟立绘的头部裁出来横向拼接，用于目检脸型变化。"""
import os
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT, exist_ok=True)
URLS = {
    "base": "https://aka.doubaocdn.com/s/4etUgQzaTo",
    "newA": "https://aka.doubaocdn.com/s/gHuxWk52br",
    "newB": "https://aka.doubaocdn.com/s/PBgzC6bge0",
}
heads = []
for k, u in URLS.items():
    p = os.path.join(OUT, f"head_{k}.png")
    if not os.path.exists(p):
        urllib.request.urlretrieve(u, p)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    # 头部区域：顶部 4%~23%，水平居中 42% 宽
    top = int(h * 0.04)
    side_h = int(h * 0.19)
    cw = int(w * 0.46)
    left = (w - cw) // 2
    crop = im.crop((left, top, left + cw, top + side_h)).resize((460, 460), Image.LANCZOS)
    heads.append(crop)
canvas = Image.new("RGB", (460 * len(heads), 460), (240, 242, 246))
for i, c in enumerate(heads):
    canvas.paste(c, (460 * i, 0))
canvas.save(os.path.join(OUT, "v25-face-compare.png"))
print("saved", canvas.size)
