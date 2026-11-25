# -*- coding: utf-8 -*-
"""走路两种画法对比：网格骨骼（新） vs 条带 warp（旧），逐帧从真窗口抓。"""
import os
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import pet_window as pw  # noqa: E402
import rig as rig_mod  # noqa: E402


class Ctl:
    def __init__(self, extra=None):
        self.config = {"skin": "default", "anim_timeline": True, "scale": 1.0,
                       "rig_mesh": True, "skeletal": True}
        self.config.update(extra or {})
        self.audio = None

    def on_action(self, key):
        pass

    def on_walk(self):
        pass

    def on_run(self):
        pass

    def on_panic(self):
        pass


COLS = 8
SHOT = {}

for label, extra in (("骨骼引擎（新）", {}),
                     ("网格腿 rig（v3.0.12）", {"skeletal": False}),
                     ("条带 warp（旧）", {"skeletal": False, "rig_mesh": False})):
    pet = pw.PetWindow(Ctl(extra), show_now=False)
    pet.set_state("walk")
    frames = []
    for i in range(COLS * 5):
        pet._tick()
        if i % 5 == 0:
            frames.append(pet.grab().toImage())
    SHOT[label] = frames
    print(f"[{label}] 抓帧 {len(frames)}，gait 相位 {pet.gait:.2f}，窗口 {pet.width()}x{pet.height()}")
    pet.hide()

rows = list(SHOT)
CW = max(f.width() for fs in SHOT.values() for f in fs)
CH = max(f.height() for fs in SHOT.values() for f in fs)
LAB = 190
img = QImage(CW * COLS + LAB, CH * len(rows), QImage.Format_ARGB32)
img.fill(QColor(252, 251, 249))
p = QPainter(img)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f):
        QFontDatabase.addApplicationFont(f)
        break
fnt = QFont()
fnt.setPointSize(13)
p.setFont(fnt)
p.setPen(QColor(70, 70, 80))
for r, label in enumerate(rows):
    y0 = r * CH
    p.drawText(QRect(6, y0 + CH // 2 - 12, LAB - 10, 26), Qt.AlignLeft, label)
    for c, f in enumerate(SHOT[label]):
        p.drawImage(QRect(LAB + c * CW, y0, f.width(), f.height()), f)
    p.setPen(QColor(215, 215, 220))
    p.drawLine(0, y0 + CH - 1, img.width(), y0 + CH - 1)
p.end()
out = r"F:\WhaleGirlPet\docs\rig_walk_compare.png"
img.save(out)
print("对比图:", out, os.path.getsize(out), "bytes")

