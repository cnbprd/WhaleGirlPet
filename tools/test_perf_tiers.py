# -*- coding: utf-8 -*-
"""渲染档与帧间隔判定回归（v3.0.21）。

    python tools/test_perf_tiers.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import perf  # noqa: E402

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
    print("[1] 手动档透传")
    for q in ("high", "mid", "low"):
        ck(f"{q} 原样返回", perf.resolve_quality(q) == q)
    ck("大写也能认", perf.resolve_quality("LOW") == "low")

    print("[2] auto 判定")
    q = perf.resolve_quality("auto")
    ck("auto 给出合法档", q in ("high", "mid", "low"), f"本机 → {q}")
    ck("空值等同 auto", perf.resolve_quality("") in ("high", "mid", "low"))
    ck("垃圾值等同 auto", perf.resolve_quality("ultra") in ("high", "mid", "low"))
    print(f"     本机远程桌面={perf.remote_session()}，独显={perf.has_discrete_gpu()}")

    print("[3] 帧间隔")
    ck("low → 40ms(25fps)", perf.frame_ms_for("low") == 40)
    ck("high → 33ms(30fps)", perf.frame_ms_for("high") == 33)
    ck("mid → 33ms", perf.frame_ms_for("mid") == 33)
    ck("override 60ms 生效", perf.frame_ms_for("low", 60) == 60)
    ck("override 太小被夹到 16", perf.frame_ms_for("low", 5) == 16)
    ck("override 太大被夹到 120", perf.frame_ms_for("low", 999) == 120)
    ck("override 0 = 默认", perf.frame_ms_for("high", 0) == 33)

    print("[4] CPU 占用估算（实测单帧耗时 / 帧预算）")
    data = {"high": (12.5, 33), "mid": (10.6, 33), "low": (6.4, 40)}
    for k, (ms, budget) in data.items():
        print(f"     {k:<5} {ms:>5.1f}ms / {budget}ms = {ms / budget * 100:>5.1f}% 单核")

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
