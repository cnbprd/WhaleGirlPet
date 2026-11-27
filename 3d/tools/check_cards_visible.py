#!/usr/bin/env python3
"""Capture all 17 2D cards from one visible 3D instance.

Run this only after the 24h soak has finished. The script refuses to start if
any whale3d.exe is already running, launches exactly one temporary instance,
sends each card over UDP, captures the client area and card crop, and builds a
contact sheet for visual review.

It never attaches to, stops, or modifies the 24h soak PID.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageOps
import psutil

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = ROOT / "whale3d.exe"
DEFAULT_OUT = ROOT.parent / "docs"
CARD_IDS = (
    "expression/idle", "expression/happy", "expression/eat", "expression/walk",
    "expression/sleep", "expression/sleepy", "expression/shy", "expression/angry",
    "expression/curious", "expression/pat", "action/wave", "action/dance",
    "action/type", "action/balloon", "action/fireworks", "action/lion",
    "action/change",
)
UDP_PORT = 47832

if sys.platform != "win32":
    raise SystemExit("check_cards_visible.py is Windows-only")

user32 = ctypes.WinDLL("user32", use_last_error=True)


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


def client_geometry(hwnd: int) -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetClientRect failed")
    origin = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError("ClientToScreen failed")
    return origin.x, origin.y, rect.right, rect.bottom


def manifest_cards() -> dict[str, tuple[int, int]]:
    path = ROOT.parent / "assets" / "2d_bridge" / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    cards: dict[str, tuple[int, int]] = {}
    for entry in data.get("cards", []):
        rect = entry.get("rect")
        if isinstance(rect, list) and len(rect) == 4:
            cards[str(entry.get("id"))] = (int(rect[2]), int(rect[3]))
    return cards


def card_rect(card_id: str, client_w: int, client_h: int) -> tuple[int, int, int, int]:
    cards = manifest_cards()
    if card_id not in cards:
        raise RuntimeError(f"card not found in manifest: {card_id}")
    card_w, card_h = cards[card_id]
    height = min(220.0, client_h * 0.36)
    width = height * card_w / card_h
    return (
        int(client_w - width - 12.0),
        int(client_h - 12.0 - height),
        int(width),
        int(height),
    )


def capture_client(hwnd: int, path: Path) -> Image.Image:
    x, y, w, h = client_geometry(hwnd)
    image = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGB")
    image.save(path)
    return image


def wait_log(log_path: Path, needle: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            if needle in text:
                return True
        time.sleep(0.1)
    return False


def send_card(card_id: str, ttl_ms: int) -> None:
    payload = {
        "emotion": "happy",
        "intensity": 0.8,
        "card": card_id,
        "card_ttl_ms": ttl_ms,
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", UDP_PORT))
    finally:
        sock.close()


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


def font(size: int) -> ImageFont.ImageFont:
    for path in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def build_contact_sheet(items: list[dict[str, object]], out_path: Path) -> None:
    tile_w, tile_h = 180, 236
    label_h = 26
    cols, rows = 4, 5
    sheet = Image.new("RGB", (tile_w * cols, (tile_h + label_h) * rows), "#202020")
    draw = ImageDraw.Draw(sheet)
    label_font = font(13)
    for index, item in enumerate(items):
        col = index % cols
        row = index // cols
        x = col * tile_w
        y = row * (tile_h + label_h)
        crop_path = Path(str(item["crop"]))
        if crop_path.exists():
            image = Image.open(crop_path).convert("RGB")
            fitted = ImageOps.contain(image, (tile_w - 8, tile_h - 8))
            sheet.paste(fitted, (x + (tile_w - fitted.width) // 2,
                                 y + (tile_h - fitted.height) // 2))
        else:
            draw.rectangle((x + 4, y + 4, x + tile_w - 4, y + tile_h - 4),
                           outline="#804040", width=2)
        draw.text((x + 6, y + tile_h + 4), str(item["card"]), fill="#dddddd",
                  font=label_font)
    sheet.save(out_path)


def launch_3d(exe: Path, log_path: Path) -> subprocess.Popen:
    if not exe.exists():
        raise RuntimeError(f"3D exe not found: {exe}")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        log_path.unlink()
    env = os.environ.copy()
    env.pop("WHALE3D_FREEZE", None)
    env.pop("WHALE3D_LONGRUN_OFFSCREEN", None)
    env.pop("WHALE3D_CARD", None)
    env["WHALE3D_SPRITE_TRACE"] = "1"
    env["WHALE3D_LOG"] = str(log_path)
    return subprocess.Popen(
        [str(exe)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def any_whale3d() -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name in {"whale3d.exe", "whale3d"}:
                found.append({"pid": proc.info.get("pid"), "cmdline": proc.info.get("cmdline")})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--ttl-ms", type=int, default=6000)
    parser.add_argument("--gap-s", type=float, default=0.9)
    parser.add_argument("--timeout-s", type=float, default=4.0)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    existing = any_whale3d()
    if existing:
        raise RuntimeError(
            "whale3d.exe is already running; do not run this until the 24h soak "
            f"is finished: {existing}"
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "longrun_cards_visible.log"
    proc: subprocess.Popen | None = None
    items: list[dict[str, object]] = []
    try:
        proc = launch_3d(args.exe, log_path)
        hwnd = wait_for_window(proc.pid, 12.0)
        if not wait_log(log_path, "Sprite layer: ready", 8.0):
            raise RuntimeError("Sprite layer did not become ready")
        time.sleep(1.0)

        client_w, client_h = client_geometry(hwnd)[2:]
        baseline = capture_client(hwnd, args.out_dir / "_3d_visible_baseline.png")
        print(f"window=0x{hwnd:x} client={client_w}x{client_h} baseline={baseline.size}")

        for card_id in CARD_IDS:
            safe = card_id.replace("/", "_")
            send_card(card_id, args.ttl_ms)
            if not wait_log(log_path, f"Sprite card: {card_id}", args.timeout_s):
                raise RuntimeError(f"card not acknowledged: {card_id}")
            time.sleep(args.gap_s)

            full_path = args.out_dir / f"_3d_visible_card_{safe}.png"
            crop_path = args.out_dir / f"_3d_visible_card_{safe}_crop.png"
            image = capture_client(hwnd, full_path)
            x, y, w, h = card_rect(card_id, client_w, client_h)
            crop = image.crop((x, y, x + w, y + h))
            crop.save(crop_path)
            items.append({
                "card": card_id,
                "full": str(full_path),
                "crop": str(crop_path),
                "client_rect": {"x": x, "y": y, "w": w, "h": h},
            })
            print(f"captured {card_id}")

        sheet_path = args.out_dir / "_3d_visible_17_cards.png"
        build_contact_sheet(items, sheet_path)
        result = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "window": {"hwnd": int(hwnd), "pid": proc.pid,
                       "client_w": client_w, "client_h": client_h},
            "baseline": str(args.out_dir / "_3d_visible_baseline.png"),
            "contact_sheet": str(sheet_path),
            "cards": items,
            "status": "needs_visual_review",
        }
        result_path = args.out_dir / "2d-card-visible-qa.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(f"result={result_path}")
        print(f"contact_sheet={sheet_path}")
        return 0
    finally:
        if not args.keep_open:
            stop_process(proc)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
