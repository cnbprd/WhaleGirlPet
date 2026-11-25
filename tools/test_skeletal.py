# -*- coding: utf-8 -*-
"""skeletal 引擎冒烟：4 个动作出帧 + 骨骼角度采样 + 单帧耗时。"""
import os
import sys
import time
sys.path.insert(0, r"F:\WhaleGirlPet\app")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import skeletal as sk  # noqa: E402

pix = QPixmap(r"F:\WhaleGirlPet\assets\skins\default.png")
sprite = sk.SkeletalSprite(pix)
print("立绘:", sprite.W, "x", sprite.H, "| 骨骼", len(sprite.skeleton.defs), "| 网格",
      sprite.skin.gx, "x", sprite.skin.gy, "| 动作", len(sk.CLIPS))

for name in ("walk", "run", "hop", "tumble", "breath"):
    clip = sk.CLIPS[name]
    rows = []
    for t in (0.0, clip.duration * 0.25, clip.duration * 0.5, clip.duration * 0.75):
        rows.append((round(t, 2), clip.pose(t)))
    print(f"\n[{name}] 时长 {clip.duration}s 循环={clip.loop}")
    for t, pose in rows:
        print("  t=%.2f" % t, {k: round(v, 1) for k, v in pose.items()})

CASES = [("walk", 0.0, 0.20, 0.39, 0.58), ("run", 0.0, 0.13, 0.26, 0.39),
         ("hop", 0.0, 0.33, 0.70, 1.47), ("tumble", 0.0, 0.88, 1.36, 1.76)]
COLS = 4
SC = 1.35
CW, CH = int(sprite.W * SC) + 8, int(sprite.H * SC) + 26
img = QImage(CW * COLS + 120, CH * len(CASES), QImage.Format_ARGB32)
img.fill(QColor(250, 249, 246))
p = QPainter(img)
p.setRenderHint(QPainter.SmoothPixmapTransform)
for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(f):
        QFontDatabase.addApplicationFont(f)
        break
fnt = QFont()
fnt.setPointSize(12)
p.setFont(fnt)
p.setPen(QColor(70, 70, 80))
for r, (name, *ts) in enumerate(CASES):
    y0 = r * CH
    dur = sk.CLIPS[name].duration
    p.drawText(QRect(6, y0 + CH // 2 - 10, 112, 20), Qt.AlignLeft, f"{name}")
    p.drawText(QRect(6, y0 + CH // 2 + 8, 112, 20), Qt.AlignLeft, f"{dur:.2f}s")
    for c, t in enumerate(ts):
        frame = sprite.frame_at(name, min(t, dur))
        x = 118 + c * CW
        p.drawPixmap(QRect(x, y0 + 24, int(sprite.W * SC), int(sprite.H * SC)), frame)
    p.setPen(QColor(216, 216, 220))
    p.drawLine(0, y0 + CH - 1, img.width(), y0 + CH - 1)
    p.setPen(QColor(70, 70, 80))
p.end()
out = r"F:\WhaleGirlPet\docs\skeletal_v313.png"
img.save(out)
print("\n帧图:", out, os.path.getsize(out), "bytes")

# 性能：模拟整帧，角度每帧都变（缓存不命中）
t0 = time.perf_counter()
N = 40
for i in range(N):
    sprite.render({"thigh_l": i % 20, "shin_l": 30 - i % 20, "spine": 1.5})
dt = (time.perf_counter() - t0) / N
print(f"render 平均 {dt*1000:.1f} ms → {1/dt:.0f} fps 上限")
