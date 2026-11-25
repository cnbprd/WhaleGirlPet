# -*- coding: utf-8 -*-
"""v3.0.4 引擎内存参数扫描：比较 slots / KV 量化对 RSS 的影响。"""
import json
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm

import psutil

MODEL = local_llm.model_path()
EXE = local_llm.server_exe()


def rss(pid):
    try:
        return round(psutil.Process(pid).memory_info().rss / 1048576, 1)
    except Exception:
        return 0.0


def run(tag, extra):
    args = [EXE, "-m", MODEL, "-c", "4096", "-t", "4", "--port", "8087",
            "--host", "127.0.0.1", "-rea", "off"] + extra
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x08000000)
    ok = False
    t0 = time.time()
    for _ in range(120):
        if p.poll() is not None:
            break
        try:
            with urllib.request.urlopen("http://127.0.0.1:8087/health", timeout=2) as r:
                if b"ok" in r.read():
                    ok = True
                    break
        except Exception:
            time.sleep(0.5)
    peak = rss(p.pid)
    try:
        p.terminate()
        p.wait(timeout=8)
    except Exception:
        p.kill()
    print(f"{tag:34s} ok={ok} {time.time()-t0:5.1f}s RSS={peak} MB", flush=True)


run("A 现状(auto slots, f16 KV)", [])
run("B -np 1", ["-np", "1"])
run("C -np 1 + q8_0 KV", ["-np", "1", "-ctk", "q8_0", "-ctv", "q8_0"])
run("D -np 1 + q8_0 KV + -c 2048", ["-np", "1", "-ctk", "q8_0", "-ctv", "q8_0", "-c", "2048"])
print("DONE")
