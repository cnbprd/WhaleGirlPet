# -*- coding: utf-8 -*-
"""Controller 侧 ASR 接线：默认关闭、成功文本走 chat、失败不造假。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from PySide6.QtWidgets import QApplication
import main

app = QApplication([])
ctl = main.Controller(app)
try:
    assert ctl.asr.enabled is False, "ASR must be off at startup"
    assert ctl.asr.listen()["reason"] == "disabled", "off ASR must not start a worker"

    ctl.open_panel()
    sent = []
    ctl.send_chat = lambda text, **kw: sent.append(text)
    ctl._dispatch_voice = lambda text: False

    ctl._on_voice({"ok": True, "text": "打开面板", "conf": 0.4, "reason": ""})
    assert sent == ["打开面板"], sent

    sent.clear()
    ctl._on_voice({"ok": False, "text": "", "conf": 0.0, "reason": "no_speech"})
    assert sent == [], "failure produced fake chat text"

    class FakeAsr:
        def __init__(self):
            self.armed = 0
            self.worker = None

        def is_listening(self):
            return False

        def arm_once(self):
            self.armed += 1

        def listen(self, wait_s=4, timeout_s=14):
            return {"started": True, "ok": True, "text": "", "conf": 0.0, "reason": ""}

    fake = FakeAsr()
    ctl.asr = fake
    ctl.voice_listen()
    assert fake.armed == 1, "manual voice trigger did not arm one shot"
    print("asr_ui_ok startup_off=True route_text='打开面板' failure_no_text=True")
finally:
    ctl.quit_app()
