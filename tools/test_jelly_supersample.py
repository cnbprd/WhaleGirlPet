# -*- coding: utf-8 -*-
"""v3.0.22：果冻回弹 + alpha 2 倍超采样 的量化回归。

    python tools/test_jelly_supersample.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402

import pet_window as pw  # noqa: E402

P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print(f"  ok   {name} {extra}")
    else:
        F += 1
        print(f"  FAIL {name} {extra}")


def alpha_stats(img: QImage):
    """边缘平滑度：统计 (0,255) 之间的 alpha 取值数、以及相邻像素 alpha 的平均跳变。"""
    vals, jumps = set(), []
    w, h = img.width(), img.height()
    for y in range(h):
        for x in range(w - 1):
            a1 = (img.pixel(x, y) >> 24) & 0xFF
            a2 = (img.pixel(x + 1, y) >> 24) & 0xFF
            if 0 < a1 < 255:
                vals.add(a1)
            if abs(a1 - a2) >= 1:
                jumps.append(abs(a1 - a2))
    mid = sum(J <= 24 for J in jumps)
    hard = sum(J >= 128 for J in jumps)
    return len(vals), (sum(jumps) / len(jumps) if jumps else 0), mid, hard


def main():
    print("[1] 果冻回弹曲线")
    ck("起手为 1（无跳变）", pw.jelly_scale(0.0) == (1.0, 1.0), str(pw.jelly_scale(0.0)))
    peak = max(abs(pw.jelly_scale(t / 1000)[0] - 1) for t in range(0, 550, 5))
    ck("峰值在 3%~9% 之间（可见但不夸张）", 0.03 <= peak <= 0.09, f"{peak * 100:.1f}%")
    s1 = pw.jelly_scale(0.12)
    s2 = pw.jelly_scale(0.30)
    ck("振幅随时间衰减", abs(s1[0] - 1) > abs(s2[0] - 1) - 0.0,
       f"0.12s={abs(s1[0]-1)*100:.1f}% / 0.30s={abs(s2[0]-1)*100:.1f}%")
    ck("结束后归位", pw.jelly_scale(0.56) == (1.0, 1.0) and pw.jelly_scale(9) == (1.0, 1.0))
    vol = [abs(x * y - 1) for x, y in (pw.jelly_scale(t / 1000) for t in range(0, 550, 5))]
    ck("体积近似守恒（|sx*sy-1| ≤ 0.004）", max(vol) <= 0.004, f"max={max(vol):.5f}")

    print("[2] alpha 边缘：原图放大 vs 2 倍超采样源")
    from PIL import Image
    src_path = os.path.join(ROOT, "assets", "skins", "default.png")
    x2_path = os.path.join(ROOT, "assets", "skins", "default@2x.png")
    ck("2× 素材已生成", os.path.exists(x2_path))
    im1 = Image.open(src_path).convert("RGBA")
    im2 = Image.open(x2_path).convert("RGBA")
    ck("2× 尺寸正好翻倍", im2.size == (im1.width * 2, im1.height * 2),
       f"{im1.size} → {im2.size}")

    def mid_alpha(img):
        """半透明边缘像素数（alpha 在 40~215）：超采样会让这条过渡带更宽。"""
        a = img.getchannel("A")
        hist = a.histogram()
        return sum(hist[40:216])

    def edge_jump_pct(img):
        """逐行找左边缘，统计相邻像素 alpha 跳变 ≥96 的行占比 —— 台阶的直接指标。"""
        a = img.getchannel("A")
        w, h = a.size
        px = a.load()
        jumps = rows = 0
        for y in range(10, h - 10):
            edge = None
            for x in range(w):
                if px[x, y] > 8:
                    edge = x
                    break
            if edge is None or edge + 1 >= w:
                continue
            rows += 1
            if abs(px[edge, y] - px[min(w - 1, edge + 1), y]) >= 96:
                jumps += 1
        return jumps / max(1, rows) * 100

    w, h = int(im1.width * 1.6), int(im1.height * 1.6)
    one = im1.resize((w, h), Image.BILINEAR)
    two = im2.resize((w, h), Image.BILINEAR)   # 模拟 Qt 的平滑缩放（双线性）
    m1, m2 = mid_alpha(one), mid_alpha(two)
    j1, j2 = edge_jump_pct(one), edge_jump_pct(two)
    print(f"    原图放大：半透明边缘 {m1} px｜2× 源压回：{m2} px")
    print(f"    台阶率：原图放大 {j1:.1f}%｜2× 源 {j2:.1f}%")
    ck("2× 源把边缘台阶压到 ≤ 5%", j2 <= 5.0, f"{j2:.1f}%")
    ck("比原图直放大明显更好", j2 <= j1 * 0.7 or j1 < 5,
       f"{j1:.1f}% → {j2:.1f}%")

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
