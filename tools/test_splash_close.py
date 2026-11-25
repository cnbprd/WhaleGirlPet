# -*- coding: utf-8 -*-
"""验证启动浮层一定会消失。

用法：
  python tools/test_splash_close.py normal   # 正常调用 finish()
  python tools/test_splash_close.py auto     # 完全不调 finish()，靠 15 秒兜底
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import splash  # noqa: E402

u = ctypes.windll.user32
TITLE = "鲸鱼娘加载中"


def find_win():
    res = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _l):
        t = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(h, t, 256)
        if t.value == TITLE:
            res.append((int(h), bool(u.IsWindowVisible(h))))
        return True

    u.EnumWindows(cb, 0)
    return res


mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
app = QApplication([])
sp = splash.LoadingSplash()
sp.show()
app.processEvents()
t0 = time.time()
print(f"[{mode}] 显示后 0.0s 窗口={find_win()}", flush=True)

if mode == "normal":
    QTimer.singleShot(3000, sp.finish)

    def _dump(tag):
        print(f"[normal] {tag} done={sp._done} fade={sp._fade:.3f} closing={sp._closing} "
              f"tm_active={sp._tm.isActive()} tm_left={sp._tm.remainingTime()} "
              f"visible={sp.isVisible()} hwnd={int(sp.winId())} 系统窗口={find_win()}", flush=True)

    QTimer.singleShot(3500, lambda: _dump("+3.5s"))
    QTimer.singleShot(6000, lambda: _dump("+6.0s"))
    QTimer.singleShot(9000, lambda: (_dump("+9.0s"), app.quit()))
else:
    for at in (8, 12, 16, 18):
        QTimer.singleShot(at * 1000, (lambda a: lambda: print(f"[auto] +{a}s 窗口={find_win()}", flush=True))(at))
    QTimer.singleShot(19000, app.quit)

app.exec()
print(f"[{mode}] 结束，残留窗口={find_win()}", flush=True)
