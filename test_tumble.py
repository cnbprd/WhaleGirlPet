# -*- coding: utf-8 -*-
"""v2.9.3b：验证「摔一跤」不再把立绘转到横躺。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication
from PIL import Image, ImageDraw

import main as m

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "_matting")
FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)
pet = ctl.pet
pet.show()

shots = {}
max_rot = 0.0
max_sy = 0.0
seq = []
pet.do_action("tumble")
t = 0.0
for i in range(400):
    pet._tick()
    t = pet.state_t
    r = abs(pet.rot) % 360
    r = min(r, 360 - r)
    max_rot = max(max_rot, r)
    seq.append((round(t, 2), round(pet.rot, 1), round(pet.sy, 2)))
    for mark in (0.30, 0.60, 1.05):
        if mark not in shots and t >= mark:
            shots[mark] = pet.grab().toImage()
    if pet.state != "tumble" and t > 1.0:
        break

print("== 采样 ==")
for s in seq[::6]:
    print("   t=%.2f rot=%5.1f sy=%.2f" % s)

check("旋转不超过 25°", max_rot <= 25.0, f"max_rot={max_rot:.1f}")
check("仍有落地压扁（sy<0.85）", any(v[2] < 0.85 for v in seq),
      f"min_sy={min(v[2] for v in seq):.2f}")
check("状态能回到 idle/follow", pet.state in ("idle", "follow"), pet.state)

# 把三个关键帧横向拼起来目检
paths = []
for mark in (0.30, 0.60, 1.05):
    img = shots.get(mark)
    if img is None:
        continue
    p = os.path.join(OUT, f"tumble-{int(mark*100)}.png")
    img.save(p)
    paths.append((mark, p))

if paths:
    ims = [(mk, Image.open(p).convert("RGBA")) for mk, p in paths]
    h = max(i.height for _, i in ims)
    w = sum(i.width for _, i in ims) + 12 * (len(ims) - 1)
    bg = Image.new("RGB", (w, h + 22), (235, 235, 235))
    x = 0
    d = ImageDraw.Draw(bg)
    for mk, im in ims:
        bg.paste(im, (x, 22), im)
        d.text((x + 4, 5), f"t={mk}", fill=(20, 20, 20))
        x += im.width + 12
    bg.save(os.path.join(OUT, "tumble-strip.png"))
    print("strip:", (w, h + 22))

print()
print("结果:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
ctl.quit_app()
sys.exit(0 if not FAIL else 1)
