# -*- coding: utf-8 -*-
"""探测本机硬件（显卡显存 / 内存 / 核心数），并据此给模型推荐。

只读查询，不装驱动、不改设置。nvidia-smi 不在时退回无需驱动的方式。
"""
import ctypes
import os
import shutil
import subprocess


def _nvidia() -> tuple:
    exe = shutil.which("nvidia-smi") or r"C:\Windows\System32\nvidia-smi.exe"
    try:
        out = subprocess.run(
            [exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, check=False)
        line = (out.stdout or "").strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        return parts[0], round(float(parts[1]) / 1024.0, 1), parts[2]
    except Exception:  # noqa: BLE001
        return "", 0.0, ""


def _ram_gb() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64)]

    try:
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        return round(st.ullTotalPhys / (1024 ** 3), 1)
    except Exception:  # noqa: BLE001
        return 0.0


def snapshot() -> dict:
    gpu, vram, driver = _nvidia()
    return {
        "gpu": gpu,
        "vram_gb": vram,
        "driver": driver,
        "ram_gb": _ram_gb(),
        "threads": os.cpu_count() or 4,
    }


def summary() -> str:
    h = snapshot()
    gpu = f"{h['gpu']}（{h['vram_gb']}GB 显存，驱动 {h['driver']}）" if h["gpu"] else "未检测到 NVIDIA 显卡"
    return f"显卡：{gpu}｜内存：{h['ram_gb']}GB｜CPU 线程：{h['threads']}"


def recommend(catalog: list) -> tuple:
    """返回 (建议的 catalog 项, 一句理由)。按显存与内存挑，宁小勿爆。"""
    h = snapshot()
    vram, ram = h["vram_gb"], h["ram_gb"]
    usable = [m for m in catalog if m.get("fits")]
    if not usable:
        return None, "清单里没有可本地跑的模型"

    by_mb = sorted(usable, key=lambda m: m["size_mb"])

    def pick(limit_mb):
        ok = [m for m in by_mb if m["size_mb"] <= limit_mb]
        return ok[-1] if ok else by_mb[0]

    # 显存装不下时靠内存：按 60% 可用内存估
    if vram >= 8:
        target, why = pick(8000), f"{vram}GB 显存足够，选大的更聪明"
    elif vram >= 6:
        target, why = pick(5200), f"{vram}GB 显存：建议 Q4 量化的 4B–7B，留出上下文余量"
    elif vram >= 4:
        target, why = pick(3200), f"{vram}GB 显存：4B Q4 刚好，别上 7B"
    elif ram >= 12:
        target, why = pick(3200), f"没显卡大显存，靠 {ram}GB 内存跑 4B（比 7B 快一倍）"
    else:
        target, why = pick(1400), f"显存 {vram}GB、内存 {ram}GB，先跑 1.5B 最稳"
    return target, why
