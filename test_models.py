# -*- coding: utf-8 -*-
"""模型库页离屏冒烟：清单渲染、复制链接、切换模型、下载器参数（不实际下载）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

import models_catalog  # noqa: E402
from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.open_panel()
panel = ctl.panel
print("tabs:", [panel.tabs.tabText(i) for i in range(panel.tabs.count())])
print("catalog:", len(models_catalog.CATALOG),
      "| downloadable:", sum(1 for x in models_catalog.CATALOG if models_catalog.can_download(x)))
print("list rows:", panel.lst_models.count())
for i in range(panel.lst_models.count()):
    print("  ", panel.lst_models.item(i).text())
print("cur label:", panel.lbl_cur_model.text())
print("local models:", ctl.local_models())

panel.lst_models.setCurrentRow(0)
panel._copy_link()
print("copy ->", panel.lbl_dl.text()[:80])

panel.lst_models.setCurrentRow(0)
panel._use_model()
print("use  ->", panel.lbl_dl.text(), "| cfg:", ctl.config.get("llm_model_file"))

# 跑不动的模型不给下载
for i in range(panel.lst_models.count()):
    if not models_catalog.can_download(models_catalog.CATALOG[i]):
        panel.lst_models.setCurrentRow(i)
        panel._dl_model()
        print("blocked ->", models_catalog.CATALOG[i]["id"], "|", panel.lbl_dl.text()[:50])
        break

panel.on_model_progress("deepseek-1.5b", 300 * 1048576, 1066 * 1048576)
print("progress ->", panel.lbl_dl.text())

print("llm info:", ctl.local_llm_info())
print("MODELS OK")
ctl.quit_app()
