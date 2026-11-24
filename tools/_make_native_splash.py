# -*- coding: utf-8 -*-
"""生成 PyInstaller 原生启动图（onefile 解压期顶住 1.5 秒空白用）。

原生 splash 只能是矩形图，做不出透明，所以配一张深色渐变卡：
中间是鲸鱼娘本人，下面一行「鲸鱼娘加载中」和三个呼吸点。
输出：assets/ui/splash_native.png（360×500）
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "assets", "skins", "default.png")
OUT = os.path.join(ROOT, "assets", "ui", "splash_native.png")

W, H = 360, 500
TOP = (32, 54, 82)
BOT = (10, 14, 20)


def gradient():
    img = Image.new("RGB", (1, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.point((0, y), tuple(int(TOP[i] * (1 - t) + BOT[i] * t) for i in range(3)))
    return img.resize((W, H), Image.BICUBIC)


def main():
    base = gradient().convert("RGBA")
    # 人物后面的柔光
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r, a in ((150, 26), (110, 30), (74, 34)):
        gd.ellipse([W // 2 - r, 90 - r // 2, W // 2 + r, 90 + r * 1.4], fill=(150, 205, 255, a))
    base = Image.alpha_composite(base, glow)

    art = Image.open(ART).convert("RGBA")
    art_h = 340
    art_w = int(art.width * art_h / art.height)
    art = art.resize((art_w, art_h), Image.LANCZOS)
    ax = (W - art_w) // 2
    ay = 380 - art_h
    base.alpha_composite(art, (ax, ay))

    d = ImageDraw.Draw(base)
    font = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 20)
    text = "鲸鱼娘加载中"
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2 - 8, 428), text, font=font, fill=(226, 236, 248, 245))
    for i in range(3):
        cx = (W - tw) / 2 + tw + 6 + i * 11
        d.ellipse([cx, 438, cx + 6, 444], fill=(120, 176, 236, 220))

    base.convert("RGB").save(OUT)
    print("saved", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
