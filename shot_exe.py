# -*- coding: utf-8 -*-
"""实机截图：启动已打包 exe，等窗口出现后抓全屏，存 assets\\_matting\\。"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "assets", "_matting")
os.makedirs(OUT_DIR, exist_ok=True)

EXE = os.path.join(ROOT, "dist", "WhaleGirlPet.exe")

proc = subprocess.Popen([EXE], cwd=os.path.join(ROOT, "dist"))
print("launched pid", proc.pid)
time.sleep(int(sys.argv[1]) if len(sys.argv) > 1 else 22)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()

w = user32.GetSystemMetrics(0)
h = user32.GetSystemMetrics(1)
print("screen", w, h)

hdc = user32.GetDC(0)
mdc = gdi32.CreateCompatibleDC(hdc)
bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
gdi32.SelectObject(mdc, bmp)
gdi32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)

from PIL import Image  # noqa: E402

buf = ctypes.create_string_buffer(w * h * 4)
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]
bi = BITMAPINFOHEADER()
bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
bi.biWidth = w
bi.biHeight = -h
bi.biPlanes = 1
bi.biBitCount = 32
bi.biCompression = 0
gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
name = sys.argv[2] if len(sys.argv) > 2 else "v23-desktop.png"
path = os.path.join(OUT_DIR, name)
img.save(path, quality=92)
print("saved", path, img.size)

gdi32.DeleteObject(bmp)
gdi32.DeleteDC(mdc)
user32.ReleaseDC(0, hdc)
