# -*- coding: utf-8 -*-
"""把用户给的截图（带浅灰底 + 右上时间水印）做成干净透明立绘，并生成多档 ico。

用法：python tools/icon_from_shot.py <截图路径>
产物：assets/ui/qwhale.png（透明底原图）、assets/ui/icon_preview.png、assets/ui/pet.ico、assets/ui/avatar.png
"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "assets", "ui")


def strip_watermark(im):
    """截图右上角的"今天 17:5x"时间水印：直接把那块区域刷成背景白。"""
    im = im.copy()
    w, h = im.size
    draw = ImageDraw.Draw(im)
    draw.rectangle((int(w * 0.62), 0, w, int(h * 0.30)), fill=(255, 255, 255, 0))
    return im


def strip_guides(im):
    """截图里的横向虚线/分隔线：整行几乎全灰且有大量非白像素的行，刷成白底。"""
    arr = np.array(im.convert("RGBA"))
    h, w = arr.shape[:2]
    rgb = arr[:, :, :3].astype(int)
    nonwhite = (rgb < 240).any(axis=2).mean(axis=1)
    grayish = ((np.abs(rgb[:, :, 0] - rgb[:, :, 1]) < 8)
               & (np.abs(rgb[:, :, 1] - rgb[:, :, 2]) < 8)
               & (rgb[:, :, 0] > 140) & (rgb[:, :, 0] < 246)).mean(axis=1)
    hits = (nonwhite > 0.45) & (grayish > 0.45)
    for y in np.where(hits)[0]:
        arr[max(0, y - 1):y + 2, :, :3] = 255
    return Image.fromarray(arr, "RGBA")


def to_alpha(im, thresh=226):
    """从四边 flood fill 掉白/浅灰背景（含截图 #f5f5f5 边），只吃连通区，不伤内部白衣服。"""
    arr = np.array(im.convert("RGBA"))
    h, w = arr.shape[:2]
    near_white = ((arr[:, :, 0] >= thresh) & (arr[:, :, 1] >= thresh)
                  & (arr[:, :, 2] >= thresh))
    seen = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if near_white[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if near_white[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and near_white[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    arr[:, :, 3] = np.where(seen, 0, 255)
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getchannel("A").getbbox()
    return out.crop(bbox) if bbox else out



def robust_crop(im, min_px=3):
    """忽略整列/整行只有 1-2 个像素的噪声（截图的边框线、虚线尾巴）。"""
    a = np.array(im)[:, :, 3]
    cols = (a > 0).sum(axis=0)
    rows = (a > 0).sum(axis=1)
    xs = np.where(cols >= min_px)[0]
    ys = np.where(rows >= min_px)[0]
    if len(xs) == 0 or len(ys) == 0:
        return im
    return im.crop((int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1))
def make_icon(src, size=256):
    """深色圆底 + 主体居中，避免透明图标在浅色任务栏上糊掉。"""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse((0, 0, size - 1, size - 1), fill=(18, 40, 66, 255))
    inner = int(size * 0.86)
    w, h = src.size
    scale = min(inner / w, inner / h)
    rz = src.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    canvas.paste(rz, ((size - rz.width) // 2, (size - rz.height) // 2), rz)
    return canvas


def main(shot):
    im = Image.open(shot).convert("RGBA")
    im = strip_watermark(im)
    im = strip_guides(im)
    cut = robust_crop(to_alpha(im))
    # 立绘统一高度 512，存一份透明底原图
    w, h = cut.size
    big = cut.resize((max(1, round(w * 512 / h)), 512), Image.LANCZOS)
    big.save(os.path.join(UI, "qwhale.png"))
    print("qwhale.png", big.size)

    icon = make_icon(cut, 256)
    icon.save(os.path.join(UI, "icon_preview.png"))
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(os.path.join(UI, "pet.ico"), format="ICO", sizes=sizes)
    icon.resize((128, 128), Image.LANCZOS).save(os.path.join(UI, "avatar.png"))
    alpha = cut.getchannel("A")
    zero = sum(1 for v in alpha.getdata() if v == 0) / (alpha.width * alpha.height)
    print(f"icon ok sizes={len(sizes)} transparent={zero:.1%} corner={alpha.getpixel((0, 0))}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.expanduser("~"), "Desktop", "Snipaste_2026-11-24_17-53-43.png"))
