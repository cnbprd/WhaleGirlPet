# -*- coding: utf-8 -*-
"""桌面图标布局：通过 SysListView32 消息读取/写回图标位置。

仅在满屏跑撞图标玩法中使用：先备份原始位置，碰撞时把附近图标挪到下方散落，
慌张结束后完整复位。任何一步失败都静默降级为“不动真实图标”。
"""
import ctypes
import random
from ctypes import wintypes

user32 = ctypes.windll.user32

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_SETITEMPOSITION = LVM_FIRST + 13


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


def _find_defview():
    progman = user32.FindWindowW("Progman", None)
    view = user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
    if view:
        return view

    # 部分系统图标视图挂在 WorkerW 下，枚举查找带 DefView 的 WorkerW
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        child = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if child:
            found.append(child)
            return False
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else 0


def _list_view():
    view = _find_defview()
    if not view:
        return 0
    return user32.FindWindowExW(view, 0, "SysListView32", None)


def _send(hwnd, msg, wparam, lparam):
    return user32.SendMessageTimeoutW(hwnd, msg, wparam, lparam, 0x2, 1000,
                                      ctypes.byref(wintypes.DWORD()))


def available() -> bool:
    try:
        return _list_view() != 0
    except OSError:
        return False


class IconLayout:
    """备份桌面图标位置；scatter 扰动附近图标，restore 全部复位。"""

    def __init__(self):
        self.hwnd = _list_view()
        self.backup = []  # [(index, x, y)]

    def reload(self):
        self.backup = []
        if not self.hwnd:
            return
        try:
            count = _send(self.hwnd, LVM_GETITEMCOUNT, 0, 0)
            for i in range(count):
                pt = POINT()
                _send(self.hwnd, LVM_GETITEMPOSITION, i, ctypes.byref(pt))
                self.backup.append((i, pt.x, pt.y))
        except OSError:
            self.backup = []

    def _set(self, index: int, x: int, y: int):
        lparam = (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)
        _send(self.hwnd, LVM_SETITEMPOSITION, index, lparam)

    def scatter_near(self, x: int, y: int, n: int = 3, spread: int = 120) -> int:
        """把靠近 (x,y) 的 n 个图标挪到下方散落位置，返回挪动数量。"""
        if not self.hwnd or not self.backup:
            return 0
        nearby = [b for b in self.backup if abs(b[1] - x) < spread]
        random.shuffle(nearby)
        moved = 0
        for i, (idx, ox, oy) in enumerate(nearby[:n]):
            nx = ox + random.randint(-spread // 2, spread // 2)
            ny = oy + random.randint(60, 140)
            try:
                self._set(idx, nx, ny)
                moved += 1
            except OSError:
                pass
        return moved

    def restore(self) -> int:
        """把备份位置写回，复位图标；返回复位数量。"""
        if not self.hwnd or not self.backup:
            return 0
        restored = 0
        for idx, ox, oy in self.backup:
            try:
                self._set(idx, ox, oy)
                restored += 1
            except OSError:
                pass
        return restored
