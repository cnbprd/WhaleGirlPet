# -*- coding: utf-8 -*-
"""把桌面那张白底截图做成多尺寸 .ico：
1) 从四边向内 flood fill 掉近白背景（只删与边缘连通的白，鲸鱼身上的白不会被误删）
2) 按主体包围盒裁切并居中成正方形，留 8% 边距
3) 输出 16/24/32/48/64/128/256 七档 ico
"""
import os
import sys
from collections import deque

from PIL import Image, ImageFilter

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "_matting", "desktop_icon_src.png")
DST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "ui", "pet_flat.ico")
PREVIEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "_matting", "icon_preview.png")


def remove_white(im: Image.Image, thr: int = 238) -> Image.Image:
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    vis = bytearray(w * h)
    q = deque()

    def near_white(x, y):
        r, g, b, _ = px[x, y]
        return r >= thr and g >= thr and b >= thr

    for x in range(w):
        for y in (0, h - 1):
            if not vis[y * w + x] and near_white(x, y):
                vis[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not vis[y * w + x] and near_white(x, y):
                vis[y * w + x] = 1
                q.append((x, y))

    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not vis[ny * w + nx] and near_white(nx, ny):
                vis[ny * w + nx] = 1
                q.append((nx, ny))

    a = im.getchannel("A").load()
    cleared = 0
    for i in range(w * h):
        if vis[i]:
            x, y = i % w, i // w
            px[x, y] = (px[x, y][0], px[x, y][1], px[x, y][2], 0)
            cleared += 1
    return im, cleared


def main():
    im = Image.open(SRC)
    cut, cleared = remove_white(im)
    print("去背像素", cleared, "/", cut.size[0] * cut.size[1])

    # 轻微羽化边缘，避免锯齿
    alpha = cut.getchannel("A").filter(ImageFilter.GaussianBlur(0.6))
    cut.putalpha(alpha)

    bbox = alpha.getbbox()
    print("主体包围盒", bbox)
    body = cut.crop(bbox)
    bw, bh = body.size

    side = max(bw, bh)
    pad = int(side * 0.08)
    canvas = Image.new("RGBA", (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
    canvas.alpha_composite(body, ((canvas.width - bw) // 2, (canvas.height - bh) // 2))

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    big = canvas.resize((256, 256), Image.LANCZOS)
    big.save(DST, format="ICO",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    big.save(PREVIEW)
    print("输出", DST, os.path.getsize(DST), "bytes")


if __name__ == "__main__":
    sys.exit(main())
