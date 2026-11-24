# -*- coding: utf-8 -*-
"""开发用：打开面板的「关于与更新」页并抓图，检查排版。

    .venv\\Scripts\\python.exe tools\\_shot_about.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as main_mod  # noqa: E402

OUT = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT, exist_ok=True)


def run():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    ctl.open_panel()
    panel = ctl.panel
    panel.tabs.setCurrentIndex(4)

    def go():
        app.processEvents()
        path = os.path.join(OUT, "v299-about.png")
        panel.grab().save(path)
        print("saved", path, panel.size().width(), "x", panel.size().height())
        app.quit()

    QTimer.singleShot(1200, go)
    app.exec()


if __name__ == "__main__":
    run()
