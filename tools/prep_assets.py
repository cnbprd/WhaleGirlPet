# -*- coding: utf-8 -*-
"""
素材预处理：
1. RGB 实底图从四角洪水填充去背（白/黑底），输出 RGBA；
2. 裁剪透明边距，留 6% 边距；
3. 统一缩放到高 512px，按比例居中放到透明画布。
原始未处理图备份到 assets/_raw/。
"""
import os
import shutil
import collections
from PIL import Image

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
RAW = os.path.join(BASE, "_raw")
TARGET_H = 512
TOL = 30  # 背景色容差


def bg_color(im: Image.Image):
    px = im.convert("RGB")
    w, h = px.size
    samples = [px.getpixel(p) for p in [
        (2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3),
        (w // 2, 2), (w // 2, h - 3), (2, h // 2), (w - 3, h // 2)]]
    # 取出现次数最多的颜色作为背景
    return max(set(samples), key=samples.count)


def dist(c1, c2):
    return sum(abs(a - b) for a, b in zip(c1, c2))


def flood_key(im: Image.Image, bg, tol=TOL):
    rgb = im.convert("RGB")
    w, h = rgb.size
    mask = bytearray(w * h)  # 1 = 背景待删
    q = collections.deque()

    def push(x, y):
        i = y * w + x
        if not mask[i] and dist(rgb.getpixel((x, y)), bg) <= tol:
            mask[i] = 1
            q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                push(nx, ny)

    out = im.convert("RGBA")
    data = out.getdata()
    new = []
    for i, p in enumerate(data):
        if mask[i]:
            new.append((p[0], p[1], p[2], 0))
        else:
            new.append(p)
    out.putdata(new)
    return out


def autocrop(im: Image.Image, margin_ratio=0.06):
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


def normalize(im: Image.Image):
    im = autocrop(im)
    w, h = im.size
    scale = TARGET_H / h
    nw = max(1, round(w * scale))
    im = im.resize((nw, TARGET_H), Image.LANCZOS)
    canvas = Image.new("RGBA", (nw, TARGET_H), (0, 0, 0, 0))
    canvas.paste(im, (0, 0), im)
    return canvas


def main():
    os.makedirs(RAW, exist_ok=True)
    for root, _, files in os.walk(BASE):
        if os.path.abspath(root) == os.path.abspath(RAW):
            continue
        for name in files:
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, BASE)
            shutil.copy2(path, os.path.join(RAW, rel.replace(os.sep, "_")))
            im = Image.open(path)
            if im.mode == "RGB":
                bg = bg_color(im)
                im = flood_key(im, bg)
            else:
                im = im.convert("RGBA")
            im = normalize(im)
            im.save(path)
            print("ok", rel, im.size)


if __name__ == "__main__":
    main()
