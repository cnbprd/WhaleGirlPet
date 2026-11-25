# -*- coding: utf-8 -*-
"""三层记忆单测：衰减不叠加、过冷归档、重复压缩、core 预算、议程提取。"""
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from memory import MemoryStore  # noqa: E402
from memory_tiers import MemoryTiers  # noqa: E402

tmp = tempfile.mkdtemp(prefix="whale_mem_")
db_path = os.path.join(tmp, "memory.db")
store = MemoryStore(db_path)
tiers = MemoryTiers(store)

now = time.time()
bad = 0


def check(name, got, want):
    global bad
    ok = got == want
    print(("[ok]  " if ok else "[BAD] ") + f"{name}: {got}" + ("" if ok else f"  (want {want})"))
    if not ok:
        bad += 1


def add(key, value, weight, days_old):
    store.db.execute("INSERT INTO facts(key,value,weight,ts) VALUES(?,?,?,?)",
                     (key, value, weight, now - days_old * 86400))
    store.db.commit()


add("作息", "凌晨两点睡", 1.0, 200)      # 老、权重不高 → 应归档
add("喜好", "爱喝冰美式", 1.0, 10)        # 新 → 只降权
add("明天", "明天要交房租", 1.0, 5)       # 议程候选
add("习惯", "每天早上喝咖啡", 1.0, 3)     # 与下一条重复 → 压缩
add("日常", "每天早上喝咖啡", 1.2, 2)

# 1) 首次调用（没设过 last_decay）应跳过，避免刚开机就把记忆扣光
r0 = tiers.tick_decay()
check("首次调用跳过", r0.get("skipped"), True)

# 2) 把"上次衰减"设到 200 天前，等价于很久没开机
tiers.db.execute("INSERT INTO meta(k,v) VALUES('last_decay',?) "
                 "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (repr(now - 200 * 86400),))
tiers.db.commit()
r1 = tiers.tick_decay()
print("  衰减结果:", r1)
check("归档了 1 条", r1["archived"], 1)
check("归档表里有它", [a["key"] for a in tiers.archival()], ["作息"])

# 3) 立刻再调一次：增量应为 0，不叠加
r2 = tiers.tick_decay()
check("紧接着再调不重复扣", r2.get("skipped"), True)

# 4) 压缩重复事实
before = int(tiers.db.execute("SELECT COUNT(*) FROM facts").fetchone()[0])
merged = tiers.compress()
after = int(tiers.db.execute("SELECT COUNT(*) FROM facts").fetchone()[0])
check("合并条数 >0", merged > 0, True)
check("facts 少了一条", before - after, merged)
row = tiers.db.execute("SELECT value,weight FROM facts WHERE key='习惯' OR key='日常'").fetchone()
print("  合并后:", row)

# 5) core 预算与结构
core = tiers.core(budget=520)
check("core 不超过预算", len(core) <= 520, True)
check("core 带记忆标题", core.startswith("【她记着的】"), True)
print("  core 长度:", len(core))

# 6) 议程
ag = tiers.agenda()
check("议程非空", len(ag) > 0, True)
print("  议程:", ag)

# 7) 统计
print("  统计:", tiers.stats())
print("\n%d 项失败" % bad)
sys.exit(1 if bad else 0)
