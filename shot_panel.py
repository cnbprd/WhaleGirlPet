# -*- coding: utf-8 -*-
"""渲染控制面板两个关键页（语音人格 / 安全体检）并存图，用于交付目检。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

OUT = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT, exist_ok=True)

ctl = Controller(app)
ctl.pet.show()
ctl.open_panel()
panel = ctl.panel
panel.tabs.setCurrentIndex(5)  # 音频库
panel.resize(980, 900)
panel.show()
for _ in range(30):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v24-tab-audio.png"))
print("audio tab saved")

panel.tabs.setCurrentIndex(6)  # 语音人格
for _ in range(20):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v24-tab-voice.png"))
print("voice tab saved")

ctl.refresh_panel()
panel.tabs.setCurrentIndex(9)  # 安全体检
for _ in range(30):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v24-tab-security.png"))
print("security tab saved")

panel.tabs.setCurrentIndex(1)  # 打工
app.processEvents()
time.sleep(0.2)
panel.grab().save(os.path.join(OUT, "v24-tab-tasks.png"))
print("tasks tab saved")

ctl.quit_app()
for _ in range(6):
    app.processEvents()
    time.sleep(0.05)
print("DONE")
