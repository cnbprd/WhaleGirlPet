# -*- coding: utf-8 -*-
"""桌面感知：电源状态（拔电/插电）与全屏应用检测。

只用 Windows 官方 Win32 API 只读查询，不注入、不挂钩、不读取窗口内容。
非 Windows 或调用失败时一律返回安全默认值（不拔电、非全屏），不会误触隐藏。
"""
import ctypes
import ctypes.wintypes as wt
import sys

IS_WIN = sys.platform.startswith("win")

# 这些窗口铺满屏幕也不算"全屏应用"，否则桌宠会被自己或桌面壳藏起来
_IGNORE_CLASS = {
    "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow", "ApplicationFrameWindow",
}

_MONITOR_DEFAULTTONEAREST = 2
_COVER_RATIO = 0.995   # 可见区域宽高都要盖住显示器 99.5% 才算全屏
_DWMWA_EXTENDED_FRAME_BOUNDS = 9
_WS_CAPTION = 0x00C00000


class _RECT(ctypes.Structure):
    _fields_ = [("left", wt.LONG), ("top", wt.LONG),
                ("right", wt.LONG), ("bottom", wt.LONG)]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", _RECT),
                ("rcWork", _RECT), ("dwFlags", wt.DWORD)]


class _POWER_STATUS(ctypes.Structure):
    _fields_ = [("ACLineStatus", wt.BYTE), ("BatteryFlag", wt.BYTE),
                ("BatteryLifePercent", wt.BYTE), ("SystemStatusFlag", wt.BYTE),
                ("BatteryLifeTime", wt.DWORD), ("BatteryFullLifeTime", wt.DWORD)]


def power_status() -> dict:
    """{'on_battery': bool, 'percent': int|None, 'has_battery': bool}"""
    out = {"on_battery": False, "percent": None, "has_battery": False}
    if not IS_WIN:
        return out
    try:
        st = _POWER_STATUS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):
            return out
        out["has_battery"] = not bool(st.BatteryFlag & 128) and st.BatteryFlag != 255
        if 0 <= st.BatteryLifePercent <= 100:
            out["percent"] = int(st.BatteryLifePercent)
        # ACLineStatus: 0 = 电池供电, 1 = 接电, 255 = 未知
        out["on_battery"] = bool(out["has_battery"] and st.ACLineStatus == 0)
    except Exception:  # noqa: BLE001
        return {"on_battery": False, "percent": None, "has_battery": False}
    return out


def on_battery() -> bool:
    return bool(power_status()["on_battery"])


def _covers(win_w: int, win_h: int, mon_w: int, mon_h: int, ratio: float = _COVER_RATIO) -> bool:
    """宽和高都盖住显示器 ratio 以上才算全屏。抽出来便于单测边界。"""
    if win_w <= 0 or win_h <= 0 or mon_w <= 0 or mon_h <= 0:
        return False
    return win_w >= mon_w * ratio and win_h >= mon_h * ratio


def foreground_fullscreen(own_hwnd: int = 0) -> bool:
    """前台窗口是否盖满它所在的显示器（并排除桌面壳与自己的窗口）。"""
    if not IS_WIN:
        return False
    u = ctypes.windll.user32
    try:
        hwnd = u.GetForegroundWindow()
        if not hwnd or (own_hwnd and hwnd == int(own_hwnd)):
            return False
        if not u.IsWindowVisible(hwnd):
            return False
        buf = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd, buf, 256)
        if buf.value in _IGNORE_CLASS:
            return False
        # 最小化窗口（IsIconic）不算全屏
        if u.IsIconic(hwnd):
            return False
        rc = _RECT()
        # 优先用 DWM 的"可见边框"：GetWindowRect 含不可见阴影，Chrome 这类自绘窗口会偏大 8px，
        # 直接用会把"最大化"误判成"全屏"，桌宠就会在用户最大化浏览器时莫名消失。
        got = False
        try:
            dwm = ctypes.windll.dwmapi
            got = bool(dwm.DwmGetWindowAttribute(
                hwnd, _DWMWA_EXTENDED_FRAME_BOUNDS,
                ctypes.byref(rc), ctypes.sizeof(_RECT)) == 0)
        except Exception:  # noqa: BLE001
            got = False
        if not got and not u.GetWindowRect(hwnd, ctypes.byref(rc)):
            return False
        mon = u.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        if not u.GetMonitorInfoW(mon, ctypes.byref(mi)):
            return False
        m = mi.rcMonitor
        return _covers(rc.right - rc.left, rc.bottom - rc.top,
                       m.right - m.left, m.bottom - m.top)
    except Exception:  # noqa: BLE001
        return False
