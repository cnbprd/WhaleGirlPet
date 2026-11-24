# -*- coding: utf-8 -*-
"""把生成图转成真透明底。

背景色不固定：宿主转码后可能是「黑底 RGB」、也可能是「白底 RGB」、或者干脆保留 RGBA。
这里先采样画布四边推断底色，再用「逐行游程 + 并查集」只清掉与边缘连通的那一块，
被人物包住的同色区域（白围裙 / 深色靴子）会被保留。

PIL 13 的 ImageDraw.floodfill 实测不生效（不报错也不改像素），所以不用它。
"""
import numpy as np
from PIL import Image, ImageFilter


def _runs_mask(bgmask: np.ndarray):
    """逐行把 bgmask 切成连续段，返回 (runs, row_runs)。"""
    h, w = bgmask.shape
    runs = []
    row_runs = []
    for y in range(h):
        row = bgmask[y]
        idx = []
        x = 0
        while x < w:
            if row[x]:
                x0 = x
                while x < w and row[x]:
                    x += 1
                idx.append(len(runs))
                runs.append((y, x0, x - 1))
            else:
                x += 1
        row_runs.append(idx)
    return runs, row_runs


def _border_ids(runs, row_runs, w, h):
    """并查集合并上下相邻段，返回所有落到画布边缘的连通域根节点。"""
    parent = list(range(len(runs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for y in range(1, h):
        for i in row_runs[y]:
            _, a0, a1 = runs[i]
            for j in row_runs[y - 1]:
                _, b0, b1 = runs[j]
                if a0 <= b1 + 1 and b0 <= a1 + 1:
                    ra, rb = find(i), find(j)
                    if ra != rb:
                        parent[rb] = ra

    border = set()
    for i in row_runs[0]:
        border.add(find(i))
    for i in row_runs[h - 1]:
        border.add(find(i))
    for i, (_, x0, x1) in enumerate(runs):
        if x0 == 0 or x1 == w - 1:
            border.add(find(i))
    return border, find


def clear_bg(im: Image.Image, mode: str = "auto", feather: bool = True) -> Image.Image:
    rgb = im.convert("RGB")
    w, h = rgb.size
    arr = np.asarray(rgb).astype(np.int16)

    edge = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    med = np.median(edge, axis=0)               # 边缘中位色 ≈ 底色

    if mode == "auto":
        mode = "dark" if float(med.mean()) < 110 else "light"

    if mode == "dark":
        bgmask = (arr.max(axis=2) <= 30)        # 近纯黑
    else:
        bgmask = (arr.min(axis=2) >= 238)       # 近纯白

    runs, row_runs = _runs_mask(bgmask)
    if not runs:
        return rgb.convert("RGBA")

    border, find = _border_ids(runs, row_runs, w, h)
    alpha = np.full((h, w), 255, dtype=np.uint8)
    for i, (y, x0, x1) in enumerate(runs):
        if find(i) in border:
            alpha[y, x0:x1 + 1] = 0

    out = rgb.convert("RGBA")
    a = Image.fromarray(alpha, "L")
    if feather:
        a = a.filter(ImageFilter.GaussianBlur(0.6))
    out.putalpha(a)
    return out


if __name__ == "__main__":
    import io
    import urllib.request

    url = "https://aka.doubaocdn.com/s/EdBvU9sqdk"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    im = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=90).read()))
    res = clear_bg(im)
    a = np.asarray(res)[..., 3]
    print("alpha_min", int(a.min()), "transparent", round(float((a < 10).mean()), 3), "bbox", res.getbbox())
    res.save(r"C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet\assets\_matting\derived\test-longmaid.png")
