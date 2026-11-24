# -*- coding: utf-8 -*-
"""离屏渲染：抓取桌宠与面板截图，保存到项目目录供目检。"""
import os
import sys
import faulthandler
faulthandler.enable()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

import main

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main.Controller(app)
app.processEvents()

out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ctl.pet.grab().save(os.path.join(out_dir, "render-pet.png"))
ctl.open_panel()
app.processEvents()
ctl.panel.grab().save(os.path.join(out_dir, "render-panel.png"))

# 切一套皮肤再抓
ctl.set_skin("blackred")
app.processEvents()
ctl.pet.grab().save(os.path.join(out_dir, "render-pet-blackred.png"))

print("saved")
QTimer.singleShot(300, ctl.quit_app)
sys.exit(app.exec())
