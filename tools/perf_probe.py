# -*- coding: utf-8 -*-
"""启动路径与热路径耗时探针：先量，再决定优化哪里。

不含 GUI 构造（那部分离屏测不准），只量真正在启动时跑的东西。
"""
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

CFG = {"llm_ctx": 4096}


def timed(name, fn):
    t0 = time.perf_counter()
    try:
        r = fn()
        err = ""
    except Exception as e:  # noqa: BLE001
        r, err = None, f"{type(e).__name__}: {e}"
    dt = (time.perf_counter() - t0) * 1000
    print(f"{name:<34} {dt:8.1f} ms  {err}")
    return dt, r


print("=== 导入阶段 ===")
timed("import local_llm", lambda: __import__("local_llm"))
import local_llm  # noqa: E402
timed("import memory + memory_tiers", lambda: (__import__("memory"), __import__("memory_tiers")))
import memory  # noqa: E402
import memory_tiers  # noqa: E402

print("\n=== 启动热路径 ===")
_, models = timed("scan_models（扫所有目录+GGUF 魔数）", lambda: local_llm.scan_models(CFG))
print("   扫到模型:", len(models or []))


class Store:
    def __init__(self, path):
        self.memory = memory.MemoryStore(path)


def build_tiers():
    d = tempfile.mkdtemp(prefix="probe_")
    s = memory.MemoryStore(os.path.join(d, "m.db"))
    return memory_tiers.MemoryTiers(s)


_, tiers = timed("MemoryTiers 建表 + 首次衰减/压缩", build_tiers)

# 造 2000 条对话，模拟重度用户的检索开销
s = tiers.store
t0 = time.perf_counter()
for i in range(2000):
    s.add_message("user" if i % 2 else "assistant", f"第{i}条：今天天气怎么样，我想出去走走看看海边的鲸鱼")
s.db.commit()
print(f"{'写入 2000 条消息':<34} {(time.perf_counter()-t0)*1000:8.1f} ms")

q = "海边鲸鱼天气"
_, _ = timed("search 2000 条里检索", lambda: s.search(q, 4))
_, _ = timed("context_block（含检索）", lambda: s.context_block(q, n_recent=4, n_facts=0))
_, _ = timed("core(420)", lambda: tiers.core(budget=420))
_, _ = timed("agenda()", lambda: tiers.agenda())

# 事实多时 compress 的 O(n²)
for i in range(60):
    s.add_fact(f"标签{i}", f"鱼片说过第{i}种喜欢的东西是海苔饭团{i}")
s.db.commit()
_, n = timed("compress 60 条事实（O(n²)）", lambda: tiers.compress())
print("   合并:", n)

print("\n=== 结果摘要 ===")
print("模型候选数:", len(models or []))
