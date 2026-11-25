# -*- coding: utf-8 -*-
"""GuardWorker 线程冒烟：进度信号 + done 信号 + 结果字段。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import guard_core as g  # noqa: E402

app = QApplication([])
loop = QEventLoop()
progress = []
result = {}


def on_done(rep):
    result.update(rep)
    loop.quit()


def on_failed(msg):
    result["failed"] = msg
    loop.quit()


w = g.GuardWorker(roots=[r"F:\WhaleGirlPet\tools\_guard_samples"])
w.progress.connect(lambda p, m: progress.append((p, m)))
w.done.connect(on_done)
w.failed.connect(on_failed)
w.start()
QTimer.singleShot(90000, loop.quit)
loop.exec()

print("进度消息条数:", len(progress), "首/末:", progress[:1], progress[-1:] if progress else [])
print("failed:", result.get("failed"))
print("score/level/counts:", result.get("score"), result.get("level"), result.get("counts"))
print("findings:", len(result.get("findings") or []), "files:", result.get("files_scanned"),
      "procs:", result.get("processes_checked"), "elapsed:", result.get("elapsed_s"))
if result.get("findings"):
    f = result["findings"][0]
    print("首条:", f["level"], f["score"], f["rule"], os.path.basename(str(f["target"])))
w.wait(3000)
