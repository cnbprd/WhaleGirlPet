# -*- coding: utf-8 -*-
"""① 真实首帧探针：不靠内存近似，直接用 Win32 找窗口 + 抓像素判断"画面真的出现了"。

三个时刻：
  A 引导进程出现（Popen 返回后第一次找到进程）
  B 窗口可见（EnumWindows → 属于该 PID + IsWindowVisible + 尺寸 > 50px）
  C 首帧有内容（对窗口矩形 ImageGrab 抓图，灰度标准差 > 8 → 不是纯色/透明）
用法：python tools/first_frame.py [exe] [观察秒数]
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import sys
import time

import psutil

EXE = sys.argv[1] if len(sys.argv) > 1 else r"F:\WhaleGirlPet\dist\WhaleGirlPet\WhaleGirlPet.exe"
WATCH = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect

try:
    from PIL import ImageGrab, ImageStat
    HAS_PIL = True
except Exception:  # noqa: BLE001
    HAS_PIL = False


def pids_of(exe):
    """onefile 有父/子两个同名进程，窗口在子进程上，必须一起查。"""
    out = []
    for p in psutil.process_iter(["exe"]):
        try:
            if os.path.basename(p.info["exe"] or "").lower() == os.path.basename(exe).lower():
                out.append(p.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def visible_rects(pid):
    """该 PID 下所有可见、有尺寸的顶层窗口矩形。"""
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, lparam):
        try:
            if not IsWindowVisible(hwnd):
                return True
            wpid = wt.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value != pid:
                return True
            r = wt.RECT()
            GetWindowRect(hwnd, ctypes.byref(r))
            w, h = r.right - r.left, r.bottom - r.top
            if w > 50 and h > 50:
                out.append((hwnd, r.left, r.top, r.right, r.bottom))
        except Exception:  # noqa: BLE001
            pass
        return True

    EnumWindows(cb, 0)
    return out


def frame_std(rect):
    """抓这块屏幕区域，返回灰度标准差；抓不到返回 -1。"""
    if not HAS_PIL:
        return -1
    try:
        l, t, r, b = rect
        img = ImageGrab.grab(bbox=(max(0, l), max(0, t), max(1, r), max(1, b)),
                             all_screens=True)
        return ImageStat.Stat(img.convert("L")).stddev[0]
    except Exception as e:  # noqa: BLE001
        global _grab_err
        _grab_err = repr(e)[:80]
        return -1


_grab_err = ""


def main():
    for p in psutil.process_iter(["exe"]):
        try:
            if os.path.basename(p.info["exe"] or "").lower() == os.path.basename(EXE).lower():
                p.kill()
        except Exception:  # noqa: BLE001
            pass
    time.sleep(0.6)

    t0 = time.perf_counter()
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pids = []
    t_proc = t_win = t_frame = None
    peak_std = 0.0
    last_grab = -9.0
    while True:
        el = time.perf_counter() - t0
        if not pids or int(el * 10) % 3 == 0:
            # onefile 的子进程要 4 秒后才出现，必须持续刷新，否则永远只看父进程
            pids = pids_of(EXE) or pids
            if pids and t_proc is None:
                t_proc = el
        if pids:
            rects = []
            for pid in pids:
                rects.extend(visible_rects(pid))
            if rects and t_win is None:
                t_win = el
            if rects and t_frame is None and el - last_grab >= 0.08:
                last_grab = el
                best = max((frame_std((rt[1], rt[2], rt[3], rt[4])) for rt in rects), default=-1)
                peak_std = max(peak_std, best)
                if best > 8:
                    t_frame = el
        if el > WATCH:
            break
        time.sleep(0.02)

    print(f"exe          {EXE}")
    print(f"A 进程出现    {t_proc if t_proc else -1:.2f} s")
    print(f"B 窗口可见    {t_win if t_win else -1:.2f} s")
    print(f"C 首帧有内容  {t_frame if t_frame else -1:.2f} s  （灰度 std 峰值 {peak_std:.1f}）")
    if _grab_err:
        print(f"抓图错误      {_grab_err}")

    for p in psutil.process_iter(["exe"]):
        try:
            if os.path.basename(p.info["exe"] or "").lower() == os.path.basename(EXE).lower():
                p.kill()
        except Exception:  # noqa: BLE001
            pass
    try:
        proc.wait(timeout=6)
    except Exception:
        pass


if __name__ == "__main__":
    main()
