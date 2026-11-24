# -*- coding: utf-8 -*-
"""按窗口标题抓指定窗口（PrintWindow，不受遮挡影响）。

用法：python tools/_shot_hwnd.py "Setup: 鲸鱼娘桌宠" out.png
"""
import ctypes
import ctypes.wintypes as wt
import sys

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

TITLE = sys.argv[1]
OUT = sys.argv[2]

found = []

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def _cb(hwnd, _lp):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    if TITLE in buf.value and user32.IsWindowVisible(hwnd):
        found.append((hwnd, buf.value))
    return True


user32.EnumWindows(WNDENUMPROC(_cb), 0)
print("匹配窗口:", found)

if not found:
    sys.exit(1)

hwnd, title = found[0]
rect = wt.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
w = rect.right - rect.left
h = rect.bottom - rect.top
print("尺寸", w, h)

hdc = user32.GetWindowDC(hwnd)
mem = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mem, bmp)
# PW_RENDERFULLCONTENT = 2，能抓到 DWM/DirectComposition 内容
ok = user32.PrintWindow(hwnd, mem, 2)
print("PrintWindow:", ok)

src = ctypes.windll.gdi32.GetObject_atom if False else None
img = Image.new("RGB", (w, h))
# 从 mem 取像素：用 GetDIBits
bi = ctypes.create_string_buffer(40)
# BITMAPINFOHEADER
import struct
struct.pack_into("<IiiHHIIiiII", bi, 0, 40, w, -h, 1, 32, 0, 0, 2835, 2835, 0, 0)
bits = ctypes.create_string_buffer(w * h * 4)
gdi32.GetDIBits(mem, bmp, 0, h, bits, bi, 0)
img = Image.frombuffer("RGBA", (w, h), bits, "raw", "BGRA", 0, 1).convert("RGB")
img.save(OUT)

gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mem)
user32.ReleaseDC(hwnd, hdc)
print("saved", OUT)
