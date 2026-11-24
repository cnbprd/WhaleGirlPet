# -*- coding: utf-8 -*-
"""v2.0.0 渲染快照：把新增面板页与三套新皮肤各抓一张 PNG，用于目检。"""
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
p.show()

# 逐页截图
names = {5: "voice", 6: "memory", 7: "security", 8: "account", 9: "schedule"}
for idx, tag in names.items():
    p.tabs.setCurrentIndex(idx)
    app.processEvents()
    path = os.path.join(out_dir, f"v4-tab-{tag}.png")
    p.tabs.currentWidget().grab().save(path)
    print("tab:", tag, path)

# 安全体检真实跑一次（同步，便于截图）
import secscan  # noqa: E402

rep = secscan.build_report()
p.refresh_scan(rep)
p.tabs.setCurrentIndex(7)
app.processEvents()
p.tabs.currentWidget().grab().save(os.path.join(out_dir, "v4-tab-security.png"))
print("security score:", rep.get("score"), "issues:", len(rep.get("issues", [])))


# 皮肤快照
def shot_skin(form: str, skin: str, tag: str):
    ctl.pet.set_form(form)
    if skin:
        ctl.pet.set_skin(skin)
    ctl.pet.show()
    ctl.pet.set_expression("happy", 0)
    app.processEvents()
    path = os.path.join(out_dir, f"v4-pet-{tag}.png")
    ctl.pet.grab().save(path)
    print("pet:", tag, path, ctl.pet.width(), "x", ctl.pet.height(),
          "| skin:", ctl.config.get("skin"))


shot_skin("mature", None, "mature")
shot_skin("mature", "jk", "jk")
shot_skin("mature", "hanfu", "hanfu")
shot_skin("loli", "loli", "loli")
print("DONE")
