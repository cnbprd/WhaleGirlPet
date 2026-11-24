# -*- coding: utf-8 -*-
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
QueryFullProcessImageName = ctypes.windll.kernel32.QueryFullProcessImageNameW
OpenProcess = ctypes.windll.kernel32.OpenProcess
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def proc_path(pid):
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    ok = QueryFullProcessImageName(h, 0, buf, ctypes.byref(size))
    ctypes.windll.kernel32.CloseHandle(h)
    return buf.value if ok else ""


def cb(hwnd, _):
    if not IsWindowVisible(hwnd):
        return True
    pid = wintypes.DWORD()
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    length = GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buf, length + 1)
    rect = wintypes.RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    path = proc_path(pid.value)
    if "Windows\\" not in path and "Program Files" not in path:
        print(f"pid={pid.value} title={buf.value!r} "
              f"rect=({rect.left},{rect.top},{rect.right},{rect.bottom}) path={path}")
    return True


EnumWindows(EnumWindowsProc(cb), 0)
