# -*- coding: utf-8 -*-
"""v2.7 目检：音频库页显示人格专属音效。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
OUT = os.path.join(ROOT, "assets", "_matting")
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.config["persona"] = "korean_green"
ctl.pet.show()
ctl.open_panel()
panel = ctl.panel
panel.resize(780, 880)
panel.refresh()
panel.tabs.setCurrentIndex(5)
for _ in range(30):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v27-tab-audio-persona.png"))
print("label:", panel.lbl_audio_lib.text().replace("\n", " | "))
print("rows:", panel.tbl_audio.rowCount())
ctl.quit_app()
