# -*- coding: utf-8 -*-
"""实测：双击桌宠到「设置」面板真正出现，用了多少秒（安装版）。"""
import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def find(title_exact=None, cls_prefix="qt", min_w=0):
    out = []

    def _cb(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.lower().startswith(cls_prefix):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 2)
        user32.GetWindowTextW(hwnd, buf, n + 2)
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        w = r.right - r.left
        if title_exact is not None and buf.value != title_exact:
            return True
        if w < min_w:
            return True
        out.append((hwnd, buf.value, r.left, r.top, w, r.bottom - r.top))
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return out


pets = [p for p in find("鲸鱼娘桌宠")]
print("桌宠窗口", pets)
hwnd, _, x, y, w, h = pets[0]
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
user32.SetForegroundWindow(hwnd)
time.sleep(0.4)

cx, cy = x + w // 2, y + int(h * 0.62)
user32.SetCursorPos(cx, cy)
time.sleep(0.2)
t0 = time.perf_counter()
for _ in range(2):
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.08)

elapsed = None
for _ in range(200):
    if find("设置", min_w=600):
        elapsed = time.perf_counter() - t0
        break
    time.sleep(0.02)

print("面板出现耗时 %.2fs" % (elapsed if elapsed else -1))
print("面板窗口", find("设置", min_w=600))
