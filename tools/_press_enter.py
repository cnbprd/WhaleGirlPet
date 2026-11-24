# -*- coding: utf-8 -*-
"""激活指定窗口后按 N 次回车（安装向导翻页用）。

用法：python tools/_press_enter.py "Setup: 鲸鱼娘桌宠" 2
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
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1

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
time.sleep(0.5)

for i in range(N):
    user32.keybd_event(0x0D, 0, 0, 0)      # Enter down
    time.sleep(0.05)
    user32.keybd_event(0x0D, 0, 0x0002, 0)  # Enter up
    print("enter", i + 1)
    time.sleep(1.2)
