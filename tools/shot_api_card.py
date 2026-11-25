# -*- coding: utf-8 -*-
"""模型 API 接入卡片：离屏截图 + 交互单测（不联网）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication, QLineEdit  # noqa: E402

app = QApplication([])
import api_access_ui as ui  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"active_profile": 0}
        self._ps = [
            {"name": "EdgeOne Makers", "endpoint": "https://api.edgeone.ai/v1",
             "model": "deepseek-r1", "api_key": "sk-live-xxxx", "api_format": "openai",
             "models": ["deepseek-r1", "qwen3"], "connected": True},
            {"name": "自定义接入", "endpoint": "https://api.anthropic.com",
             "model": "", "api_key": "", "api_format": "anthropic",
             "models": [], "connected": False},
        ]
        self.saves = 0

    def profiles(self):
        return self._ps

    def save_config(self):
        self.saves += 1

    def new_profile(self):
        self._ps.append({"name": f"接入 {len(self._ps)+1}", "endpoint": "", "model": "",
                         "api_key": "", "api_format": "openai", "models": []})
        self.config["active_profile"] = len(self._ps) - 1

    def test_ai_connection(self):
        raise AssertionError("截图时不该真测连接")


ctl = StubCtl()
card = ui.ApiAccessCard(ctl)
card.resize(620, 700)
card.refresh()

# 先截「已接入列表 + 第二档（未连接）」
ctl.config["active_profile"] = 1
card.refresh()
p1 = os.path.join(ROOT, "docs", "api_card_v315_edit.png")
card.grab().save(p1)

# 再切回已连接那档
ctl.config["active_profile"] = 0
card.refresh()
p2 = os.path.join(ROOT, "docs", "api_card_v315_on.png")
card.grab().save(p2)

# ---------------- 交互核对 ----------------
print("当前档状态文字:", card.lbl_state.text())
card._set_fmt("gemini")
print("点 Gemini 后 pills:", {k: b.isChecked() for k, b in card.fmt_btns.items()})
print("当前 fmt:", card._fmt)

card.btn_eye.setChecked(True)
card._toggle_eye()
print("眼睛开启 echoMode:", card.ed_key.echoMode(), "== Normal", card.ed_key.echoMode() == QLineEdit.Normal)
card.btn_eye.setChecked(False)
card._toggle_eye()

card.ed_name.setText("我的中转")
card.ed_endpoint.setText("https://api.moonshot.cn/v1")
card.cb_model.setCurrentText("moonshot-v1-8k")
card._set_fmt("openai")
card._save()
prof = ctl.profiles()[0]
print("保存后:", prof["name"], "|", prof["api_format"], "|", prof["model"],
      "| connected:", prof["connected"], "| saves:", ctl.saves)

card._disconnect(1)
print("断开第 2 档后 key:", repr(ctl.profiles()[1]["api_key"]),
      "| connected:", ctl.profiles()[1]["connected"])

print("截图:", os.path.getsize(p1), os.path.getsize(p2))
