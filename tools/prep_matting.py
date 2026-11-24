# -*- coding: utf-8 -*-
"""把 _matting 下的 AI 抠图结果裁剪归一化回 assets，并输出 alpha 质检数据。"""
import os
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
STAGE = os.path.join(BASE, "_matting")
TARGET_H = 512

MAP = {
    "expressions_angry.png": "expressions/angry.png",
    "expressions_curious.png": "expressions/curious.png",
    "expressions_pat.png": "expressions/pat.png",
    "expressions_shy.png": "expressions/shy.png",
    "expressions_sleepy.png": "expressions/sleepy.png",
    "skins_blackgown.png": "skins/blackgown.png",
    "skins_blackred.png": "skins/blackred.png",
}


def autocrop(im, margin_ratio=0.06):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    w, h = im.size
    mx = int((r - l) * margin_ratio)
    my = int((b - t) * margin_ratio)
    l = max(0, l - mx); t = max(0, t - my)
    r = min(w, r + mx); b = min(h, b + my)
    return im.crop((l, t, r, b))


def normalize(im):
    im = autocrop(im)
    w, h = im.size
    scale = TARGET_H / h
    nw = max(1, round(w * scale))
    return im.resize((nw, TARGET_H), Image.LANCZOS)


def main():
    for src, dst in MAP.items():
        im = Image.open(os.path.join(STAGE, src)).convert("RGBA")
        im = normalize(im)
        im.save(os.path.join(BASE, dst))
        alpha = im.getchannel("A")
        lo = min(alpha.getpixel((2, 2)), alpha.getpixel((im.width - 3, 2)),
                 alpha.getpixel((2, im.height - 3)), alpha.getpixel((im.width - 3, im.height - 3)))
        transparent = sum(1 for v in alpha.getdata() if v == 0) / len(alpha.getdata())
        print(f"{dst} {im.size} corner_alpha={lo} transparent={transparent:.1%}")


if __name__ == "__main__":
    main()
