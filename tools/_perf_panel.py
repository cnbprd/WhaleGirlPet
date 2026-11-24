# -*- coding: utf-8 -*-
"""量测：面板打开总耗时 + 每个页面首次构建耗时 + refresh 耗时。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtWidgets import QApplication

import main as main_mod

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

t0 = time.perf_counter()
ctl = main_mod.Controller(app)
print("Controller 初始化 %.2fs" % (time.perf_counter() - t0))

t1 = time.perf_counter()
ctl.open_panel()
panel = ctl.panel
print("open_panel 总耗时 %.2fs" % (time.perf_counter() - t1))

print("页面数", panel.tabs.count())

# 逐页切换，量 refresh 与切页耗时
for i in range(panel.tabs.count()):
    name = panel.side.item(i).text()
    t = time.perf_counter()
    panel.tabs.setCurrentIndex(i)
    app.processEvents()
    print("  切到 %-8s %.3fs" % (name, time.perf_counter() - t))

t2 = time.perf_counter()
panel.refresh()
app.processEvents()
print("refresh() %.2fs" % (time.perf_counter() - t2))

app.quit()
