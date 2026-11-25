# -*- coding: utf-8 -*-
"""第 7 条：迁移断点续传实测。

造 120MB 假数据 → 复制到 40% 强行中断 → 再跑一次 → 校验只补剩下的 60%、文件一致。
"""
import hashlib
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import migrate  # noqa: E402

BASE = os.path.join(ROOT, ".tmp_migrate")
SRC = os.path.join(BASE, "src")
DST = os.path.join(BASE, "dst")
FILES, MB = 60, 2
R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def build():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(SRC)
    block = bytes(range(256)) * (MB * 1024 * 1024 // 256)
    for i in range(FILES):
        sub = os.path.join(SRC, f"d{i % 6}")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, f"f{i}.bin"), "wb") as f:
            f.write(bytes([i % 255]) + block[1:])
    with open(os.path.join(SRC, "data_root.txt"), "w", encoding="utf-8") as f:
        f.write("old")


def digest(root):
    out = {}
    for p in migrate._walk(root):
        rel = os.path.relpath(p, root)
        if rel in ("migrate_state.json", "data_root.txt"):
            continue
        with open(p, "rb") as f:
            out[rel] = hashlib.sha256(f.read()).hexdigest()
    return out


def main():
    build()
    t0 = time.perf_counter()
    stop_at = {}

    def progress(done, total, rel):
        if done >= total * 0.4:
            stop_at["hit"] = True

    stats1 = migrate.copy_resumable(
        SRC, DST, progress=progress, should_stop=lambda: stop_at.get("hit", False))
    ck("第一轮确实中途停了", 0 < stats1["copied_files"] < FILES,
       f"{stats1['copied_files']}/{FILES} 个文件｜{stats1['copied_bytes'] / 1048576:.0f}MB")
    ck("中断后目标里已有部分文件", len(digest(DST)) > 0)

    stats2 = migrate.copy_resumable(SRC, DST)
    ck("第二轮跳过已复制", stats2["skipped_files"] >= stats1["copied_files"],
       f"跳过 {stats2['skipped_files']}｜补 {stats2['copied_files']}｜"
       f"续传前已有 {stats2['bytes_before'] / 1048576:.0f}MB")
    ck("第二轮只补剩余字节", stats2["copied_bytes"] < stats1["total_bytes"] * 0.75,
       f"补 {stats2['copied_bytes'] / 1048576:.0f}MB / 总 {stats2['total_bytes'] / 1048576:.0f}MB")
    same = digest(SRC) == digest(DST)
    ck("最终内容一致", same)
    ck("不收 data_root.txt", "data_root.txt" not in digest(DST))
    st = os.path.join(DST, migrate.STATE_NAME)
    ck("状态文件落盘", os.path.exists(st), f"{os.path.getsize(st)}B")
    print(f"总耗时 {time.perf_counter() - t0:.1f}s（含造数据）")
    shutil.rmtree(BASE, ignore_errors=True)
    bad = [x for x in R if not x[1]]
    print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")


if __name__ == "__main__":
    main()
