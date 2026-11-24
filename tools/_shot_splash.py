# -*- coding: utf-8 -*-
"""临时工具：真实桌面截一张启动屏，用于目检（用完可删）。"""
import os
import sys

sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from splash import LoadingSplash

app = QApplication(sys.argv)
s = LoadingSplash()
s.set_step("正在读取配置与记忆…")
s.show()


def shot():
    out = r"F:\WhaleGirlPet\assets\_matting\splash.png"
    s.grab().save(out)
    print("saved", out, os.path.getsize(out))
    os._exit(0)


QTimer.singleShot(1600, shot)
sys.exit(app.exec())
