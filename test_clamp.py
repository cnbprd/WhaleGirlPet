# -*- coding: utf-8 -*-
"""v2.9.4 校验：桌宠不会被推出主屏（双屏环境下的"凭空消失"）。

    .venv/Scripts/python.exe test_clamp.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

import main as m

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)
ctl.config["tts_on"] = False
ctl.config["fs_hide_on"] = False
ctl.config["power_saver_on"] = False
pet = ctl.pet
pet.show()
app.processEvents()

scr = QGuiApplication.primaryScreen().availableGeometry()
W = pet.width()
print(f"主屏 {scr.width()}x{scr.height()} @({scr.left()},{scr.top()})  宠物窗口 {W}x{pet.height()}")

print("== 1. 推到主屏右侧之外（模拟跑进副屏）==")
pet.move(scr.right() + 200, pet.y())
pet._clamp_to_screen()
pct = 100.0 * (scr.right() - pet.x()) / W
check("窗口仍有大半在主屏", pct >= 60, f"主屏内宽度占比 {pct:.1f}%")

print("== 2. 推到主屏左侧之外 ==")
pet.move(scr.left() - W - 200, pet.y())
pet._clamp_to_screen()
left_ok = pet.x() + W > scr.left() + 20
check("左侧也留得住", left_ok, f"x={pet.x()} right={pet.x()+W} 屏左={scr.left()}")

print("== 3. 上下边界 ==")
pet.move(pet.x(), scr.bottom() + 300)
pet._clamp_to_screen()
check("底部不越界", pet.y() < scr.bottom(), f"y={pet.y()} bottom={scr.bottom()}")

print("== 4. 正常位置不被乱动 ==")
cx, cy = scr.left() + 300, scr.top() + 200
pet.move(cx, cy)
pet._clamp_to_screen()
check("正常位置保持", (pet.x(), pet.y()) == (cx, cy), f"{pet.x()},{pet.y()}")

print("\n结果:", "ALL PASS" if not FAIL else f"FAILED {FAIL}")
pet.hide()
sys.exit(0 if not FAIL else 1)
