# -*- coding: utf-8 -*-
"""列出所有可见顶层窗口：标题 / 尺寸 / 位置 / 类名，用于排查窗口没打开的问题。"""
import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
rows = []


def _cb(hwnd, _lp):
    if not user32.IsWindowVisible(hwnd):
        return True
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return True
    buf = ctypes.create_unicode_buffer(n + 2)
    user32.GetWindowTextW(hwnd, buf, n + 2)
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w > 200 and h > 200:
        rows.append((buf.value, w, h, r.left, r.top, cls.value))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
for t, w, h, x, y, c in sorted(rows, key=lambda r: -r[1] * r[2]):
    print(f"{w:5d}x{h:<5d} @({x},{y})  [{c}]  {t[:60]}")
