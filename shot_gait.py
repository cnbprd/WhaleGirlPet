# -*- coding: utf-8 -*-
"""步态目检：抓 4 个相位静帧拼一张，看腿有没有真的动、接缝难看吗。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

root = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(root, "assets", "_matting")
ctl = Controller(app)
pet = ctl.pet
pet.show()
app.processEvents()

frames = []
for amp in (0.0, 6.0):
    for g in (0.0, 0.25, 0.5, 0.75):
        pet.gait_on = bool(amp)
        pet.gait_amp = amp
        pet.gait = g
        pet.update()
        app.processEvents()
        frames.append(pet.grab())

w = max(f.width() for f in frames)
h = max(f.height() for f in frames)
sheet = QPixmap(w * 4, h * 2)
sheet.fill(0)
p = QPainter(sheet)
for i, f in enumerate(frames):
    p.drawPixmap(QRect((i % 4) * w, (i // 4) * h, f.width(), f.height()), f)
p.end()
path = os.path.join(out_dir, "gait-4frames.png")
sheet.save(path)
print("saved:", path, sheet.width(), "x", sheet.height())
print("hip_y:", pet._hip_y, "ank_y:", pet._ank_y, "pix h:", pet._pix.height())
print("upper:", pet._upper.size(), "leg:", pet._leg.size(), "foot:", pet._foot.size())
