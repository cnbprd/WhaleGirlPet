# -*- coding: utf-8 -*-
"""v2.9.0 联机自检：真实拉起 Controller，强制走一轮环境播报，检查缓存与台词。

不依赖人工盯气泡（气泡 5 秒就消失）。
    .venv/Scripts/python.exe test_v29_live.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import awareness
import main as m

app = QApplication([])
ctl = m.Controller(app)
state = {"t0": 0, "done": False}


def finish():
    if state["done"]:
        return
    state["done"] = True
    try:
        print("worker:", ctl.ambient_worker)
        print("cache keys:", list((ctl._ambient_cache or {}).keys()))
        print("weather:", (ctl._ambient_cache or {}).get("weather"))
        print("news[0]:", ((ctl._ambient_cache or {}).get("news") or [""])[0][:50])
        print("greeted flag:", getattr(ctl, "_ambient_greeted", None))
        print("pet visible:", ctl.pet.isVisible(), "size:", ctl.pet.width(), ctl.pet.height())
        print("own fullscreen(False 期望):", awareness.foreground_fullscreen(int(ctl.pet.winId())))
        print("battery:", awareness.power_status())
    finally:
        ctl.quit_app()


def poll():
    state["t0"] += 1
    # 等后台线程结束，再给 200ms 让 done 信号落地
    if ctl.ambient_worker is None and ctl._ambient_cache:
        QTimer.singleShot(200, finish)
        return
    if state["t0"] > 40:
        print("超时：20 秒内没拿到环境数据")
        finish()
        return
    QTimer.singleShot(500, poll)


print("bubble probe:", ctl.pet.bubble.isVisible() if hasattr(ctl.pet, "bubble") else "n/a")
ctl._on_ambient_tick(force=True)
QTimer.singleShot(500, poll)
sys.exit(app.exec())
