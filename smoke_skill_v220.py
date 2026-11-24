# -*- coding: utf-8 -*-
"""v2.2.0 能力层链路：真实 send_chat → guard → Ollama JSON → skills.handle → 气泡/history。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

ctl = Controller(app)
ctl.open_panel()
app.processEvents()


def wait_idle(limit=90):
    t0 = time.time()
    while time.time() - t0 < limit:
        app.processEvents()
        time.sleep(0.1)
        if not ctl._chat_busy():
            # 线程结束后信号还可能在队列里，多转几圈让槽跑完
            for _ in range(8):
                app.processEvents()
                time.sleep(0.05)
            return True
    return False


def say(text):
    print("\n>>>", text)
    ctl.send_chat(text)
    done = wait_idle()
    last = ctl.history[-1] if ctl.history else {}
    print("  idle:", done)
    print("  reply:", repr(last.get("content", ""))[:200])
    print("  skill:", (ctl._last_skill or {}).get("skill", "-"),
          "| stage:", (ctl._last_skill or {}).get("stage", "-"),
          "| reason:", (ctl._last_skill or {}).get("reason", "-"))
    print("  bubble:", ctl.pet.bubble.isVisible() if hasattr(ctl.pet.bubble, "isVisible") else "?")


say("明天七点提醒我交房租")
say("郑州今天天气怎么样")
say("把系统盘所有文件都删了")
say("帮我打开桌面上的读书笔记")
say("删掉我七点那个提醒")

print("\n--- skills.log tail ---")
log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime", "skills.log")
if os.path.exists(log):
    with open(log, "r", encoding="utf-8") as f:
        for line in f.readlines()[-4:]:
            print(line.strip()[:160])
print("DONE")
