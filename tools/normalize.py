# -*- coding: utf-8 -*-
"""素材归一化：裁掉透明包围盒、留 14px 边距、高度归一到 512px，输出 RGBA PNG。

用法:
  python tools/normalize.py <输入png> <输出png> [--pad 14] [--height 512]
"""
import argparse
import os
import sys

from PIL import Image

TARGET_H = 512
PAD = 14


def normalize(src: str, dst: str, pad: int = PAD, height: int = TARGET_H) -> dict:
    im = Image.open(src).convert("RGBA")
    alpha = im.split()[3]
    bbox = alpha.getbbox()
    if bbox:
        l, t, r, b = bbox
        l = max(0, l - pad)
        t = max(0, t - pad)
        r = min(im.width, r + pad)
        b = min(im.height, b + pad)
        im = im.crop((l, t, r, b))
    scale = height / im.height
    new_w = max(1, round(im.width * scale))
    im = im.resize((new_w, height), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    im.save(dst, "PNG")
    corners = [im.getpixel((x, y))[3] for x, y in
               ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
    return {"size": im.size, "corner_alpha": corners, "bytes": os.path.getsize(dst)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--pad", type=int, default=PAD)
    ap.add_argument("--height", type=int, default=TARGET_H)
    args = ap.parse_args()
    info = normalize(args.src, args.dst, args.pad, args.height)
    print(info)
