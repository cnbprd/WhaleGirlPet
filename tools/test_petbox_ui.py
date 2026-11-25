# -*- coding: utf-8 -*-
"""v3.0.12 面板冒烟：桌宠行为页新增的两个动画开关能建、能读配置。"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import QApplication  # noqa: E402

import panel as panel_mod  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"skin": "default", "scale": 1.0, "form": "mature",
                       "anim_timeline": False, "rig_mesh": True}
        self.saved = 0

    def save_config(self):
        self.saved += 1

    def toggle_chatter(self, v):
        pass

    def set_skin(self, k):
        self.config["skin"] = k

    def set_scale(self, v):
        pass


app = QApplication([])
p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)
p.ctl = StubCtl()
for attr in ("ed_name", "skin_combo", "size_combo", "form_combo"):
    setattr(p, attr, None)
box = p._build_pet_box()
box.resize(760, 420)

checks = [w for w in box.findChildren(panel_mod.QCheckBox)]
print("开关数量:", len(checks))
for c in checks:
    print(" -", c.text(), "| checked =", c.isChecked())
print("anim_timeline 配置 =", p.ctl.config.get("anim_timeline"),
      "| rig_mesh 配置 =", p.ctl.config.get("rig_mesh"))

# 切一下开关，确认信号链路写回配置（初始都是未选中，先点开再点关）
for chk, key in ((p.chk_rig, "rig_mesh"), (p.chk_timeline, "anim_timeline")):
    chk.setChecked(True)
    on = p.ctl.config[key]
    chk.setChecked(False)
    off = p.ctl.config[key]
    print(f"{chk.text()}: 默认 {off} ← 关 / 开 → {on} | save_config {p.ctl.saved} 次")

# refresh() 里的回填元组是否包含这些开关（面板每次打开都会刷新）
import inspect
src = inspect.getsource(panel_mod.ControlPanel.refresh)
print("refresh 回填含 anim_timeline:", '"anim_timeline"' in src,
      "| 含 rig_mesh:", '"rig_mesh"' in src,
      "| 含 skeletal:", '"skeletal"' in src)

img = box.grab()
out = r"F:\WhaleGirlPet\docs\panel_petbox_v312.png"
img.save(out)
print("面板截图:", out, os.path.getsize(out), "bytes")

