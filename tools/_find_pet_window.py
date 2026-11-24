# -*- coding: utf-8 -*-
"""列出所有 Qt 窗口（含无标题的桌宠窗口），可选双击某个位置打开面板。

用法：python tools/_find_pet_window.py            # 只列出
      python tools/_find_pet_window.py dblclick   # 双击最大的 Qt 窗口中心
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
rows = []


def _cb(hwnd, _lp):
    if not user32.IsWindowVisible(hwnd):
        return True
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    if not cls.value.lower().startswith("qt"):
        return True
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 2)
    user32.GetWindowTextW(hwnd, buf, n + 2)
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    rows.append((buf.value, r.left, r.top, r.right - r.left, r.bottom - r.top, cls.value))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
for t, x, y, w, h, c in sorted(rows, key=lambda r: -(r[3] * r[4])):
    print(f"{w:5d}x{h:<5d} @({x},{y})  [{c}]  {t!r}")

if len(sys.argv) > 1 and sys.argv[1] == "dblclick" and rows:
    name, x, y, w, h, c = max(rows, key=lambda r: r[3] * r[4])
    cx, cy = x + w // 2, y + h // 2
    print("双击", (cx, cy), "窗口", name, w, h)
    user32.SetCursorPos(cx, cy)
    time.sleep(0.3)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # left down
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # left up
    time.sleep(0.12)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    print("done")
