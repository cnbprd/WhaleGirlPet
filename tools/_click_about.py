# -*- coding: utf-8 -*-
"""点开安装版面板左侧第 5 项「关于与更新」（按客户区比例算坐标）。

用法：python tools/_click_about.py
"""
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32
cands = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def _cb(hwnd, _lp):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    if buf.value == "设置" and user32.IsWindowVisible(hwnd):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.lower().startswith("qt"):
            return True  # 跳过 Windows 自带「设置」等同名窗口
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        cands.append((hwnd, r.right - r.left, r.bottom - r.top))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
if not cands:
    raise SystemExit("没找到「设置」窗口，先跑 _force_open_panel.py")
hwnd = max(cands, key=lambda t: t[1] * t[2])[0]

rc = wt.RECT()
user32.GetClientRect(hwnd, ctypes.byref(rc))
cw, ch = rc.right, rc.bottom
# 侧栏宽 138 / 面板宽约 706 → x≈9.8%；第 5 项中心 y≈29.2%
p = wt.POINT(int(cw * 0.098), int(ch * 0.292))
user32.ClientToScreen(hwnd, ctypes.byref(p))
user32.SetForegroundWindow(hwnd)
time.sleep(0.35)
user32.SetCursorPos(p.x, p.y)
time.sleep(0.2)
for _ in range(2):
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.08)
print("点击", p.x, p.y, "客户区", cw, ch)
