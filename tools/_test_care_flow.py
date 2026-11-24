# -*- coding: utf-8 -*-
"""v2.9.7 联动自检：语音入口 → 打工气泡 / 商城 / 背包 / 状态栏。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main_mod.Controller(app)
results = []


def step1():
    ok = ctl._dispatch_voice("大肥鱼，去打工吧")
    results.append(("语音『去打工』命中", bool(ok)))
    results.append(("弹出工作选项气泡", ctl.ask_win is not None and ctl.ask_win.isVisible()))
    results.append(("气泡给了 3 个活", len(getattr(ctl.ask_win, "_pairs", [])) == 3))
    if ctl.ask_win:
        ctl.ask_win.close()
    ctl._dispatch_voice("打开零食商城")
    results.append(("语音『零食商城』打开窗口", ctl.shop_win is not None and ctl.shop_win.isVisible()))
    ctl._dispatch_voice("打开背包")
    results.append(("语音『背包』打开窗口", ctl.bag_win is not None and ctl.bag_win.isVisible()))
    ctl.state.thirst = 10
    ctl.state.hunger = 20
    shown = ctl.maybe_status_bar(force=True)
    results.append(("需求到位弹状态栏", bool(shown) and ctl.status_win.isVisible()))
    ctl.state.hunger = 80
    ctl.state.thirst = 90
    ctl.state.mood = 90
    ctl.state.coins = 300
    shown2 = ctl.maybe_status_bar(force=True)
    results.append(("状态都正常时不弹", not shown2))
    ctl._dispatch_voice("喝口水")
    results.append(("语音『喝水』补水", ctl.state.thirst > 60))
    ctl.beg_snack()
    results.append(("讨零食会亮商城/台词", ctl.shop_win.isVisible()))
    for name, ok in results:
        print(("PASS " if ok else "FAIL ") + name)
    print("RESULT:", "ALL PASS" if all(x for _, x in results) else "HAS FAIL")
    app.quit()


QTimer.singleShot(2500, step1)
QTimer.singleShot(1500, lambda: None)
app.exec()
