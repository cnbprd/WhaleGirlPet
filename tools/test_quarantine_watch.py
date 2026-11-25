# -*- coding: utf-8 -*-
"""隔离区 + 实时监控回归（v3.0.21）。

    python tools/test_quarantine_watch.py
"""
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import quarantine as q  # noqa: E402
import realtime  # noqa: E402

P = F = 0


def ck(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print(f"  ok   {name} {extra}")
    else:
        F += 1
        print(f"  FAIL {name} {extra}")


def main():
    tmp = tempfile.mkdtemp(prefix="whale_q_")
    data = os.path.join(tmp, "data")
    os.makedirs(data, exist_ok=True)

    import paths
    orig_data = paths.data_dir
    try:
        paths.data_dir = lambda: data
        import guard_core
        orig_root = guard_core._data_root
        guard_core._data_root = lambda: data

        print("[1] 隔离：移走 + 留下可恢复副本")
        bad = os.path.join(tmp, "evil.exe")
        with open(bad, "wb") as f:
            f.write(b"MZ" + b"\x00" * 100 + b"EVIL")
        sha = guard_core.sha256_of(bad)
        r = q.quarantine_file(bad, [{"rule": "T-1", "title": "测试命中"}], reason="自测")
        ck("隔离成功", r["ok"], str(r))
        ck("原文件已移走", not os.path.exists(bad))
        ck("副本存在", os.path.isfile(r["item"]))
        ck("副本哈希与原文件一致", guard_core.sha256_of(r["item"]) == sha)
        import json
        meta = json.load(open(r["item"] + ".json", encoding="utf-8"))
        ck("元信息写了原路径", meta.get("origin") == os.path.abspath(bad), meta.get("origin"))
        ck("文件名被净化（保留原名）", "evil.exe" in os.path.basename(r["item"]),
           os.path.basename(r["item"]))

        print("[2] 列表")
        items = q.list_items()
        ck("列表里有它", any(i["item"] == r["item"] for i in items), f"{len(items)} 条")
        ck("列表带原路径", any(tmp in (i.get("origin") or "") for i in items))

        print("[3] 拒绝目录与链接")
        d = os.path.join(tmp, "adir")
        os.makedirs(d, exist_ok=True)
        ck("目录不收", q.quarantine_file(d)["ok"] is False)
        link = os.path.join(tmp, "link.exe")
        try:
            os.symlink(bad, link)
            ck("符号链接不收", q.quarantine_file(link)["ok"] is False)
            os.remove(link)
        except OSError:
            print("     （本机无权限建符号链接，跳过）")

        print("[4] 恢复")
        before = tmp
        r2 = q.restore(r["item"])
        ck("恢复成功", r2["ok"], str(r2))
        ck("回到原路径", r2.get("path") == bad and os.path.isfile(bad))
        ck("副本已清", not os.path.exists(r["item"]))

        print("[5] 原位置被占用时改名不覆盖")
        r3 = q.quarantine_file(bad)
        ck("再次隔离", r3["ok"])
        with open(bad, "wb") as f:  # 原位置重新放一个同名文件
            f.write(b"new occupant")
        r4 = q.restore(r3["item"])
        ck("改名恢复", r4["ok"] and r4["path"].endswith(".restored.exe"), str(r4))
        ck("占位文件未被覆盖", open(bad, "rb").read() == b"new occupant")

        print("[6] 彻底删除")
        victim = os.path.join(tmp, "gone.exe")
        with open(victim, "wb") as f:
            f.write(b"MZ gone")
        r5 = q.quarantine_file(victim)
        ck("删除隔离副本", q.delete_item(r5["item"])["ok"])
        ck("副本确实没了", not os.path.exists(r5["item"]))

        print("[7] 实时监控")
        wd = os.path.join(tmp, "watch")
        os.makedirs(wd, exist_ok=True)
        got = []
        w = realtime.DirWatcher(dirs=[wd], on_new=lambda p: got.append(p), interval=0.5)
        w.prime()
        f1 = os.path.join(wd, "a.exe")
        with open(f1, "wb") as f:
            f.write(b"MZ")
        f2 = os.path.join(wd, "b.txt")   # 非可执行后缀，不该报
        with open(f2, "wb") as f:
            f.write(b"hi")
        new = w.poll_once()
        ck("新 exe 被发现", f1 in new, str(new))
        ck("txt 不报", f2 not in new)
        ck("回调收到", f1 in got)
        with open(f1, "ab") as f:  # 内容变化 → mtime/size 变
            f.write(b"more")
        time.sleep(0.02)
        new2 = w.poll_once()
        ck("改动被复查", f1 in new2, str(new2))
        ck("已存在文件不重复报", w.poll_once() == [])
        w.stop()
        t0 = time.perf_counter()
        w2 = realtime.DirWatcher(dirs=[wd])
        w2.snapshot()
        ck("单次快照 < 50ms", (time.perf_counter() - t0) * 1000 < 50,
           f"{(time.perf_counter() - t0) * 1000:.1f} ms")
        ck("目录不存在也不崩", realtime.DirWatcher(dirs=[os.path.join(tmp, "nope")]).prime() == 0)
    finally:
        paths.data_dir = orig_data
        guard_core._data_root = orig_root
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
