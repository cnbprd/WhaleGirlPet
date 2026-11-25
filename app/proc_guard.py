# -*- coding: utf-8 -*-
"""让 dafeiyu-server 子进程跟着父进程一起死（Windows Job Object）。

背景（v3.0.4 实测）：桌宠被任务管理器强杀、或者崩溃退出时，子进程没人收尸，
实测留下一个 2.39GB 的 dafeiyu-server 一直常驻，直到重启电脑才消失。
这里用一个带 KILL_ON_JOB_CLOSE 的 Job Object 把它绑死：父进程句柄一关，
系统自动连子进程一起杀。
"""
import ctypes
import os

_JOB = None
_JOB_KILL_ON_CLOSE = 0x00002000
_JOB_EXTENDED_INFO = 9


class _IoCounters(ctypes.Structure):
    _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong)]


class _BasicLimit(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimit),
                ("IoInfo", _IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def attach(proc) -> bool:
    """把子进程绑进"父进程死则子进程死"的 Job 里。失败返回 False（不影响正常跑）。"""
    global _JOB
    if os.name != "nt" or proc is None:
        return False
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        if _JOB is None:
            h = k32.CreateJobObjectW(None, None)
            if not h:
                return False
            info = _ExtendedLimit()
            info.BasicLimitInformation.LimitFlags = _JOB_KILL_ON_CLOSE
            k32.SetInformationJobObject(ctypes.c_void_p(h), _JOB_EXTENDED_INFO,
                                       ctypes.byref(info), ctypes.sizeof(info))
            _JOB = h
        handle = int(getattr(proc, "_handle", 0) or 0)
        if not handle:
            return False
        return bool(k32.AssignProcessToJobObject(ctypes.c_void_p(_JOB),
                                                 ctypes.c_void_p(handle)))
    except Exception:  # noqa: BLE001
        return False
