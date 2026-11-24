# -*- coding: utf-8 -*-
"""合成 v2.1.0 预览图：直接用落盘的皮肤 PNG（富江脸版），四套形象 + 标题。"""
import os

from PIL import Image, ImageDraw, ImageFont

base = os.path.dirname(os.path.abspath(__file__))
skins = os.path.join(base, "assets", "skins")

items = [
    (os.path.join(skins, "default.png"), "成熟形态 · 蓝女仆"),
    (os.path.join(skins, "jk.png"), "日式学生制服"),
    (os.path.join(skins, "hanfu.png"), "汉服襦裙"),
    (os.path.join(base, "assets", "loli", "default.png"), "萝莉形态（第二形态）"),
]

W, H = 1440, 900
BG = (26, 31, 46)
card = (35, 42, 60)
canvas = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(canvas)

font_path = r"C:\Windows\Fonts\msyh.ttc"
try:
    title_font = ImageFont.truetype(font_path, 44)
    label_font = ImageFont.truetype(font_path, 26)
    sub_font = ImageFont.truetype(font_path, 22)
except OSError:
    title_font = label_font = sub_font = ImageFont.load_default()

draw.text((60, 44), "鲸鱼娘桌宠 · 大肥鱼  v2.1.0", font=title_font, fill=(233, 238, 250))
draw.text((62, 104), "富江脸 · 五家开源模型一键下载 · 方言语音 · 记忆知识库 · 安全体检 · 双形态",
          font=sub_font, fill=(150, 165, 195))

cell_w = 330
gap = 18
total = cell_w * 4 + gap * 3
x0 = (W - total) // 2
top = 170
img_h = 660

for i, (p, label) in enumerate(items):
    x = x0 + i * (cell_w + gap)
    draw.rounded_rectangle([x, top, x + cell_w, top + img_h + 66], radius=18, fill=card)
    if os.path.exists(p):
        im = Image.open(p).convert("RGBA")
        ratio = (img_h - 10) / im.height
        im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
        ox = x + (cell_w - im.width) // 2
        oy = top + 10 + (img_h - 10 - im.height) // 2
        canvas.paste(im, (ox, oy), im)
    tw = draw.textlength(label, font=label_font)
    draw.text((x + (cell_w - tw) / 2, top + img_h + 14), label, font=label_font, fill=(210, 220, 240))

out = os.path.join(base, "preview.png")
canvas.save(out)
print("preview saved:", out, canvas.size)
