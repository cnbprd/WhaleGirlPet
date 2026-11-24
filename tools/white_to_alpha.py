# -*- coding: utf-8 -*-
"""白底立绘转透明底：仅从画面四边向内 flood fill 白色连通区，不碰内部白色衣服。"""
import os
import sys
from collections import deque

import numpy as np
from PIL import Image


def white_to_alpha(src, dst, thresh=244):
    im = Image.open(src).convert("RGBA")
    arr = np.array(im)
    h, w = arr.shape[:2]
    whiteish = ((arr[:, :, 0] >= thresh) & (arr[:, :, 1] >= thresh)
                & (arr[:, :, 2] >= thresh))
    seen = np.zeros((h, w), dtype=bool)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if whiteish[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if whiteish[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and whiteish[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    arr[:, :, 3] = np.where(seen, 0, 255)
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getchannel("A").getbbox()
    if bbox:
        out = out.crop(bbox)
    # 高度统一到 512（与项目其它皮肤一致）
    w2, h2 = out.size
    scale = 512 / h2
    out = out.resize((max(1, round(w2 * scale)), 512), Image.LANCZOS)
    out.save(dst)
    alpha = out.getchannel("A")
    transparent = alpha.getdata()
    zero = sum(1 for v in transparent if v == 0) / len(transparent)
    corner = min(alpha.getpixel((1, 1)), alpha.getpixel((out.width - 2, 1)),
                 alpha.getpixel((1, out.height - 2)), alpha.getpixel((out.width - 2, out.height - 2)))
    print(f"{dst} {out.size} corner_alpha={corner} transparent={zero:.1%}")


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    white_to_alpha(src, dst)
