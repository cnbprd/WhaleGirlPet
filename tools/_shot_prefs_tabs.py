# -*- coding: utf-8 -*-
"""v2.9.8 设置页 5 个子标签逐一截图（真实控件渲染）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod
from panel import ControlPanel

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")
NAMES = ["关于与更新", "储存位置", "语音唤醒", "天气资讯", "桌宠行为"]

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main_mod.Controller(app, defer_show=True)
panel = ControlPanel(ctl)
panel.show()


def grab(i=0):
    if i >= len(NAMES):
        app.quit()
        return
    panel.side.setCurrentRow(4)          # 设置页
    panel.prefs_tabs.setCurrentIndex(i)
    app.processEvents()
    QTimer.singleShot(300, lambda: _save(i))


def _save(i):
    panel.grab().save(os.path.join(OUT, f"v298-prefs-{i}-{NAMES[i]}.png"))
    QTimer.singleShot(200, lambda: grab(i + 1))


QTimer.singleShot(1200, grab)
sys.exit(app.exec())
