# -*- coding: utf-8 -*-
"""深/浅底对比抽查。"""
import os
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
OUT = os.path.join(os.path.dirname(BASE), "check-dark.png")
names = ["skins/blackgown.png", "skins/blackred.png", "expressions/curious.png", "expressions/pat.png"]

cells = []
for bg in [(40, 40, 46), (235, 235, 238)]:
    row = Image.new("RGB", (4 * 300, 340), bg)
    for i, n in enumerate(names):
        im = Image.open(os.path.join(BASE, n)).convert("RGBA")
        im.thumbnail((280, 300), Image.LANCZOS)
        row.paste(im, (i * 300 + (300 - im.width) // 2, 20), im)
    cells.append(row)

sheet = Image.new("RGB", (4 * 300, 680), (128, 128, 128))
sheet.paste(cells[0], (0, 0)); sheet.paste(cells[1], (0, 340))
sheet.save(OUT)
print(OUT)
