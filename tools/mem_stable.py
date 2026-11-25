# -*- coding: utf-8 -*-
"""观察引擎 RSS 随时间的走势：加载完成瞬间 vs 静置 30/60/120 秒后。"""
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm

import psutil

MODEL = local_llm.model_path()
EXE = local_llm.server_exe()
p = subprocess.Popen([EXE, "-m", MODEL, "-c", "4096", "-t", "4", "--port", "8087",
                      "--host", "127.0.0.1", "-rea", "off", "-np", "1"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=0x08000000)
t0 = time.time()
for _ in range(120):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8087/health", timeout=2) as r:
            if b"ok" in r.read():
                break
    except Exception:
        time.sleep(0.5)


def snap(tag):
    pr = psutil.Process(p.pid)
    mi = pr.memory_full_info()
    print(f"{tag}: RSS={mi.rss/1048576:.0f}MB private={getattr(mi,'private',0)/1048576:.0f}MB "
          f"t={time.time()-t0:.0f}s", flush=True)


snap("加载完成")
time.sleep(30)
snap("静置30s")
time.sleep(30)
snap("静置60s")
time.sleep(60)
snap("静置120s")
p.terminate()
p.wait(timeout=8)
print("DONE")
