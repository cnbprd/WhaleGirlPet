# -*- coding: utf-8 -*-
"""列出引擎进程里所有 >20MB 的虚拟内存段（不筛 Type），并尽量对上文件名。"""
import ctypes
import os
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)


class MBI64(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("align1", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t), ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD), ("Type", wintypes.DWORD),
                ("align2", wintypes.DWORD)]


class PMC_EX(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.c_void_p, ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
GMF = getattr(k32, "K32GetMappedFileNameW", None) or psapi.GetMappedFileNameW
GMF.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_wchar_p, wintypes.DWORD]
GMF.restype = wintypes.DWORD

MODEL = local_llm.model_path()
p = subprocess.Popen([local_llm.server_exe(), "-m", MODEL, "-c", "4096", "-t", "4",
                      "--port", "8087", "--host", "127.0.0.1", "-rea", "off", "-np", "1"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=0x08000000)
for _ in range(140):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8087/health", timeout=2) as r:
            if b"ok" in r.read():
                break
    except Exception:
        time.sleep(0.5)

h = k32.OpenProcess(0x0400 | 0x0010, False, p.pid)
c = PMC_EX()
c.cb = ctypes.sizeof(c)
psapi.GetProcessMemoryInfo(ctypes.c_void_p(h), ctypes.byref(c), c.cb)
print(f"WS={c.WorkingSetSize/1048576:.0f}MB  PagefileUsage={c.PagefileUsage/1048576:.0f}MB")

TYPE_NAME = {1: "MEM_PRIVATE", 2: "MEM_MAPPED", 131072: "MEM_IMAGE"}
STATE = {4096: "COMMIT", 65536: "FREE", 8192: "RESERVE"}

addr = 0
big = []
regions = 0
fails = 0
while addr < 0x7FFFFFFFFFFE:
    mbi = MBI64()
    r = k32.VirtualQueryEx(ctypes.c_void_p(h), ctypes.c_void_p(addr),
                          ctypes.byref(mbi), ctypes.c_size_t(ctypes.sizeof(mbi)))
    if not r:
        fails += 1
        if fails > 200:
            break
        addr = (addr + 0x100000) & ~0xFFF
        continue
    fails = 0
    base = int(mbi.BaseAddress or 0)
    size = int(mbi.RegionSize or 0)
    regions += 1
    if size >= 20 * 1048576:
        buf = ctypes.create_unicode_buffer(600)
        ok = GMF(ctypes.c_void_p(h), ctypes.c_void_p(base), buf, 600)
        name = os.path.basename(buf.value.replace("\\", "/")) if ok else ""
        big.append((size, TYPE_NAME.get(mbi.Type, str(mbi.Type)),
                    STATE.get(mbi.State, str(mbi.State)), name))
    addr = base + size

print(f"\n共 {regions} 个区域，>20MB 的 {len(big)} 个：")
for size, tp, st, name in sorted(big, key=lambda x: -x[0]):
    print(f"   {size/1048576:8.1f}MB  {tp:12s} {st:8s} {name}")

p.terminate()
p.wait(timeout=8)
print("DONE")
