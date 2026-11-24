# -*- coding: utf-8 -*-
"""离屏冒烟测试：构造主控与桌宠，跑 1.5 秒事件循环后退出。"""
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

# 触发一轮面板刷新与聊天回退路径
ctl.open_panel()
ctl.refresh_panel()
ctl.send_chat("你好")
QTimer.singleShot(1500, ctl.quit_app)
sys.exit(app.exec())
