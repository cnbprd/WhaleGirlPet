# -*- coding: utf-8 -*-
"""v3.0.11 时间轴引擎实测：数值采样 + 事件点 + 8 动作帧图（可肉眼验收）。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")

import anim_engine as anim  # noqa: E402
import paths  # noqa: E402

print("动作数:", len(anim.CLIPS))
for n in anim.names():
    print("  ", anim.describe(n))

# 1) 采样：逐帧推进，验证缓动曲线与末帧
for name in anim.names():
    tl = anim.Timeline()
    tl.play(name)
    clip = anim.CLIPS[name]
    rows = []
    for i in range(0, int(clip.duration * 60) + 1):
        p = tl.step(1.0 / 60.0)
        if i % 12 == 0 and p:
            rows.append((round(tl.t, 2), round(p.bob, 1), round(p.rot, 1),
                         round(p.sx, 2), round(p.sy, 2)))
    evs = []
    tl2 = anim.Timeline()
    tl2.play(name)
    for _ in range(int(clip.duration * 60) + 3):
        tl2.step(1.0 / 60.0)
        evs += tl2.pop_events()
    print(f"\n[{name}] 采样(时间,bob,rot,sx,sy) 前 5 个:", rows[:5])
    print(f"[{name}] 事件点:", evs or "无", "| 末帧 done=", clip.done(tl2.t))

# 2) 帧图：8 个动作 × 6 帧，用真实立绘套引擎姿态画出来
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap  # noqa: E402
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])   # QPixmap 需要 GUI 应用实例，否则 offscreen 下直接崩

# 离屏平台拿不到系统默认字形，手动装一个中文字体，否则标签全是方块
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402

for _f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
           r"C:\Windows\Fonts\arial.ttf"):
    if os.path.exists(_f) and QFontDatabase.addApplicationFont(_f) >= 0:
        break
ui_font = QFont(QFont().defaultFamily(), 9)

skin = QPixmap(paths.asset_path(paths.SKINS["default"][1]))
CELL_W, CELL_H = 86, 150
rows = len(anim.names())
cols = 6
img = QImage(CELL_W * cols + 132, CELL_H * rows + 24, QImage.Format_ARGB32)
img.fill(QColor(246, 246, 248))
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
p.setPen(QColor(120, 120, 130))
p.setFont(ui_font)
LABELS = {"crab": "crab 螃蟹步", "floatstep": "floatstep 漂浮", "trot": "trot 小跑",
          "look": "look 左右看", "eatrice": "eatrice 吃白饭", "tumble": "tumble 摔跤",
          "brawl": "brawl 打闹", "hop": "hop 蹦跳"}
for r, name in enumerate(anim.names()):
    y0 = 24 + r * CELL_H
    p.drawText(QRect(4, y0 + CELL_H // 2 - 8, 124, 16), Qt.AlignLeft, LABELS.get(name, name))
    tl = anim.Timeline()
    tl.play(name)
    for c in range(cols):
        frac = (c + 0.5) / cols
        t = anim.CLIPS[name].duration * frac
        pose = anim.CLIPS[name].pose(t)
        cx = 132 + c * CELL_W + CELL_W // 2
        base_y = y0 + CELL_H - 8
        pix = skin.scaledToHeight(int(118 * (pose.sy or 1.0)),
                                  Qt.SmoothTransformation)
        pix = pix.scaledToWidth(int(pix.width() * (pose.sx or 1.0)), Qt.SmoothTransformation)
        p.save()
        p.translate(cx, base_y + pose.bob)
        p.rotate(pose.rot)
        p.drawPixmap(QRect(-pix.width() // 2, -pix.height(), pix.width(), pix.height()), pix)
        p.restore()
        p.setPen(QColor(200, 200, 210))
        p.drawLine(132 + c * CELL_W, y0, 132 + c * CELL_W, y0 + CELL_H)
        p.setPen(QColor(120, 120, 130))
    p.drawLine(4, y0 + CELL_H - 1, img.width() - 4, y0 + CELL_H - 1)
p.end()
out = r"F:\WhaleGirlPet\docs\anim_v311_preview.png"
img.save(out)
print("\n帧图已写:", out, os.path.getsize(out), "bytes")

