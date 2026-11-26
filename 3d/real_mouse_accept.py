import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(r"F:\WhaleGirlPet\3d")
LOG = ROOT / "real_mouse_accept.log"

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Explicit 64-bit-safe signatures. The previous harness let ctypes use the
# default c_int restype and default 32-bit argument conversion, which both
# truncated some window handles and raised OverflowError inside the WndProc.
LRESULT = ctypes.c_longlong
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM]
user32.CreateWindowExW.restype = wt.HWND
user32.CreateWindowExW.argtypes = [ctypes.c_ulong, wt.LPCWSTR, wt.LPCWSTR,
                                   ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, wt.HWND, wt.HMENU,
                                   wt.HINSTANCE, wt.LPVOID]
user32.WindowFromPoint.restype = wt.HWND
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.GetParent.restype = wt.HWND
user32.GetParent.argtypes = [wt.HWND]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
gdi32.CreateSolidBrush.restype = wt.HBRUSH
gdi32.CreateSolidBrush.argtypes = [wt.COLORREF]
gdi32.DeleteObject.restype = wt.BOOL
gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
user32.FillRect.restype = ctypes.c_int
user32.FillRect.argtypes = [wt.HDC, ctypes.POINTER(wt.RECT), wt.HBRUSH]

# Per-monitor DPI awareness so screen coordinates match the pet's physical pixels.
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
except Exception:
    pass

LRESULT = ctypes.c_longlong
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM)

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_ERASEBKGND = 0x0014
BN_CLICKED = 0
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = wt.HWND(-1)

logf = open(LOG, "w", encoding="utf-8", buffering=1)


def log(s):
    print(s)
    logf.write(s + "\n")


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


state = {"underlay": 0, "button": 0, "clicks": 0, "parent_clicks": 0}


@WNDPROC
def proc(hwnd, msg, wparam, lparam):
    if msg == WM_LBUTTONDOWN:
        state["parent_clicks"] += 1
        log(f"underlay WM_LBUTTONDOWN hwnd={hwnd} x={lparam & 0xffff} y={(lparam >> 16) & 0xffff}")
    elif msg == WM_COMMAND:
        code = (wparam >> 16) & 0xffff
        cid = wparam & 0xffff
        if code == BN_CLICKED and cid == 1:
            state["clicks"] += 1
            log(f"underlay BN_CLICKED id={cid} count={state['clicks']}")
    elif msg == WM_ERASEBKGND:
        hdc = wt.HDC(wparam)
        rect = wt.RECT()
        user32.GetClientRect(hwnd, ctypes.byref(rect))
        brush = gdi32.CreateSolidBrush(0x00FFFFFF)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        return 1
    elif msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def pump(seconds=0.3):
    end = time.time() + seconds
    msg = wt.MSG()
    while time.time() < end:
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.02)


def find_window(title):
    return user32.FindWindowW(None, title)


