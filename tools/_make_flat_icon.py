# -*- coding: utf-8 -*-
"""生成大肥鱼（Q 版鲸鱼娘）透明底图标：托盘、窗口、菜单项都用它。
产物：assets/ui/pet_flat.ico + pet_flat_256.png
"""
import os

from PIL import Image

ROOT = r"F:\WhaleGirlPet"
SRC = os.path.join(ROOT, "assets", "ui", "qwhale.png")
OUT_ICO = os.path.join(ROOT, "assets", "ui", "pet_flat.ico")
OUT_PNG = os.path.join(ROOT, "assets", "ui", "pet_flat_256.png")

im = Image.open(SRC).convert("RGBA")
bbox = im.getbbox()
im = im.crop(bbox)

side = 256
inner = 248
w = int(im.width * inner / im.height)
r = im.resize((w, inner), Image.LANCZOS)
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
canvas.paste(r, ((side - w) // 2, (side - inner) // 2), r)
canvas.save(OUT_PNG)
canvas.save(OUT_ICO, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("saved", OUT_ICO, os.path.getsize(OUT_ICO), "bytes;", OUT_PNG)
