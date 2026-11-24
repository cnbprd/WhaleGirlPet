# -*- coding: utf-8 -*-
"""按窗口标题 + 窗口内相对坐标点击（用于安装向导自动化目检）。

用法：python tools/_click_rel.py "Setup: 鲸鱼娘桌宠" 135 200
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    pass

TITLE = sys.argv[1]
RX = int(sys.argv[2])
RY = int(sys.argv[3])

found = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def _cb(hwnd, _lp):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    if TITLE in buf.value and user32.IsWindowVisible(hwnd):
        found.append(hwnd)
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
if not found:
    print("没找到窗口")
    sys.exit(1)

hwnd = found[0]
user32.ShowWindow(hwnd, 9)
user32.SetForegroundWindow(hwnd)
time.sleep(0.4)

rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
x = rect.left + RX
y = rect.top + RY
print("点击", x, y)
user32.SetCursorPos(x, y)
time.sleep(0.2)
user32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
time.sleep(0.05)
user32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
