# -*- coding: utf-8 -*-
"""v2.1.0 渲染快照：模型库页 + 富江脸皮肤（真实平台，不设 offscreen，避免中文字体缺失）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "_matting")
ctl = Controller(app)
ctl.open_panel()
p = ctl.panel
p.resize(560, 720)
p.show()
app.processEvents()

idx = [i for i in range(p.tabs.count()) if p.tabs.tabText(i) == "模型库"][0]
p.tabs.setCurrentIndex(idx)
app.processEvents()
p.tabs.currentWidget().grab().save(os.path.join(out_dir, "v21-tab-models.png"))
print("models tab:", idx, "rows:", p.lst_models.count())

p.lst_models.setCurrentRow(0)
app.processEvents()
p.tabs.currentWidget().grab().save(os.path.join(out_dir, "v21-tab-models-sel.png"))


def shot(form, skin, tag):
    ctl.pet.set_form(form)
    if skin:
        ctl.pet.set_skin(skin)
    ctl.pet.show()
    ctl.pet.set_expression("default", 0)
    app.processEvents()
    ctl.pet.grab().save(os.path.join(out_dir, f"v21-pet-{tag}.png"))
    print("pet:", tag, ctl.pet.width(), "x", ctl.pet.height())


shot("mature", None, "default")
shot("mature", "jk", "jk")
shot("mature", "blackgreen", "blackgreen")
shot("loli", "loli", "loli")
print("DONE")
