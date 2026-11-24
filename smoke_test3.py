# -*- coding: utf-8 -*-
"""v2.0.0 离屏冒烟：构造 Controller + 面板，验证新模块接线与各标签页可创建。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

import paths  # noqa: E402
from main import Controller  # noqa: E402

print("version:", paths.APP_VERSION)
ctl = Controller(app)
print("account:", ctl.account_name(), "| form:", ctl.config.get("form"))
print("persona:", ctl.config.get("persona"), "| skins:", len(paths.SKINS))

ctl.open_panel()
panel = ctl.panel
print("tabs:", [panel.tabs.tabText(i) for i in range(panel.tabs.count())])
print("kb:", ctl.kb_stats(), "| memory:", ctl.memory_count(), "| facts:", len(ctl.memory_facts()))
print("llm:", ctl.local_llm_info())
print("schedule:", ctl.schedule_tasks())
print("yesterday:", (ctl.yesterday_report() or "(空)")[:80])

for k in ("tumble", "brawl", "hop", "crab", "eatrice"):
    ctl.pet.do_action(k)
print("actions ok")

ctl.pet.set_form("loli")
print("loli ->", ctl.config.get("skin"), "| form", ctl.config.get("form"))
ctl.pet.set_form("mature")
print("mature ->", ctl.config.get("skin"), "| form", ctl.config.get("form"))

print("scan-report keys:", list(ctl.last_scan().keys()))
print("SMOKE OK")
ctl.quit_app()
