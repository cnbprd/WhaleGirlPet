# -*- coding: utf-8 -*-
"""探针：splash 的 24ms timer 为什么不回调。

同时挂三个计时器：
  A splash 自己的 _tm（monkey-patch 计数）
  B 一个全新 QTimer(24ms)
  C 一个全新 QTimer(500ms)
看哪些在跑，进而判断是"Qt 定时器整体不跑"还是"这个 timer 断了"。
"""
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import splash  # noqa: E402

app = QApplication([])
sp = splash.LoadingSplash()
sp.show()
app.processEvents()

n = {"A": 0, "B": 0, "C": 0}

# A：把原来连到 _tick 的槽换成计数 + 原来的逻辑
try:
    sp._tm.timeout.disconnect()
except Exception:
    pass
orig_tick = sp._tick


def _a():
    n["A"] += 1
    orig_tick()


sp._tm.timeout.connect(_a)

tb = QTimer()
tb.setInterval(24)
tb.timeout.connect(lambda: n.__setitem__("B", n["B"] + 1))
tb.start()

tc = QTimer()
tc.setInterval(500)
tc.timeout.connect(lambda: n.__setitem__("C", n["C"] + 1))
tc.start()

t0 = time.time()


def dump(tag):
    print(f"{tag} t={time.time()-t0:.1f}s 计数 A={n['A']} B={n['B']} C={n['C']} "
          f"fade={sp._fade:.3f} splash_tm_active={sp._tm.isActive()} "
          f"B_active={tb.isActive()}", flush=True)


for at in (1, 3, 6):
    QTimer.singleShot(at * 1000, (lambda a: lambda: dump(f"+{a}s"))(at))
QTimer.singleShot(7000, app.quit)
app.exec()
dump("结束")
