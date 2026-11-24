# -*- coding: utf-8 -*-
"""v2.6 边界验收：确认 walk 一路匀速不再减速，且能贴到屏幕边缘。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402

ctl = Controller(app)
pet = ctl.pet
pet.show()
scr = QGuiApplication.primaryScreen().availableGeometry()
print("screen", scr.width(), "x", scr.height())
print("edge_factor(近右边缘, 向右):", pet._edge_factor(scr.right() - pet.width() - 30, 1))
print("edge_over:", pet._edge_over(), "of width", pet.width())

# 放到左边，向右走 6 秒，采样 x
pet.move(scr.left(), scr.top() + 100)
pet.set_state("walk")
pet.walk_dir = 1
xs = []
t0 = time.time()
while time.time() - t0 < 6.0:
    app.processEvents()
    time.sleep(0.1)
    xs.append(pet.x())
print("x start", xs[0], "x end", xs[-1], "x max", max(xs))
print("right edge touch:", max(xs) + pet.width(), "vs screen right", scr.right())

# 每 0.5 秒位移，比较尾部是否被减速
seg = [xs[i + 5] - xs[i] for i in range(0, len(xs) - 5, 5)]
print("per-0.5s deltas:", seg[:3], "...", seg[-3:])
ctl.quit_app()
