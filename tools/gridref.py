# -*- coding: utf-8 -*-
"""给立绘叠坐标网格，用于量取骨骼枢轴（肩/肘/髋/膝/踝）。"""
import os
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
scale = 2
src = r"F:\WhaleGirlPet\assets\skins\default.png"
pix = QPixmap(src)
W, H = pix.width(), pix.height()
img = QImage((W + 40) * scale, (H + 40) * scale, QImage.Format_ARGB32)
img.fill(QColor(255, 255, 255))
p = QPainter(img)
p.setRenderHint(QPainter.SmoothPixmapTransform)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f):
        QFontDatabase.addApplicationFont(f)
        break
fnt = QFont()
fnt.setPointSize(7)
p.setFont(fnt)
p.scale(scale, scale)
p.translate(20, 20)
p.drawPixmap(0, 0, pix)
p.setPen(QColor(0, 150, 220, 160))
for x in range(0, W + 1, 20):
    p.drawLine(x, 0, x, H)
    p.drawText(QRect(x + 1, 2, 18, 10), Qt.AlignLeft, str(x))
for y in range(0, H + 1, 20):
    p.drawLine(0, y, W, y)
    p.drawText(QRect(2, y + 1, 18, 10), Qt.AlignLeft, str(y))
p.end()
out = r"F:\WhaleGirlPet\docs\rig_grid_default.png"
img.save(out)
print("网格图:", out, W, "x", H)
