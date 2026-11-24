# -*- coding: utf-8 -*-
"""用经典形象生成程序图标：裁头部做成多尺寸 ico，并输出预览图供目检。"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "assets", "skins", "default.png")
OUT_ICO = os.path.join(ROOT, "assets", "ui", "pet.ico")
OUT_PNG = os.path.join(ROOT, "assets", "ui", "icon_preview.png")

img = Image.open(SRC).convert("RGBA")
print("src:", img.size)

bbox = img.getbbox()
print("alpha bbox:", bbox)
x0, y0, x1, y1 = bbox
w, h = x1 - x0, y1 - y0

# 头肩：从主体顶部往下 0.30，宽度取身宽的 0.78 居中
head_h = int(h * 0.30)
cx = x0 + w // 2
side = int(min(w * 0.78, head_h * 1.15))
left = max(x0, cx - side // 2)
top = y0 - int(h * 0.004)
crop = img.crop((left, max(0, top), left + side, max(0, top) + side))
print("crop:", crop.size)

# 圆形底衬，避免透明图标在浅色任务栏上消失
canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
mask = Image.new("L", (side, side), 0)
from PIL import ImageDraw  # noqa: E402

d = ImageDraw.Draw(mask)
d.ellipse((2, 2, side - 2, side - 2), fill=235)
bg = Image.new("RGBA", (side, side), (18, 40, 66, 255))
canvas.paste(bg, (0, 0), mask)
canvas.alpha_composite(crop)

sizes = [16, 24, 32, 48, 64, 128, 256]
canvas.resize((256, 256), Image.LANCZOS).save(OUT_ICO, sizes=[(s, s) for s in sizes])
canvas.resize((256, 256), Image.LANCZOS).save(OUT_PNG)
print("saved:", OUT_ICO, OUT_PNG)
