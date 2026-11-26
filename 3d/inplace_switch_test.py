import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time
from pathlib import Path

import psutil
from PIL import ImageGrab

ROOT = Path(os.environ.get("WHALE3D_TEST_ROOT", r"F:\WhaleGirlPet\3d"))
DOCS = Path(r"F:\WhaleGirlPet\docs")
user32 = ctypes.windll.user32
WM_COMMAND = 0x0111
CB_SETCURSEL = 0x014E

# 64-bit-safe signatures.
user32.FindWindowW.restype = wt.HWND
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.GetDlgItem.restype = wt.HWND
user32.GetDlgItem.argtypes = [wt.HWND, ctypes.c_int]
user32.SendMessageW.restype = ctypes.c_longlong
user32.SendMessageW.argtypes = [wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.PostMessageW.argtypes = [wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM]
user32.GetWindowRect.restype = wt.BOOL
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]


def wait_window(title, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        h = user32.FindWindowW(None, title)
        if h:
            return h
        time.sleep(0.15)
    return 0


def private_bytes(pid):
    try:
        return int(psutil.Process(pid).memory_info().private)
    except Exception:
        return 0


def rect_of(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right - r.left, r.bottom - r.top)


def shot(hwnd, path):
    try:
        x, y, w, h = rect_of(hwnd)
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(path)
        return True
    except Exception as e:
        print("shot failed", e)
        return False


def open_settings(pet):
    user32.PostMessageW(pet, WM_COMMAND, 1003, 0)
    s = wait_window("鲸鱼娘 3D · 设置", 4)
    time.sleep(0.3)
    return s


def close_settings(s):
    if s:
        user32.PostMessageW(s, 0x0010, 0, 0)
        time.sleep(0.25)


def select(hwnd, cid, index):
    c = user32.GetDlgItem(hwnd, cid)
    user32.SendMessageW(c, CB_SETCURSEL, index, 0)


def apply(s):
    user32.PostMessageW(s, WM_COMMAND, 2004, 0)
    time.sleep(0.7)


def run_switch(pet, s, model_index, clip_index=0, face_index=1, animator_index=0):
    select(s, 2007, model_index)
    select(s, 2001, clip_index)
    select(s, 2002, face_index)
    select(s, 2003, animator_index)
    apply(s)


def main():
    env = os.environ.copy()
    env.pop("WHALE3D_SWITCH", None)
    env["WHALE3D_FACE"] = "open"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_ANIMATOR"] = "ozz"
    log = open(ROOT / "inplace_switch.err.log", "w", encoding="utf-8", buffering=1)
    out = open(ROOT / "inplace_switch.log", "w", encoding="utf-8", buffering=1)
    p = subprocess.Popen([str(ROOT / "whale3d.exe")], cwd=str(ROOT), env=env,
                         stdout=out, stderr=log)
    pet = wait_window("WhaleGirl 3D Placeholder", 12)
    print("pet", pet, "pid", p.pid)
    if not pet:
        p.terminate()
        return 2

    samples = []
    def sample(label, seconds=2.0):
        end = time.time() + seconds
        peak = private_bytes(p.pid)
        while time.time() < end:
            peak = max(peak, private_bytes(p.pid))
            time.sleep(0.12)
        samples.append((label, peak))
        print(f"{label}: peak_private={peak}")
        return peak

    time.sleep(4.0)
    before = sample("whale steady", 4.0)
    shot(pet, DOCS / "_3d_inplace_whale_before.png")

    s = open_settings(pet)
    print("settings", s)
    if not s:
        p.terminate()
        return 3
    run_switch(pet, s, 1)  # placeholder
    close_settings(s)
    s1 = sample("placeholder after in-place")
    shot(pet, DOCS / "_3d_inplace_placeholder.png")

    s = open_settings(pet)
    if not s:
        p.terminate()
        return 4
    run_switch(pet, s, 0)  # whale back
    close_settings(s)
    s2 = sample("whale back after in-place")
    shot(pet, DOCS / "_3d_inplace_whale_back.png")

    # One more round to expose monotonic growth.
    s = open_settings(pet)
    if not s:
        p.terminate()
        return 5
    run_switch(pet, s, 1)
    close_settings(s)
    s3 = sample("placeholder round 2")

    s = open_settings(pet)
    if not s:
        p.terminate()
        return 6
    run_switch(pet, s, 0)
    close_settings(s)
    s4 = sample("whale round 2")

    print("samples", samples)
    print("same_pid", p.pid, "alive", p.poll() is None)
    print("children", [(c.pid, c.name()) for c in psutil.Process(p.pid).children(recursive=True)])
    user32.PostMessageW(pet, WM_COMMAND, 1004, 0)
    time.sleep(1)
    try:
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        p.terminate()
    print("exit", p.poll())
    log.close()
    out.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
