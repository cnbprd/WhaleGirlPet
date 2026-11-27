#!/usr/bin/env python3
"""Probe whether the 3D sprite card lets desktop clicks pass through.

Run this only after the 24h soak has finished. By default it launches one
temporary 3D process, shows a single card, and performs a dry probe. Add
--click to create a small target window and send one real left click.

The script never attaches to, stops, or modifies the 24h soak PID. If --pid is
used, it only inspects the window belonging to that exact PID.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = ROOT / "whale3d.exe"
DEFAULT_LOG = ROOT.parent / "build" / "click_through.log"
DEFAULT_OUT = ROOT.parent / "docs" / "click-through-result.json"
CARD_IDS = (
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat", "action/wave", "action/dance",
    "action/type", "action/balloon", "action/fireworks", "action/lion",
    "action/change",
)
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTTRANSPARENT = -1
SPRITE_RECT_RE = re.compile(r"Sprite rect: \((\d+),(\d+) (\d+)x(\d+)\)")

if sys.platform != "win32":
    raise SystemExit("check_click_through.py is Windows-only")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def _init_win32() -> None:
    user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ScreenToClient.restype = wintypes.BOOL
    user32.SendMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.SendMessageW.restype = wintypes.LPARAM
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.mouse_event.argtypes = [
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD
    ]
    user32.mouse_event.restype = None


_init_win32()
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def find_windows_for_pid(pid: int) -> list[int]:
    found: list[int] = []

    @EnumWindowsProc
    def callback(hwnd: int, _lparam: int) -> int:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(int(hwnd))
        return 1

    user32.EnumWindows(callback, 0)
    return found


def window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def window_pid(hwnd: int) -> int:
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    return int(owner.value)


def client_geometry(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetClientRect failed")
    origin = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError("ClientToScreen failed")
    return origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top


def card_from_manifest(card_id: str) -> tuple[int, int]:
    manifest_path = ROOT.parent / "assets" / "2d_bridge" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in data.get("cards", []):
        if entry.get("id") == card_id:
            rect = entry.get("rect")
            if isinstance(rect, list) and len(rect) == 4:
                return int(rect[2]), int(rect[3])
    raise RuntimeError(f"card not found in manifest: {card_id}")


def fallback_card_rect(card_id: str, client_w: int, client_h: int) -> tuple[int, int, int, int]:
    card_w, card_h = card_from_manifest(card_id)
    height = min(220.0, client_h * 0.36)
    width = height * card_w / card_h
    return (
        int(client_w - width - 12.0),
        int(client_h - 12.0 - height),
        int(width),
        int(height),
    )


def read_sprite_rect(log_path: Path, timeout: float) -> tuple[int, int, int, int] | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            matches = SPRITE_RECT_RE.findall(text)
            if matches:
                x, y, w, h = matches[-1]
                return int(x), int(y), int(w), int(h)
        time.sleep(0.2)
    return None


def wait_for_window(pid: int, timeout: float) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        candidates = find_windows_for_pid(pid)
        titled = [h for h in candidates if "鲸鱼娘" in window_title(h)]
        if titled:
            return titled[-1]
        if candidates:
            return candidates[-1]
        time.sleep(0.2)
    raise RuntimeError(f"3D window not found for PID {pid}")


def pack_point(x: int, y: int) -> int:
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def hit_test(hwnd: int, screen_x: int, screen_y: int) -> int:
    result = user32.SendMessageW(
        hwnd, WM_NCHITTEST, 0, pack_point(screen_x, screen_y)
    )
    return int(result)


def window_from_point(screen_x: int, screen_y: int) -> int:
    return int(user32.WindowFromPoint(wintypes.POINT(screen_x, screen_y)))


def describe_window(hwnd: int) -> dict[str, object]:
    if not hwnd:
        return {"hwnd": 0, "pid": 0, "title": ""}
    return {
        "hwnd": int(hwnd),
        "pid": window_pid(hwnd),
        "title": window_title(hwnd),
    }


class ClickTarget:
    """A small Tk target that sits behind the always-on-top 3D window."""

    def __init__(self, screen_x: int, screen_y: int, size: int = 96) -> None:
        import tkinter as tk
        self._tk = tk
        self._root = tk.Tk()
        self._root.withdraw()
        self._top = tk.Toplevel(self._root)
        self._top.overrideredirect(True)
        self._top.geometry(f"{size}x{size}+{screen_x - size // 2}+{screen_y - size // 2}")
        self._top.configure(bg="#202020")
        self._top.attributes("-topmost", False)
        self._clicks = 0
        self._top.bind("<Button-1>", self._on_click)
        self._top.update_idletasks()
        self._top.lift()
        self._pump(0.2)

    def _on_click(self, _event) -> None:
        self._clicks += 1

    def _pump(self, seconds: float) -> None:
        deadline = time.time() + seconds
        while time.time() < deadline:
            self._root.update()
            time.sleep(0.01)

    @property
    def clicks(self) -> int:
        return self._clicks

    def click_here(self, screen_x: int, screen_y: int) -> int:
        old = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(old))
        user32.SetCursorPos(screen_x, screen_y)
        self._pump(0.1)
        user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        self._pump(0.1)
        user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        self._pump(0.6)
        user32.SetCursorPos(old.x, old.y)
        return self._clicks

    def close(self) -> None:
        try:
            self._top.destroy()
            self._root.destroy()
        except Exception:
            pass


def launch_3d(card: str, ttl_ms: int, log_path: Path, exe: Path) -> subprocess.Popen:
    if not exe.exists():
        raise RuntimeError(f"3D exe not found: {exe}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("WHALE3D_FREEZE", None)
    env.pop("WHALE3D_LONGRUN_OFFSCREEN", None)
    env["WHALE3D_CARD"] = card
    env["WHALE3D_CARD_TTL"] = str(ttl_ms)
    env["WHALE3D_SPRITE_TRACE"] = "1"
    env["WHALE3D_LOG"] = str(log_path)
    return subprocess.Popen(
        [str(exe)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--pid", type=int, default=0, help="inspect an existing test PID")
    parser.add_argument("--card", choices=CARD_IDS, default="expression/happy")
    parser.add_argument("--ttl-ms", type=int, default=10000)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--wait-s", type=float, default=10.0)
    parser.add_argument("--click", action="store_true", help="send one real click")
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    proc: subprocess.Popen | None = None
    target: ClickTarget | None = None
    try:
        if args.pid:
            pid = args.pid
            proc = None
            hwnd = wait_for_window(pid, args.wait_s)
            print(f"attach pid={pid} hwnd=0x{hwnd:x}")
        else:
            log_path = args.log
            if log_path.exists():
                log_path.unlink()
            proc = launch_3d(args.card, args.ttl_ms, log_path, args.exe)
            pid = proc.pid
            hwnd = wait_for_window(pid, args.wait_s)
            print(f"launch pid={pid} hwnd=0x{hwnd:x}")

        client_x, client_y, client_w, client_h = client_geometry(hwnd)
        sprite_rect = read_sprite_rect(args.log, 4.0)
        if sprite_rect is None:
            sprite_rect = fallback_card_rect(args.card, client_w, client_h)
            print("warning: Sprite rect not logged; using manifest fallback")
        card_x, card_y, card_w, card_h = sprite_rect
        screen_x = client_x + card_x + card_w // 2
        screen_y = client_y + card_y + card_h // 2

        if screen_x < 0 or screen_y < 0:
            raise RuntimeError("card is offscreen; run without offscreen mode")

        card_hit = hit_test(hwnd, screen_x, screen_y)
        model_x = client_x + client_w // 2
        model_y = client_y + client_h // 2
        model_hit = hit_test(hwnd, model_x, model_y)
        under_point = describe_window(window_from_point(screen_x, screen_y))

        if args.click:
            target = ClickTarget(screen_x, screen_y)
            # Re-check after the target exists so the report names the window
            # that actually sits under the card.
            under_point = describe_window(window_from_point(screen_x, screen_y))
            clicks_before = target.clicks
            clicks_after = target.click_here(screen_x, screen_y)
            target_result = {
                "clicks_before": clicks_before,
                "clicks_after": clicks_after,
                "received": clicks_after > clicks_before,
            }
        else:
            target_result = None

        report = {
            "ok": card_hit == HTTRANSPARENT,
            "hwnd": int(hwnd),
            "pid": pid,
            "client": {
                "x": client_x, "y": client_y, "w": client_w, "h": client_h,
            },
            "card_rect": {
                "x": card_x, "y": card_y, "w": card_w, "h": card_h,
                "screen_x": screen_x, "screen_y": screen_y,
            },
            "card_hit_test": card_hit,
            "model_hit_test": model_hit,
            "card_expected": "HTTRANSPARENT (-1)",
            "model_expected": "HTCLIENT (1)",
            "window_from_point": under_point,
            "target": target_result,
            "mode": "click" if args.click else "dry-run",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))

        passed = card_hit == HTTRANSPARENT
        if args.click and target_result is not None:
            passed = passed and bool(target_result["received"])
        return 0 if passed else 1
    finally:
        if target is not None:
            target.close()
        if not args.keep_open:
            stop_process(proc)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
