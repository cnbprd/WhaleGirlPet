# -*- coding: utf-8 -*-
"""验证 Job Object：起引擎、绑 Job，然后父进程硬退出（os._exit，不走清理流程）。
如果子进程随后消失，说明"父死子死"生效，不会再留 2.3GB 孤儿。"""
import os
import subprocess
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm
import proc_guard

args = [local_llm.server_exe(), "-m", local_llm.model_path(), "-c", "4096", "-t", "4",
        "--port", "8086", "--host", "127.0.0.1", "-rea", "off"]
proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=0x08000000)
print("CHILD_PID", proc.pid, flush=True)
print("JOB_ATTACH", proc_guard.attach(proc), flush=True)
time.sleep(16)
print("HARD_EXIT_NOW", flush=True)
os._exit(1)   # 模拟崩溃 / 任务管理器强杀，跳过 atexit 与 stop()
