# -*- coding: utf-8 -*-
"""v2.5 空闲算力：确认空闲时走 Ollama GPU，并实测一句回答耗时。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
OUT = os.path.join(ROOT, "assets", "_matting")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402

import gpu_guard  # noqa: E402

ctl = Controller(app)
print("game:", gpu_guard.game_running(force=True), gpu_guard.game_name())
print("backend:", ctl.llm.backend, "| gpu_when_idle:", ctl.config.get("gpu_when_idle"))

t0 = time.time()
ok = ctl.llm.start()
print("start:", ok, f"{time.time() - t0:.2f}s", ctl.llm.last_error)
t0 = time.time()
reply = ctl.llm.chat([{"role": "user", "content": "用一句话介绍你自己"}], max_tokens=120)
print("chat:", f"{time.time() - t0:.2f}s", repr((reply or "")[:80]))

ctl.pet.show()
ctl.open_panel()
panel = ctl.panel
panel.resize(760, 900)
panel.tabs.setCurrentIndex(7)
for _ in range(30):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v25-tab-models-gpu.png"))
print("saved")
ctl.quit_app()
