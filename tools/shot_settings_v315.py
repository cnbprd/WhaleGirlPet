# -*- coding: utf-8 -*-
"""设置页离屏截图：确认「联网后端管理」已换成「模型 API 接入」卡片。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import panel as panel_mod  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"active_profile": 0, "llm_on": True, "llm_idle_unload_min": 20,
                       "name": "大肥鱼"}
        self._ps = [{"name": "智谱默认", "endpoint": "", "model": "glm-4-flash",
                     "api_key": "sk-xxx", "api_format": "openai", "models": [], "connected": False}]
        self.saved = 0

    def profiles(self):
        return self._ps

    def save_config(self):
        self.saved += 1

    def new_profile(self):
        pass

    def local_models(self):
        return []

    def set_auto(self, on):
        self.config["auto"] = on

    def test_ai_connection(self):
        pass

    def get_name(self):
        return "大肥鱼"


p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)
p.ctl = StubCtl()
page = p._tab_settings()
page.resize(760, 1200)
img = page.grab()
out = os.path.join(ROOT, "docs", "settings_v315.png")
img.save(out)

has_card = hasattr(p, "api_card")
has_old = hasattr(p, "cb_profiles")
print("新卡片存在:", has_card, "| 旧下拉残留:", has_old)
print("卡片状态:", p.api_card.lbl_state.text())
print("设置页高度:", page.height(), "| 截图:", os.path.getsize(out), "bytes")
