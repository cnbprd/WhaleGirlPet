# -*- coding: utf-8 -*-
"""验证语音命令分发：不碰麦克风，直接把识别结果喂给 _on_voice。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.pet.show()
app.processEvents()


def feed(text, wait=0.4):
    print(f"\n>>> 语音：「{text}」")
    ctl._on_voice({"ok": True, "text": text, "conf": 0.5, "reason": ""})
    t0 = time.time()
    while time.time() - t0 < wait:
        app.processEvents()
        time.sleep(0.05)
    print("   panel:", "已打开" if ctl.panel is not None else "未打开",
          "| pet.state:", ctl.pet.state,
          "| task:", (ctl.task_active or {}).get("key", "-"),
          "| sign_worker:", ctl.sign_worker is not None and ctl.sign_worker.isRunning())


feed("打开面板", 0.8)
feed("跳舞", 0.6)
feed("清理垃圾", 0.6)
feed("番茄钟", 0.6)
feed("喝水提醒", 0.4)
feed("跟着我", 0.4)
feed("小号", 0.4)
feed("置顶", 0.4)
feed("停下", 0.6)
feed("更新病毒库", 0.6)
feed("换装", 0.6)
print("\nskin now:", ctl.config.get("skin"),
      "| size:", ctl.config.get("size_label"),
      "| topmost:", ctl.config.get("topmost"),
      "| tomato:", ctl.tomato_timer.isActive(),
      "| water:", ctl.config.get("water_on"),
      "| follow:", ctl.pet.follow)

print("\n>>> 非命令句应落到对话链路")
feed("明天七点提醒我交房租", 0.2)
t0 = time.time()
while time.time() - t0 < 40:
    app.processEvents()
    time.sleep(0.1)
    if not ctl._chat_busy():
        for _ in range(8):
            app.processEvents()
            time.sleep(0.05)
        break
print("reply:", repr((ctl.history[-1] if ctl.history else {}).get("content", ""))[:120])
print("last_skill:", (ctl._last_skill or {}).get("skill"))
print(">>> 走正常退出流程")
ctl.quit_app()
for _ in range(10):
    app.processEvents()
    time.sleep(0.05)
print("EXIT-CLEAN")
