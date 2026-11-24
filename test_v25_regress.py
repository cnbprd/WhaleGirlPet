# -*- coding: utf-8 -*-
"""v2.5 回归：新皮肤渲染 + 步态 warp 4 帧 + 各标签页可打开。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
OUT = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.pet.show()
for _ in range(20):
    app.processEvents()
    time.sleep(0.03)

# 1) 新皮肤
ctl.set_skin("mature")
for _ in range(20):
    app.processEvents()
    time.sleep(0.05)
ctl.pet.grab().save(os.path.join(OUT, "v25-skin-mature.png"))
print("skin size:", ctl.pet.width(), "x", ctl.pet.height())

# 2) 步态 warp 4 帧（走）
states = []
for i in range(4):
    ctl.pet.gait_phase = i / 4.0
    ctl.pet.update()
    app.processEvents()
    time.sleep(0.12)
    states.append(ctl.pet.grab().toImage().copy())
frames = [s.scaled(220, 400) for s in states]
canvas_w = sum(f.width() for f in frames)
from PySide6.QtGui import QImage, QPainter, QColor  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

canvas = QImage(canvas_w, 400, QImage.Format_ARGB32)
canvas.fill(QColor("#101722"))
p = QPainter(canvas)
x = 0
for f in frames:
    p.drawImage(x, 0, f)
    x += f.width()
p.end()
canvas.save(os.path.join(OUT, "v25-gait-mature.png"))
print("gait saved")

# 3) 各标签页
ctl.open_panel()
panel = ctl.panel
panel.resize(760, 900)
ok = []
for i in range(panel.tabs.count()):
    panel.tabs.setCurrentIndex(i)
    app.processEvents()
    time.sleep(0.05)
    ok.append(panel.tabs.tabText(i))
print("tabs:", ok)

panel.tabs.setCurrentIndex(7)  # 账号形态（皮肤列表应出现新皮肤）
for _ in range(20):
    app.processEvents()
    time.sleep(0.04)
panel.grab().save(os.path.join(OUT, "v25-tab-account.png"))
print("account tab saved")

ctl.quit_app()
