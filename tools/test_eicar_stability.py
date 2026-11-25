# -*- coding: utf-8 -*-
"""EICAR 端到端稳定性统计（v3.0.21）。

用户授权真实触发 Windows Defender。目的不是"每次都自己命中"，而是：
同一条结论在多轮里必须一致 —— 要么自家规则命中，要么系统引擎先拦住/先删掉，
两者都算"检测生效"，`ok` 必须稳定为 True。

    python tools/test_eicar_stability.py --rounds 10
"""
import argparse
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import guard_core  # noqa: E402


def lock_latency(tries: int = 25, gap: float = 0.1) -> dict:
    """测：EICAR 落盘后，多久读不动（被锁或被删）。"""
    d = tempfile.mkdtemp(prefix="whale_eicar_lat_")
    p = os.path.join(d, "eicar.txt")
    res = {"first_fail_ms": None, "errno": None, "state": "readable"}
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(guard_core.EICAR_TEXT + "\n")
        t0 = time.perf_counter()
        for _ in range(tries):
            try:
                with open(p, "rb") as f:
                    f.read(8)
            except OSError as e:
                res.update(first_fail_ms=round((time.perf_counter() - t0) * 1000, 1),
                           errno=getattr(e, "errno", None),
                           state=("removed" if not os.path.exists(p) else "locked"))
                break
            if not os.path.exists(p):
                res.update(first_fail_ms=round((time.perf_counter() - t0) * 1000, 1),
                           errno=None, state="removed")
                break
            time.sleep(gap)
    finally:
        try:
            os.remove(p)
        except OSError:
            pass
        try:
            os.rmdir(d)
        except OSError:
            pass
    return res


def branch_cover() -> int:
    """两条真实分支都能用纯函数复现，不依赖 Defender 这一轮到底锁不锁。"""
    cases = [
        ("自家命中", True, [{"rule": "AV-EICAR"}], "", [], True),
        ("系统锁住内容", True, [], "system", [], True),
        ("系统直接删除", True, [], "system-removed", [], True),
        ("其它错误不算通过", True, [], "err13", [], False),
        ("无害对照被咬=失败", True, [{"rule": "AV-EICAR"}], "", [{"rule": "X"}], False),
        ("规则层没命中=失败", False, [{"rule": "AV-EICAR"}], "", [], False),
    ]
    fail = 0
    for name, rm, hits, blocked, clean, want in cases:
        got = guard_core.eicar_verdict(rm, hits, blocked, clean)["ok"]
        if got != want:
            fail += 1
            print(f"  FAIL {name}: 期望 {want} 得到 {got}")
        else:
            print(f"  ok   {name}")
    return fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--gap", type=float, default=0.5, help="每轮间隔秒，让 Defender 状态复位")
    a = ap.parse_args()

    rows = []
    print("判定分支覆盖（不依赖系统是否出手）")
    bad_branch = branch_cover()
    print(f"分支覆盖：{6 - bad_branch}/6\n")
    print(f"EICAR 稳定性：{a.rounds} 轮（授权真实触发 Defender）")
    print("  #   ok   自家命中  系统拦截        耗时ms")
    for i in range(1, a.rounds + 1):
        r = guard_core.eicar_selftest()
        mode = ("self" if r["eicar_hits"] else (r["blocked"] or "none"))
        rows.append((r["ok"], mode, r["ms"], r["clean_hits"]))
        print(f"  {i:<3} {str(r['ok']):<5} {r['eicar_hits']:<9} {mode:<15} {r['ms']}")
        if i < a.rounds:
            time.sleep(a.gap)

    ok_n = sum(1 for x in rows if x[0])
    self_n = sum(1 for x in rows if x[1] == "self")
    sys_n = sum(1 for x in rows if str(x[1]).startswith("system"))
    bad = [x for x in rows if not x[0]]
    ms = sorted(x[2] for x in rows)
    print("\n汇总")
    print(f"  ok {ok_n}/{len(rows)} · 自家命中 {self_n} 次 · 系统拦截 {sys_n} 次")
    print(f"  耗时 p50 {ms[len(ms)//2]}ms / max {ms[-1]}ms")
    print(f"  误报（无害对照被咬）{sum(x[3] for x in rows)} 次")
    if bad:
        print(f"  不稳定 {len(bad)} 轮：{bad}")
    lat = lock_latency()
    print(f"  落盘→读不动：{lat['state']} @ {lat['first_fail_ms']}ms（errno={lat['errno']}）")
    stable = (ok_n == len(rows)) and sys_n + self_n == len(rows) and sum(x[3] for x in rows) == 0
    print(f"\n结论：{'稳定' if stable and not bad_branch else '不稳定'}")
    return 0 if (stable and not bad_branch) else 1


if __name__ == "__main__":
    sys.exit(main())
