# -*- coding: utf-8 -*-
"""裁 8 套皮肤的头部区域放大，检查刘海是否遮眼、泪痣是否可见。"""
import os

from PIL import Image

base = os.path.dirname(os.path.abspath(__file__))
skins = os.path.join(base, "assets", "skins")
files = ["default.png", "jk.png", "hanfu.png", "longmaid.png",
         "blackgown.png", "blackgreen.png", "blackred.png"]

crops = []
for f in files:
    p = os.path.join(skins, f)
    im = Image.open(p).convert("RGBA")
    w, h = im.size
    box = (int(w * 0.24), int(h * 0.02), int(w * 0.78), int(h * 0.26))
    c = im.crop(box)
    ratio = 360 / c.height
    c = c.resize((int(c.width * ratio), 360), Image.LANCZOS)
    crops.append(c)

lp = os.path.join(base, "assets", "loli", "default.png")
im = Image.open(lp).convert("RGBA")
w, h = im.size
c = im.crop((int(w * 0.2), int(h * 0.03), int(w * 0.8), int(h * 0.34)))
ratio = 360 / c.height
crops.append(c.resize((int(c.width * ratio), 360), Image.LANCZOS))

pad = 10
W = sum(x.width for x in crops) + pad * (len(crops) + 1)
H = 360 + pad * 2
canvas = Image.new("RGB", (W, H), (245, 245, 245))
x = pad
for c in crops:
    canvas.paste(c, (x, pad), c)
    x += c.width + pad
out = os.path.join(base, "assets", "_matting", "tomie-heads.png")
canvas.save(out)
print("saved:", out, canvas.size)
