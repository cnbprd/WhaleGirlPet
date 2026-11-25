# -*- coding: utf-8 -*-
"""流畅度基准：骨骼渲染 / 时间轴 / 混合，多场景多轮取 p50、p95。

    python tools/perf_bench.py            # 默认 3 轮
    python tools/perf_bench.py --rounds 5
"""
import argparse
import os
import statistics
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import anim_engine as am  # noqa: E402
import skeletal as sk  # noqa: E402

SKIN = os.path.join(ROOT, "assets", "skins", "default.png")


def pct(vals, q):
    if not vals:
        return 0.0
    vals = sorted(vals)
    i = min(len(vals) - 1, int(round(q * (len(vals) - 1))))
    return vals[i]


def run_rounds(fn, rounds, n):
    allv, per = [], []
    for _ in range(rounds):
        vals = fn(n)
        allv += vals
        per.append(sum(vals) / len(vals))
    return {"p50": pct(allv, 0.5), "p95": pct(allv, 0.95),
            "mean": sum(allv) / len(allv), "rounds": [round(x, 2) for x in per]}


def bench_render(sprite, clip_name, rounds, n=40):
    clip = sk.CLIPS.get(clip_name)

    def one(k):
        vals = []
        for i in range(k):
            t = (i / max(k, 1)) * (clip.duration if clip else 0.8)
            pose = clip.pose(t) if clip else {}
            t0 = time.perf_counter()
            sprite.render(pose)
            vals.append((time.perf_counter() - t0) * 1000)
        return vals

    return run_rounds(one, rounds, n)


def bench_timeline(rounds, n=2000):
    def one(k):
        tl = am.Timeline()
        tl.play("crab")
        tl.play("trot", mix=0.15)
        vals = []
        for i in range(k):
            t0 = time.perf_counter()
            if not tl.is_mixing():
                tl.play("crab" if i % 2 else "trot", mix=0.15)
            tl.step(1 / 60)
            tl.pose_now()
            vals.append((time.perf_counter() - t0) * 1e6)
        return vals

    return run_rounds(one, rounds, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--quality", default="high", choices=["high", "mid", "low"])
    a = ap.parse_args()
    sprite = sk.SkeletalSprite(QPixmap(SKIN), a.quality)
    print(f"[{a.quality}] 立绘 {sprite.W}x{sprite.H}，网格 {sprite.skin.gx}x{sprite.skin.gy}，"
          f"三角形 {sprite.skin.gx * sprite.skin.gy * 2}，{a.rounds} 轮")
    print(f"{'场景':<10}{'p50(ms)':>9}{'p95(ms)':>9}{'mean':>8}   每轮均值")
    for name in ("idle", "walk", "run", "tumble"):
        r = bench_render(sprite, name, a.rounds)
        print(f"{name:<10}{r['p50']:>9.2f}{r['p95']:>9.2f}{r['mean']:>8.2f}   {r['rounds']}")
    r = bench_timeline(a.rounds)
    print(f"{'timeline':<10}{r['p50'] / 1000:>9.3f}{r['p95'] / 1000:>9.3f}"
          f"{r['mean'] / 1000:>8.3f}   {[round(x / 1000, 3) for x in r['rounds']]} (µs→ms)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
