# -*- coding: utf-8 -*-
"""真实桌面截启动屏（全屏截图，能看到透明背景实际合成效果）。"""
import os
import sys

sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PIL import ImageGrab
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from splash import LoadingSplash

app = QApplication(sys.argv)
s = LoadingSplash()
s.show()


def shot():
    out = r"F:\WhaleGirlPet\assets\_matting\splash2.png"
    im = ImageGrab.grab()
    im.save(out)
    print("saved", out, im.size)
    os._exit(0)


QTimer.singleShot(1400, shot)
sys.exit(app.exec())
