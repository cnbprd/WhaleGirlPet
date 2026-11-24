# -*- coding: utf-8 -*-
"""按标题抓窗口，自动挑面积最大的那个（避免抓到小的对话框/气泡）。

用法：python tools/_shot_by_title.py "设置" out.png
"""
import ctypes
import ctypes.wintypes as wt
import struct
import sys

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

TITLE = sys.argv[1]
OUT = sys.argv[2]

cands = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def _cb(hwnd, _lp):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    if TITLE == buf.value and user32.IsWindowVisible(hwnd):
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        cands.append((hwnd, buf.value, r.right - r.left, r.bottom - r.top, cls.value))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
for c in cands:
    print("候选", c)
if not cands:
    sys.exit(1)

# 同名窗口很多（Windows 自带的「设置」也是这个名字），优先挑 Qt 窗口
qt = [c for c in cands if c[4].lower().startswith("qt")]
pool = qt or cands
hwnd, title, w, h = max(pool, key=lambda c: c[2] * c[3])[:4]
print("选中", title, w, h)

hdc = user32.GetWindowDC(hwnd)
mem = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mem, bmp)
user32.PrintWindow(hwnd, mem, 2)

bi = ctypes.create_string_buffer(40)
struct.pack_into("<IiiHHIIiiII", bi, 0, 40, w, -h, 1, 32, 0, 0, 2835, 2835, 0, 0)
bits = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(mem, bmp, 0, h, bits, bi, 0)
img = Image.frombuffer("RGBA", (w, h), bits, "raw", "BGRA", 0, 1).convert("RGB")
img.save(OUT)

gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem)
user32.ReleaseDC(hwnd, hdc)
print("saved", OUT, img.size)
