# -*- coding: utf-8 -*-
"""v3.0.17：实测打包 exe 的冷启动耗时与常驻内存。

指标定义（不用 GUI 探测，避免误差来源太多）：
  1) 进程首现：onefile 的引导进程被创建的时刻
  2) 解包完成：引导进程 fork 出真正的主进程（子进程）的时刻 —— onefile 的最大启动成本在这
  3) 就绪温度：第一个子进程 RSS 到 100MB 以上（Qt 起来、窗口绘制中）
  4) 常驻 RSS：启动后第 25 秒两个进程 RSS 之和

用法：python tools/measure_boot.py [exe路径] [观察秒数]
"""
import os
import subprocess
import sys
import time

import psutil

EXE = sys.argv[1] if len(sys.argv) > 1 else r"F:\WhaleGirlPetApp\WhaleGirlPet.exe"
WATCH = float(sys.argv[2]) if len(sys.argv) > 2 else 25.0


def pids_of(exe):
    out = []
    for p in psutil.process_iter(["name", "exe"]):
        try:
            if os.path.basename(p.info["exe"] or "").lower() == os.path.basename(exe).lower():
                out.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return out


def rss_mb(procs):
    tot = 0
    for p in procs:
        try:
            tot += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return tot / 1048576


def children(procs):
    out = []
    for p in procs:
        try:
            out.extend(p.children(recursive=True))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return out


def main():
    # 先清干净，保证是冷启动
    for p in pids_of(EXE):
        try:
            p.kill()
        except Exception:
            pass
    time.sleep(0.6)

    t0 = time.perf_counter()
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    first_pid_s = None
    child_at = None
    ready_at = None
    samples = []
    last = 0.0
    while True:
        el = time.perf_counter() - t0
        if el - last >= 1.0:
            last = el
            procs = pids_of(EXE)
            ch = children(procs)
            tot = rss_mb(procs) + rss_mb(ch)
            samples.append((round(el, 1), len(procs), len(ch), round(tot)))
            if first_pid_s is None and procs:
                first_pid_s = el
            if child_at is None and ch:
                child_at = el
            if ready_at is None and tot >= 150:
                ready_at = el   # 合计 150MB = Qt 已加载、窗口正在绘制
        if el > WATCH:
            break
        time.sleep(0.15)

    procs = pids_of(EXE)
    ch = children(procs)
    total = rss_mb(procs) + rss_mb(ch)
    boot = psutil.Process(proc.pid)

    print(f"exe            {EXE}")
    print(f"exe 文件大小    {os.path.getsize(EXE)/1048576:.1f} MB")
    print(f"引导进程首现    {first_pid_s if first_pid_s is not None else -1:.2f} s")
    print(f"解包+主进程起   {child_at if child_at is not None else -1:.2f} s")
    print(f"RSS>=100MB     {ready_at if ready_at is not None else -1:.2f} s")
    print(f"{WATCH:.0f}s 常驻 RSS   {total:.0f} MB  ({len(procs)}+{len(ch)} 进程)")
    print("采样(秒,顶层进程,子进程,合计MB):")
    for s in samples[::3]:
        print("  ", s)

    # 收尾：杀掉，别把桌宠留在用户桌面上
    for p in procs + ch:
        try:
            p.kill()
        except Exception:
            pass
    try:
        boot.wait(timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    main()
