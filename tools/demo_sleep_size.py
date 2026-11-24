# -*- coding: utf-8 -*-
"""把新旧 sleep 立绘按程序的显示尺寸合成到同一张桌面截图上，做直观对比。"""
import os
from PIL import Image, ImageDraw

root = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet"
bg_path = os.path.join(root, "assets", "_matting", "vid2", "big_12_0.png")
old_path = os.path.join(root, "assets", "_raw", "backup_20261124", "expressions-sleep-v2.png")
new_path = os.path.join(root, "assets", "expressions", "sleep.png")

SCALE = 0.947  # 与 test_flash 实测一致：512 高立绘显示 485
bg = Image.open(bg_path).convert("RGB")
W, H = bg.size


def place(canvas, sprite_path, cx, bottom_y):
    s = Image.open(sprite_path).convert("RGBA")
    w = int(s.width * SCALE)
    h = int(s.height * SCALE)
    s = s.resize((w, h), Image.LANCZOS)
    canvas.paste(s, (cx - w // 2, bottom_y - h), s)
    return w, h


left = bg.copy()
wl, hl = place(left, old_path, 1050, 820)

right = bg.copy()
wr, hr = place(right, new_path, 1050, 820)

sheet = Image.new("RGB", (W, H * 2 + 50), (20, 20, 20))
sheet.paste(left, (0, 30))
sheet.paste(right, (0, H + 60))
dr = ImageDraw.Draw(sheet)
dr.text((12, 8), f"OLD sleep  {wl}x{hl}", fill=(255, 220, 120))
dr.text((12, H + 38), f"NEW sleep  {wr}x{hr}  (人物高度=站姿的 62%)", fill=(140, 255, 170))

out = os.path.join(root, "assets", "_matting", "vid2", "sleep_size_compare.png")
sheet.save(out)
print(out, sheet.size)
