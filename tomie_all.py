# -*- coding: utf-8 -*-
"""八套皮肤落盘后目检图：4×2 网格，浅底，检查脸型/泪痣是否统一。"""
import os

from PIL import Image, ImageDraw

base = os.path.dirname(os.path.abspath(__file__))
skins = os.path.join(base, "assets", "skins")
loli = os.path.join(base, "assets", "loli", "default.png")

items = [
    (os.path.join(skins, "default.png"), "default 蓝女仆"),
    (os.path.join(skins, "jk.png"), "jk 学生制服"),
    (os.path.join(skins, "hanfu.png"), "hanfu 汉服"),
    (os.path.join(skins, "longmaid.png"), "longmaid 长裙女仆"),
    (os.path.join(skins, "blackgown.png"), "blackgown 暗夜礼服"),
    (os.path.join(skins, "blackgreen.png"), "blackgreen 墨绿"),
    (os.path.join(skins, "blackred.png"), "blackred 绯红"),
    (loli, "loli 萝莉"),
]

CELL = 300
PAD = 16
COLS = 4
ROWS = 2
W = COLS * CELL + (COLS + 1) * PAD
H = ROWS * (CELL + 30) + (ROWS + 1) * PAD
canvas = Image.new("RGB", (W, H), (240, 238, 234))
draw = ImageDraw.Draw(canvas)

for i, (p, label) in enumerate(items):
    r, c = divmod(i, COLS)
    x = PAD + c * (CELL + PAD)
    y = PAD + r * (CELL + 30 + PAD)
    if os.path.exists(p):
        im = Image.open(p).convert("RGBA")
        ratio = min(CELL / im.width, CELL / im.height)
        im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
        canvas.paste(im, (x + (CELL - im.width) // 2, y), im)
    draw.text((x + 6, y + CELL + 6), label, fill=(40, 40, 40))

out = os.path.join(base, "assets", "_matting", "tomie-all.png")
canvas.save(out)
print("saved:", out, canvas.size)
