# -*- coding: utf-8 -*-
"""v2.9.6 实测：点托盘「搜索剪贴板内容」先弹授权框，拒绝后不去读剪贴板。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

import main as main_mod

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")


def snap(name):
    QGuiApplication.primaryScreen().grabWindow(0).save(os.path.join(OUT, name))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app, defer_show=True)
    ctl.pet.show()
    ctl.pet.bubble.show_text("测试：先复制点东西，再让我搜剪贴板", 3000)

    hit = {"read": 0}
    orig = ctl.search_in_browser

    def spy():
        hit["read"] += 1
        orig()

    ctl.search_in_browser = spy

    QTimer.singleShot(700, ctl.ask_search_clipboard)
    QTimer.singleShot(900, lambda: print("modal:", QApplication.activeModalWidget()))
    QTimer.singleShot(1100, lambda: snap("v296-clip-ask.png"))
    QTimer.singleShot(1900, lambda: QApplication.activeModalWidget() and
                      QApplication.activeModalWidget().reject())
    QTimer.singleShot(2400, lambda: print("拒绝后是否读了剪贴板（0=没读）：", hit["read"]))
    QTimer.singleShot(2600, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
