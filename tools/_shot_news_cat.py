# -*- coding: utf-8 -*-
"""v2.9.8 实测：点「体育」分类按钮，看资讯文本框是否真的出标题。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod
from panel import ControlPanel

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main_mod.Controller(app, defer_show=True)
panel = ControlPanel(ctl)
panel.show()


def go():
    panel.side.setCurrentRow(4)
    panel.prefs_tabs.setCurrentIndex(3)
    panel.news_cat_btns["sports"].click()


def grab():
    panel.grab().save(os.path.join(OUT, "v298-news-sports.png"))
    print("TEXT:", panel.txt_news.toPlainText()[:160].replace("\n", " / "))
    app.quit()


QTimer.singleShot(1200, go)
QTimer.singleShot(4200, grab)
sys.exit(app.exec())
