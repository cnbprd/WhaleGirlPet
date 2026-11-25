# -*- coding: utf-8 -*-
"""v3.0.11 真窗口取帧：让 PetWindow 自己画（走真实 paintEvent），抓 4 个动作 × 6 帧。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import pet_window as pw  # noqa: E402


class Ctl:
    def __init__(self):
        self.config = {"skin": "default", "anim_timeline": True, "scale": 1.0}

    def on_action(self, key):
        pass

    def on_panic(self):
        pass

    def on_walk(self):
        pass

    def on_run(self):
        pass


pet = pw.PetWindow(Ctl(), show_now=False)
print("窗口尺寸:", pet.width(), "x", pet.height())

NEED = ("hop", "tumble", "look", "crab")
COLS = 6
scraps = {}
for key in NEED:
    pet.do_action(key)
    dur = pw.CLIPS_DUR.get(key, 2.0) if hasattr(pw, "CLIPS_DUR") else 2.0
    dur = min(dur, 2.2)
    frames = []
    # 先进入动作，再按等间隔推进到该动作的 6 个采样点
    total = int(dur / (pw.FRAME_MS / 1000.0))
    marks = set(int(total * (c + 0.5) / COLS) for c in range(COLS))
    for i in range(total + 1):
        pet._tick()
        if i in marks:
            frames.append(pet.grab().toImage())
    scraps[key] = frames
    print(f"[{key}] 抓帧 {len(frames)} 张，state={pet.state}")
    pet.tl.stop()

CW = max(f.width() for fs in scraps.values() for f in fs)
CH = max(f.height() for fs in scraps.values() for f in fs)
LAB_W = 168
img = QImage(CW * COLS + LAB_W, CH * len(NEED) + 20, QImage.Format_ARGB32)
img.fill(QColor(250, 249, 246))
p = QPainter(img)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f) and QFontDatabase.addApplicationFont(f) >= 0:
        break
lf = QFont()
lf.setPointSize(20)
p.setFont(lf)
p.setPen(QColor(90, 90, 100))
LAB = {"hop": "hop 蹦跳", "tumble": "tumble 摔跤", "look": "look 左右看", "crab": "crab 螃蟹步"}
for r, key in enumerate(NEED):
    y0 = 20 + r * CH
    p.drawText(QRect(6, y0 + CH // 2 - 16, LAB_W - 12, 34), Qt.AlignLeft, LAB[key])
    for c, frame in enumerate(scraps[key]):
        p.drawImage(QRect(LAB_W + c * CW, y0, frame.width(), frame.height()), frame)
    p.setPen(QColor(210, 210, 215))
    p.drawLine(0, y0 + CH - 1, img.width(), y0 + CH - 1)
p.end()

out = r"F:\WhaleGirlPet\docs\anim_v311_window.png"
img.save(out)
print("真窗口帧图:", out, os.path.getsize(out), "bytes")
pet.bubble.close()


