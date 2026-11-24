# -*- coding: utf-8 -*-
"""校验韩语人格：面板下拉选中 + 语音页截图 + 存档旧键迁移。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

import persona as pers  # noqa: E402
from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.open_panel()
p = ctl.panel

# 模拟旧存档：把内存配置改成旧键，看迁移逻辑是否生效
ctl.config["persona"] = "malaysia_green"
if ctl.config.get("persona") in pers.LEGACY_ALIASES:
    ctl.config["persona"] = pers.LEGACY_ALIASES[ctl.config["persona"]]
print("after migrate:", ctl.config["persona"])

ctl.set_persona("korean_green")
p.tabs.setCurrentIndex(5)
app.processEvents()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "_matting", "v4-tab-voice-kr.png")
p.tabs.currentWidget().grab().save(out)
print("voice tab:", out)

# 下拉里是否出现韩语项
names = [p.cmb_persona.itemText(i) for i in range(p.cmb_persona.count())]
print("dropdown:", names)
print("current:", p.cmb_persona.currentText())

ctl.set_persona("sichuan_sweet")
print("DONE")
