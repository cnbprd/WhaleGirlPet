# -*- coding: utf-8 -*-
"""v3.0.4 内存优化实测：模拟孤儿 -> 清理 -> 起引擎 -> 空闲卸载，逐步打印内存。"""
import json
import subprocess
import sys
import time

sys.path.insert(0, r"F:\WhaleGirlPet\app")
import local_llm
import paths
import proc_guard


def ws_of(name_sub):
    out = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {name_sub}", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, encoding="oem", errors="ignore",
        creationflags=0x08000000).stdout or ""
    rows = []
    for line in out.splitlines():
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 5 and parts[0].lower().endswith(name_sub.lower()):
            try:
                mem = int(parts[4].replace(",", "").replace(" K", "").replace("K", ""))
            except ValueError:
                continue
            rows.append((int(parts[1]), round(mem / 1024, 1)))
    return rows


def total(rows):
    return round(sum(m for _, m in rows), 1)


cfg = {}
try:
    with open(paths.config_file(), "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception:
    pass
cfg["llm_backend"] = "dafeiyu_cpp"   # 强制自带引擎，才测得到 dafeiyu-server

print("== 0. 起点 ==", ws_of("dafeiyu-server.exe"))

# 1) 人为造一个"上次崩溃留下的孤儿"（Popen 起、不绑 Job）
print("== 1. 模拟孤儿进程 ==")
orphan = subprocess.Popen(
    [local_llm.server_exe(), "-m", local_llm.model_path(), "-c", "4096", "-t", "4",
     "--port", "8086", "--host", "127.0.0.1", "-rea", "off"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
time.sleep(14)
print("   加载后：", ws_of("dafeiyu-server.exe"), "合计", total(ws_of("dafeiyu-server.exe")), "MB")

n = local_llm.kill_stray_servers()
time.sleep(2)
rows = ws_of("dafeiyu-server.exe")
print(f"== 2. kill_stray_servers() 杀掉 {n} 个 -> 剩余 {rows} 合计 {total(rows)} MB ==")

# 3) 正常起引擎，并绑 Job
print("== 3. ServerManager 启动 ==")
mgr = local_llm.ServerManager(dict(cfg))
t0 = time.time()
ok = mgr.start()
print(f"   start()={ok} 用时 {time.time()-t0:.1f}s backend={mgr.backend}")
rows = ws_of("dafeiyu-server.exe")
print("   进程：", rows, "合计", total(rows), "MB")
print("   Job Object 绑定：", proc_guard.attach(mgr.proc))

# 4) 空闲卸载
mgr.last_used = time.monotonic() - 30 * 60
print("== 4. 空闲判定 ==", "idle=", round(mgr.idle_minutes(), 1),
      "should_unload(20)=", mgr.should_unload(20))
mgr.stop()
time.sleep(2)
rows = ws_of("dafeiyu-server.exe")
print("   stop() 后：", rows, "合计", total(rows), "MB")
print("== 5. Ollama（用户自己的服务，未动）==", ws_of("ollama.exe"))
print("DONE")
