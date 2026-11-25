# -*- coding: utf-8 -*-
"""v3.0.26 展示图：裙摆/尾巴分层在 -4° / 0° / +4° 的静止与摆动对比。

运行：.venv\\Scripts\\python.exe tools\\make_secondary_preview.py
产出：docs/secondary_v326.png
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import secondary as secondary_mod  # noqa: E402
from paths import asset_path  # noqa: E402


def render(skin, angle):
    orig = QPixmap(asset_path("skins/" + skin + ".png"))
    w, h = orig.width(), orig.height()
    sec = secondary_mod.SecondaryMotion(1.0)
    sec.set_skin(skin, False)
    for s in sec.springs.values():
        s.angle = angle
        s.vel = 0.0
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.translate(w // 2, h)
    p.drawPixmap(QRect(-w // 2, -h, w, h), orig)
    sec.paint(p, w, h)
    p.end()
    return img


def main():
    app = QApplication(sys.argv)
    skins = [("default", "Maid"), ("jk", "JK uniform")]
    angles = (-4.0, 0.0, 4.0)
    cell_w, cell_h = 290, 240
    header = 64
    out = QImage(cell_w * 3 + 40, header + cell_h * 2 + 24, QImage.Format_ARGB32)
    out.fill(QColor("#f2f4f8"))
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    for row, (skin, _label) in enumerate(skins):
        for col, angle in enumerate(angles):
            im = render(skin, angle)
            crop = im.copy(0, max(0, 175), im.width(), 230)
            x = 20 + col * cell_w
            y = header + row * cell_h + 28
            p.drawImage(QRect(x, y, cell_w - 20, cell_h - 34), crop)
    p.end()
    path = os.path.join(ROOT, "docs", "secondary_v326.png")
    out.save(path)

    # Qt 的 offscreen 字体库不一定有雅黑，标签改用 Pillow + Arial 画，避免出现方块
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        fb = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 19)
        fs = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 12)
    except OSError:
        fb = fs = ImageFont.load_default()
    d.text((20, 14), "v3.0.26  skirt / tail alpha layers + Verlet spring", font=fb, fill=(31, 42, 68))
    d.text((20, 40), "full base + moving layer; no hole, no white seam; inertia drives the spring",
           font=fs, fill=(91, 102, 128))
    for row, (_skin, label) in enumerate(skins):
        y = header + row * cell_h + 6
        d.text((20, y), label, font=fs, fill=(56, 68, 94))
        for col, angle in enumerate(angles):
            x = 20 + col * cell_w
            d.text((x, y + 12), "%+.0f deg" % angle, font=fs, fill=(132, 144, 168))
    im.save(path)
    print("saved docs/secondary_v326.png")


if __name__ == "__main__":
    main()
