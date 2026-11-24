# -*- coding: utf-8 -*-
"""端到端验证「大肥鱼做小软件」：真调模型 → 抽代码 → 存盘（不自动运行）。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod
import paths

ASK = "写个脚本打印 hello 和当前时间"
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main_mod.Controller(app)
ctl._ask_run_tool = lambda path, code: print("WOULD ASK RUN:", path, flush=True)

before = set(os.listdir(maker_dir)) if (maker_dir := os.path.join(paths.data_dir(), "scripts")) and os.path.isdir(maker_dir) else set()
ctl.make_tool(ASK)

state = {"done": False}


def poll():
    d = os.path.join(paths.data_dir(), "scripts")
    now = set(os.listdir(d)) if os.path.isdir(d) else set()
    new = sorted(now - before)
    if new:
        print("NEW SCRIPT:", new, flush=True)
        for n in new:
            p = os.path.join(d, n)
            print(open(p, encoding="utf-8").read()[:600], flush=True)
        state["done"] = True
        app.quit()


timer = QTimer()
timer.timeout.connect(poll)
timer.start(1500)


def report():
    print("tool_worker finished:", getattr(getattr(ctl, "tool_worker", None), "isFinished", lambda: "n/a")(),
          "| err:", getattr(ctl, "last_tool_error", "-"))
    app.quit()


QTimer.singleShot(70_000, report)
app.exec()
print("RESULT:", "GOT CODE" if state["done"] else "NO OUTPUT (模型没回/超时)")
