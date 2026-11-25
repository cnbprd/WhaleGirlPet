# -*- coding: utf-8 -*-
"""档 B 原型：从单张立绘切部件 + 关节旋转，验证接缝质量（先只做腿）。"""
import os
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
SRC = r"F:\WhaleGirlPet\assets\skins\default.png"
src = QPixmap(SRC)
W, H = src.width(), src.height()
print("立绘:", W, "x", H)


class Bone:
    def __init__(self, name, rect, pivot, children=(), z=0.0):
        self.name = name
        self.rect = QRect(*rect)
        self.slice = src.copy(self.rect)
        self.px, self.py = pivot
        self.children = list(children)
        self.angle = 0.0
        self.z = z


# 只切裙子以下的双腿：大腿（裙摆遮住上端，幅度小）+ 小腿（含鞋，膝上摆）
THIGH_L = Bone("thigh_L", (92, 296, 48, 104), (116, 300))
SHIN_L = Bone("shin_L", (96, 390, 44, 126), (116, 396))
THIGH_R = Bone("thigh_R", (128, 296, 48, 104), (152, 300))
SHIN_R = Bone("shin_R", (126, 390, 44, 126), (152, 396))
THIGH_L.children = [SHIN_L]
THIGH_R.children = [SHIN_R]
LEGS = [THIGH_L, THIGH_R]


def base_clean() -> QPixmap:
    """底图擦掉部件所占区域，部件离开后露出的是透明（裙底/背景）。"""
    base = QPixmap(src)
    p = QPainter(base)
    p.setCompositionMode(QPainter.CompositionMode_Clear)
    for b in LEGS:
        p.fillRect(b.rect, Qt.transparent)
        for c in b.children:
            p.fillRect(c.rect, Qt.transparent)
        p.fillRect(c.rect, Qt.transparent)
    p.end()
    return base


def draw_bone(p, b, angles):
    p.save()
    p.translate(b.px, b.py)
    p.rotate(angles.get(b.name, 0.0))
    p.translate(-b.px, -b.py)
    p.drawPixmap(b.rect.topLeft(), b.slice)
    for c in b.children:
        draw_bone(p, c, angles)
    p.restore()


def render(angles) -> QImage:
    canvas = QPixmap(W, H)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawPixmap(0, 0, base_clean())
    for b in LEGS:
        draw_bone(p, b, angles)
    p.end()
    return canvas.toImage()


CASES = [
    ("立正", {}),
    ("小腿 +14", {"shin_L": 14, "shin_R": 14}),
    ("小腿 -14", {"shin_L": -14, "shin_R": -14}),
    ("交替迈步", {"thigh_L": -8, "shin_L": 16, "thigh_R": 6, "shin_R": -6}),
    ("单腿屈膝", {"thigh_L": -12, "shin_L": 26}),
]

SC = 1.6
BW, BH = int(W * SC) + 8, int(H * SC) + 26
img = QImage(BW * len(CASES), BH, QImage.Format_ARGB32)
img.fill(QColor(250, 249, 246))
p = QPainter(img)
p.setRenderHint(QPainter.SmoothPixmapTransform)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f):
        QFontDatabase.addApplicationFont(f)
        break
fnt = QFont()
fnt.setPointSize(11)
p.setFont(fnt)
p.setPen(QColor(70, 70, 80))
for i, (label, angles) in enumerate(CASES):
    x0 = i * BW
    frame = render(angles)
    p.drawImage(QRect(x0 + 4, 22, int(W * SC), int(H * SC)), frame)
    p.drawText(QRect(x0 + 6, 2, BW - 8, 18), Qt.AlignLeft, label)
    if i:
        p.setPen(QColor(220, 220, 224))
        p.drawLine(x0, 0, x0, BH - 1)
        p.setPen(QColor(70, 70, 80))
p.end()
out = r"F:\WhaleGirlPet\docs\rig_proto_legs.png"
img.save(out)
print("腿部原型图:", out, os.path.getsize(out), "bytes")
