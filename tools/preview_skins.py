# -*- coding: utf-8 -*-
"""把全部皮肤 + 表情渲染成一张预览图，目检「是不是同一张脸」。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt

from paths import EXPRESSIONS, SKINS, asset_path

OUT = os.path.join(ROOT, "assets", "_matting")
app = QApplication([])

H = 210
GAP = 10
LABEL = 18

items = [(label, rel) for label, rel in [(v[0], v[1]) for v in SKINS.values()]]
items += [("表情:" + k, v) for k, v in EXPRESSIONS.items()]

loaded = []
for label, rel in items:
    pm = QPixmap(asset_path(rel))
    if pm.isNull():
        print("missing", rel)
        continue
    loaded.append((label, pm.scaledToHeight(H, Qt.SmoothTransformation)))

w = sum(p.width() for _, p in loaded) + GAP * (len(loaded) - 1) + 20
h = H + LABEL + 20
canvas = QPixmap(w, h)
canvas.fill(QColor(246, 244, 240))
p = QPainter(canvas)
p.setPen(QColor(40, 40, 40))
p.setFont(QFont("Microsoft YaHei", 7))
x = 10
for label, pm in loaded:
    p.drawPixmap(x, LABEL + 6, pm)
    p.drawText(x, 12, label)
    x += pm.width() + GAP
p.end()
path = os.path.join(OUT, "skins-preview.png")
canvas.save(path)
print("saved", path, canvas.width(), "x", canvas.height(), "| items", len(loaded))
