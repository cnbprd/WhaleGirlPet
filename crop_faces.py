# -*- coding: utf-8 -*-
"""下载富江版立绘，裁头部区域放大，拼一张对比图目检。"""
import io
import os
import urllib.request

from PIL import Image, ImageDraw, ImageFont

base = os.path.dirname(os.path.abspath(__file__))
mat = os.path.join(base, "assets", "_matting")

ITEMS = [
    ("https://aka.doubaocdn.com/s/4etUgQzaTo", "tomie-mature.png", "成熟·女仆"),
    ("https://aka.doubaocdn.com/s/klmscsrBf9", "tomie-jk.png", "JK 制服"),
    ("https://aka.doubaocdn.com/s/NVy8nFIRa6", "tomie-hanfu.png", "汉服"),
    ("https://aka.doubaocdn.com/s/JO4JNM9xrs", "tomie-loli.png", "萝莉形态"),
]

UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url: str, path: str):
    if os.path.exists(path) and os.path.getsize(path) > 100_000:
        return Image.open(path)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return Image.open(io.BytesIO(data))


faces = []
for url, name, label in ITEMS:
    im = fetch(url, os.path.join(mat, name)).convert("RGBA")
    w, h = im.size
    # 头部大致在上方 4%~34%，水平居中 60% 宽
    box = (int(w * 0.24), int(h * 0.03), int(w * 0.76), int(h * 0.30))
    face = im.crop(box)
    target_h = 560
    face = face.resize((int(face.width * target_h / face.height), target_h), Image.LANCZOS)
    faces.append((face, label, (w, h)))

cell_w = 430
canvas = Image.new("RGB", (cell_w * 4, 700), (24, 28, 40))
d = ImageDraw.Draw(canvas)
try:
    f = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)
except OSError:
    f = ImageFont.load_default()

for i, (face, label, size) in enumerate(faces):
    x = i * cell_w + (cell_w - face.width) // 2
    canvas.paste(face, (x, 20), face)
    tw = d.textlength(label, font=f)
    d.text((i * cell_w + (cell_w - tw) / 2, 610), f"{label} {size[0]}x{size[1]}", font=f, fill=(215, 222, 238))

out = os.path.join(mat, "tomie-faces.png")
canvas.save(out)
print("faces:", out)
