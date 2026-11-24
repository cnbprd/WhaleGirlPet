# -*- coding: utf-8 -*-
"""v2.9.6 目检：真实桌面启动后逐页抓控制面板（含新增的「设置」页）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")
os.makedirs(OUT, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    controller = main_mod.Controller(app)
    controller.open_panel()
    panel = controller.panel

    def shot_all():
        n = panel.tabs.count()
        for i in range(n):
            panel.tabs.setCurrentIndex(i)
            app.processEvents()
            label = panel.side.item(i).text().replace("/", "_")
            panel.grab().save(os.path.join(OUT, f"v296-panel-{i:02d}-{label}.png"))
        app.quit()

    QTimer.singleShot(900, shot_all)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
