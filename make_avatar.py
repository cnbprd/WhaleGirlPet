# -*- coding: utf-8 -*-
"""聊天头像：复用图标头肩裁切（已验证效果好），缩放到 128px。"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "assets", "ui", "icon_preview.png")
OUT = os.path.join(ROOT, "assets", "ui", "avatar.png")

img = Image.open(SRC).convert("RGBA")
img.resize((128, 128), Image.LANCZOS).save(OUT)
print("saved", OUT, img.size)
