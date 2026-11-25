"""v3.0.23 第 11 条：把走路 4 个相位分别用 skeletal / rig 引擎出帧，拼成对照图。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtCore import QRect, Qt

import skeletal as sk_mod
import rig as rig_mod

app = QGuiApplication(sys.argv)

SKIN = os.path.join(ROOT, "assets", "skins", "blackred.png")
pix = QPixmap(SKIN)
W, H = pix.width(), pix.height()

sprite = sk_mod.SkeletalSprite(pix, "high")
rig = rig_mod.Rig(pix)

phases = [0.0, 0.25, 0.5, 0.75]
frames = []
for ph in phases:
    pose = sk_mod.CLIPS["walk"].pose(ph * 0.78)
    lift = H * 0.011
    off = {"thigh_l": (0.0, -lift * max(0.0, __import__("math").sin(ph * 2 * 3.1415926))),
           "thigh_r": (0.0, -lift * max(0.0, -__import__("math").sin(ph * 2 * 3.1415926)))}
    frames.append(("skel %.2f" % ph, sprite.render(pose, off)))
for ph in phases:
    ang = rig_mod.Rig.walk_angles(ph * 2 * 3.1415926, amp_thigh=9.0, amp_shin=20.0)
    frames.append(("rig %.2f" % ph, rig.frame(*ang)))

from PIL import Image, ImageDraw

cell_w, cell_h = W, H + 18
canvas = Image.new("RGB", (cell_w * 4, cell_h * 2 + 4), (24, 32, 48))
draw = ImageDraw.Draw(canvas)
for idx, (label, pm) in enumerate(frames):
    row, col = divmod(idx, 4)
    img = pm.toImage().convertToFormat(pm.toImage().Format.Format_RGBA8888)
    ptr = img.bits()
    from PIL import Image as I
    qimg = I.frombytes("RGBA", (W, H), bytes(ptr))
    canvas.paste(qimg, (col * cell_w, row * cell_h + 18), qimg)
    draw.text((col * cell_w + 4, row * cell_h + 2), label, fill=(230, 240, 255))

out = os.path.join(ROOT, "docs", "walk_frames_v323.png")
canvas.save(out)
print("saved", out, canvas.size)
