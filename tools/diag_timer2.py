# -*- coding: utf-8 -*-
"""第二次探针：正常 tick + 3 秒后 finish，捕获 _tick 内部异常。"""
import sys
import traceback

sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import splash  # noqa: E402

app = QApplication([])
sp = splash.LoadingSplash()
sp.show()
app.processEvents()

errs = []
n = {"tick": 0}
orig = sp._tick
try:
    sp._tm.timeout.disconnect()
except Exception:
    pass


def _wrap():
    n["tick"] += 1
    try:
        orig()
    except Exception as e:  # noqa: BLE001
        errs.append(f"{e!r}")
        if len(errs) <= 3:
            traceback.print_exc()


sp._tm.timeout.connect(_wrap)


def dump(tag):
    print(f"{tag} tick={n['tick']} fade={sp._fade:.3f} done={sp._done} "
          f"closing={sp._closing} visible={sp.isVisible()} 异常数={len(errs)} "
          f"{errs[:2]}", flush=True)


QTimer.singleShot(3000, sp.finish)
for at in (2, 4, 6):
    QTimer.singleShot(at * 1000, (lambda a: lambda: dump(f"+{a}s"))(at))
QTimer.singleShot(7000, app.quit)
app.exec()
dump("结束")
