# -*- coding: utf-8 -*-
"""重做 sleep 表情：去底 + 按"人物高度=站姿的 62%"重排到 512 高画布。

这样程序按图高缩放时，坐姿的人不会比站姿大一整圈。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import numpy as np
from PIL import Image

from bg_cut import clear_bg

root = r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet"
src = os.path.join(root, "assets", "_matting", "derived", "sleep-v3-raw.png")
dst_dir = os.path.join(root, "assets", "_matting", "derived")

TARGET_H = 512
BODY_RATIO = 0.62          # 坐姿人体高度占画布高度的比例

im = Image.open(src)
cut = clear_bg(im, feather=True)
a = np.asarray(cut)[..., 3]
print("raw alpha: min", int(a.min()), "transparent", round(float((a < 10).mean()), 3))

bbox = cut.getbbox()
print("bbox:", bbox)
body = cut.crop(bbox)

new_h = int(TARGET_H * BODY_RATIO)
new_w = max(1, int(body.width * new_h / body.height))
body = body.resize((new_w, new_h), Image.LANCZOS)

canvas = Image.new("RGBA", (new_w, TARGET_H), (0, 0, 0, 0))
canvas.paste(body, (0, TARGET_H - new_h), body)

p_out = os.path.join(dst_dir, "sleep-v3.png")
canvas.save(p_out)
a2 = np.asarray(canvas)[..., 3]
print("out:", canvas.size, "alpha_min", int(a2.min()),
      "transparent", round(float((a2 < 10).mean()), 3))

# 与 default 并排（白底）目检
def on_white(im, H=700):
    w = int(im.width * H / im.height)
    r = im.resize((w, H), Image.LANCZOS)
    bgc = Image.new("RGBA", (w, H), (255, 255, 255, 255))
    bgc.alpha_composite(r)
    return bgc.convert("RGB")

d = Image.open(os.path.join(root, "assets", "skins", "default.png")).convert("RGBA")
old = Image.open(os.path.join(root, "assets", "expressions", "sleep.png")).convert("RGBA")
new = Image.open(p_out).convert("RGBA")

parts = [(on_white(d), "default"), (on_white(old), "sleep OLD"), (on_white(new), "sleep NEW")]
W = sum(p[0].width for p in parts) + 40
H = 740
sheet = Image.new("RGB", (W, H), (235, 235, 235))
from PIL import ImageDraw
dr = ImageDraw.Draw(sheet)
x = 10
for img, tag in parts:
    sheet.paste(img, (x, 30))
    dr.text((x, 8), tag, fill=(0, 0, 0))
    x += img.width + 10
p_cmp = os.path.join(dst_dir, "cmp-sleep-v3.png")
sheet.save(p_cmp)
print("cmp:", p_cmp)
