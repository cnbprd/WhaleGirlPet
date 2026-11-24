# -*- coding: utf-8 -*-
"""把素材拼到中性灰底上做质检，输出 contact-sheet.png。"""
import os
import glob
from PIL import Image, ImageDraw

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
OUT = os.path.join(os.path.dirname(BASE), "contact-sheet.png")

files = sorted(glob.glob(os.path.join(BASE, "**", "*.png"), recursive=True))
cell_w, cell_h = 300, 360
cols = 5
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (128, 128, 130))
d = ImageDraw.Draw(sheet)

for i, f in enumerate(files):
    im = Image.open(f).convert("RGBA")
    im.thumbnail((cell_w - 20, cell_h - 40), Image.LANCZOS)
    x = (i % cols) * cell_w + (cell_w - im.width) // 2
    y = (i // cols) * cell_h + 20
    sheet.paste(im, (x, y), im)
    d.text(((i % cols) * cell_w + 8, (i // cols) * cell_h + 4),
           os.path.relpath(f, BASE), fill=(255, 255, 0))

sheet.save(OUT)
print(OUT)