def wait_window(title, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        h = find_window(title)
        if h:
            return h
        pump(0.2)
    return 0


def rect_of(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def click_at(x, y):
    user32.SetCursorPos(x, y)
    pump(0.15)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # LEFTDOWN
    pump(0.1)
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # LEFTUP
    pump(0.5)


def drag_from_to(x1, y1, x2, y2):
    user32.SetCursorPos(x1, y1)
    pump(0.2)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    pump(0.2)
    user32.SetCursorPos(x2, y2)
    pump(0.3)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    pump(0.5)


def main():
    inst = kernel32.GetModuleHandleW(None)
    cls = WNDCLASSW()
    cls.lpfnWndProc = proc
    cls.hInstance = inst
    cls.lpszClassName = "Whale3DRealMouseUnderlay"
    if not user32.RegisterClassW(ctypes.byref(cls)):
        log("RegisterClass failed")
        return 2

    # Place the underlay where the pet will be moved. It stays non-topmost,
    # so the pet's always-on-top flag keeps the pet above it.
    ux, uy, uw, uh = 1200, 300, 420, 620
    under = user32.CreateWindowExW(
        WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
        cls.lpszClassName,
        "Whale3D real-mouse underlay",
        WS_POPUP | WS_VISIBLE,
        ux, uy, uw, uh,
        None, None, inst, None,
    )
    if not under:
        log("CreateWindowEx underlay failed")
        return 3
    state["underlay"] = under
    button = user32.CreateWindowExW(
        0,
        "BUTTON",
        "CLICK TARGET",
        WS_CHILD | WS_VISIBLE,
        0, 0, uw, uh,
        under, wt.HANDLE(1), inst, None,
    )
    state["button"] = button
    user32.ShowWindow(under, 5)  # SW_SHOW
    user32.UpdateWindow(under)
    log(f"underlay hwnd={under} button={button} rect={rect_of(under)}")

    env = os.environ.copy()
    env["WHALE3D_FACE"] = "open"
    env["WHALE3D_CLIP"] = "idle"
    env["WHALE3D_ANIMATOR"] = "ozz"
    out = open(ROOT / "real_mouse_accept.err.log", "w", encoding="utf-8", buffering=1)
    pet = subprocess.Popen(
        [str(ROOT / "whale3d.exe")],
        cwd=str(ROOT),
        env=env,
        stdout=out,
        stderr=out,
    )

    ph = wait_window("WhaleGirl 3D Placeholder")
    log(f"pet hwnd={ph} pid={pet.pid}")
    if not ph:
        pet.terminate()
        user32.DestroyWindow(under)
        return 4

    user32.SetWindowPos(ph, HWND_TOPMOST, ux, uy, uw, uh,
                        SWP_SHOWWINDOW)
    pump(2.0)
    pr = rect_of(ph)
    log(f"pet rect={pr}")

    corner = (ux + 8, uy + 8)
    center = (ux + 210, uy + 300)

    def win_info(h):
        cls = ctypes.create_unicode_buffer(128)
        txt = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 128)
        user32.GetWindowTextW(h, txt, 256)
        return f"{h} class={cls.value!r} text={txt.value!r} parent={user32.GetParent(h)} rect={rect_of(h)}"

    h_corner = user32.WindowFromPoint(wt.POINT(*corner))
    h_center = user32.WindowFromPoint(wt.POINT(*center))
    log(f"WindowFromPoint corner={win_info(h_corner)}")
    log(f"button={win_info(button)}")
    log(f"WindowFromPoint center={win_info(h_center)} pet={ph}")

    # Real cursor click at the transparent corner. It must reach the button.
    clicks_before = state["clicks"]
    click_at(*corner)
    log(f"after corner click: clicks={state['clicks']} parent_clicks={state['parent_clicks']}")

    # The click may have raised the underlay; put the pet back on top.
    user32.SetWindowPos(ph, HWND_TOPMOST, ux, uy, uw, uh, SWP_SHOWWINDOW)
    pump(0.3)

    # Real cursor click/drag at the character center. It must move the pet.
    before = rect_of(ph)
    drag_from_to(center[0], center[1], center[0] + 35, center[1] + 25)
    after = rect_of(ph)
    log(f"drag pet rect before={before} after={after} moved={before != after}")
    log(f"after center drag underlay clicks={state['clicks']} parent_clicks={state['parent_clicks']}")

    # Raise the pet back to top after the underlay click, then verify corner
    # still routes to the button.
    user32.SetWindowPos(ph, HWND_TOPMOST, after[0], after[1], uw, uh, SWP_SHOWWINDOW)
    pump(0.5)
    new_corner = (after[0] + 8, after[1] + 8)
    h2 = user32.WindowFromPoint(wt.POINT(*new_corner))
    log(f"WindowFromPoint after drag corner={win_info(h2)}")

    # Leave the pet for a moment, then ask it to exit through its tray command.
    pump(0.5)
    user32.PostMessageW(ph, WM_COMMAND, 1004, 0)
    pump(0.8)
    try:
        pet.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pet.terminate()
    log(f"pet exit={pet.poll()}")

    user32.DestroyWindow(under)
    pump(0.3)
    out.close()
    log("done")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        logf.close()
