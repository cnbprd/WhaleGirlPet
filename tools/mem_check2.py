# -*- coding: utf-8 -*-
"""v3.0.4 内存实测（psutil 版）：引擎加载前/后/卸载后 + 桌宠主进程。"""
import json
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm
import paths

import psutil


def engine_rss():
    tot = 0.0
    pids = []
    for p in psutil.process_iter(["name", "memory_info"]):
        if (p.info["name"] or "").lower() == "dafeiyu-server.exe":
            tot += p.info["memory_info"].rss / 1048576
            pids.append(p.pid)
    return round(tot, 1), pids


cfg = {}
try:
    with open(paths.config_file(), "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    pass
cfg["llm_backend"] = "dafeiyu_cpp"

print("起点引擎内存(MB)：", engine_rss())
mgr = local_llm.ServerManager(dict(cfg))
t0 = time.time()
ok = mgr.start()
time.sleep(3)
print(f"start()={ok} {time.time()-t0:.1f}s -> 引擎 {engine_rss()}")
mgr.last_used = time.monotonic() - 30 * 60
print("should_unload(20)=", mgr.should_unload(20), " idle=", round(mgr.idle_minutes(), 1))
mgr.stop()
time.sleep(3)
print("stop() 后引擎：", engine_rss())
print("当前进程(测试脚本)RSS_MB：", round(psutil.Process().memory_info().rss / 1048576, 1))
print("DONE")
