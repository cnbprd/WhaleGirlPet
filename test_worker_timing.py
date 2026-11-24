# -*- coding: utf-8 -*-
"""定位：LocalChatWorker 的 isRunning 时序 + 信号是否真的回来。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

import local_llm  # noqa: E402

m = local_llm.ServerManager({"ollama_host": "http://127.0.0.1:11434",
                             "ollama_model": "qwen3.5:4b", "llm_ctx": 4096})
print("backend:", m.backend, "alive:", local_llm.ollama_alive(m.ollama_host))

got = []
w = local_llm.LocalChatWorker(m, [{"role": "user", "content": "说一句话"}],
                              max_tokens=60, temperature=0.2, fmt="json")
w.reply_ready.connect(lambda s: got.append(("ok", s)))
w.failed.connect(lambda s: got.append(("fail", s)))
t0 = time.time()
w.start()
print("isRunning right after start():", w.isRunning())
for i in range(200):
    app.processEvents()
    time.sleep(0.1)
    if i in (0, 1, 2, 5, 10):
        print(f"  t={time.time()-t0:.1f}s running={w.isRunning()} got={len(got)}")
    if got and not w.isRunning():
        break
print("elapsed:", round(time.time() - t0, 1), "running:", w.isRunning(), "got:", got[:1])
