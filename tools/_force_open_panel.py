# -*- coding: utf-8 -*-
"""把桌宠窗口强制置顶，再双击其中心，尝试打开面板。

用法：python tools/_force_open_panel.py
"""
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
target = []


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
    if buf.value == "鲸鱼娘桌宠":
        target.append((hwnd, r.left, r.top, r.right - r.left, r.bottom - r.top))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
print("找到桌宠窗口", target)
if not target:
    raise SystemExit(1)

hwnd, x, y, w, h = target[0]
user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
user32.SetForegroundWindow(hwnd)
time.sleep(0.4)

# 取窗口底部靠中间的位置（人物脚上方，避免点到透明空区）
cx, cy = x + w // 2, y + int(h * 0.62)
print("双击坐标", cx, cy)
user32.SetCursorPos(cx, cy)
time.sleep(0.25)
for _ in range(2):
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.04)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.10)
print("已双击")
