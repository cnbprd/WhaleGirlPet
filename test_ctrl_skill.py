# -*- coding: utf-8 -*-
"""诊断 Controller 侧能力层：逐 0.1s 打印 worker 状态。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

ctl = Controller(app)
print("llm_on:", ctl.config.get("llm_on"), "available:", __import__("local_llm").available())
print("backend:", ctl.llm.backend, "host:", ctl.llm.ollama_host)

ctl.send_chat("明天七点提醒我交房租")
print("after send_chat: skill_worker=", ctl.skill_worker, "llm_worker=", ctl.llm_worker,
      "busy=", ctl._chat_busy())

t0 = time.time()
for i in range(120):
    app.processEvents()
    time.sleep(0.1)
    sw = ctl.skill_worker
    lw = ctl.llm_worker
    if i % 5 == 0:
        print(f"t={time.time()-t0:.1f}s busy={ctl._chat_busy()} "
              f"skill_run={sw.isRunning() if sw else None} "
              f"llm_run={lw.isRunning() if lw else None} "
              f"last_skill={ctl._last_skill.get('skill')}")
    if ctl.history and ctl.history[-1]["role"] == "assistant":
        print("GOT REPLY:", repr(ctl.history[-1]["content"]))
        print("last_skill:", ctl._last_skill)
        break
else:
    print("NO REPLY in 12s. history tail:", ctl.history[-3:])
