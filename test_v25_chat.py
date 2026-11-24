# -*- coding: utf-8 -*-
"""v2.5 验收：1) 聊天页气泡/附件/导出 2) TTS 连续多句是否每句都播。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
OUT = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtCore import QThread, Signal  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402

app = QApplication(sys.argv)

# ---------- 1. TTS 队列 ----------
import tts as tts_mod  # noqa: E402


class FakeWorker(QThread):
    done = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, text, voice, rate, pitch, play_id):
        super().__init__()
        self.text, self.voice, self.rate, self.pitch, self.play_id = text, voice, rate, pitch, play_id

    def stop(self):
        pass

    def run(self):
        time.sleep(0.25)
        self.done.emit(self.play_id, f"fake_{self.text}.mp3")


class FakeAudio:
    def __init__(self):
        self.calls = []

    def play_file(self, p):
        self.calls.append(p)
        return True


tts_mod.SynthWorker = FakeWorker
fa = FakeAudio()
svc = tts_mod.TTSService({"tts_on": True, "tts_online": True}, fa)
tts_mod.cached_path = lambda *a, **k: ""
for s in ("第一句测试文本。", "第二句测试文本。", "第三句测试文本。"):
    svc.say(s, {"voice": "v", "rate": 0, "pitch": 0})
t0 = time.time()
while time.time() - t0 < 7.0:
    app.processEvents()
    time.sleep(0.02)
print("TTS play_file calls:", len(fa.calls), fa.calls)

# ---------- 2. 聊天页 ----------
from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.pet.show()
ctl.open_panel()
panel = ctl.panel
panel.tabs.setCurrentIndex(3)
panel.resize(760, 900)

sample_img = os.path.join(ROOT, "assets", "ui", "icon_preview.png")
sample_file = os.path.join(ROOT, "README.md")
panel.append_chat("user", "给你看张图，还有这个文件", attachment=sample_img)
panel.append_chat("pet", "收到啦～图我存本地了，文件我只记了路径，不会乱动你的东西。")
panel.append_chat("user", "把这份 README 一起收着", attachment=sample_file)
panel.append_chat("pet", "好的，已经记下这份文档。要不要我导出今天的聊天记录？")
for _ in range(30):
    app.processEvents()
    time.sleep(0.05)
panel.grab().save(os.path.join(OUT, "v25-chat.png"))
print("chat tab saved")

# 导出（绕过对话框）
QFileDialog.getSaveFileName = staticmethod(
    lambda *a, **k: (os.path.join(OUT, "v25-chat-export.md"), ""))
panel.export_chat()
app.processEvents()
print("export status:", panel.chat_status.text())
print("chat_log rows:", len(panel._chat_log))

ctl.quit_app()
