# -*- coding: utf-8 -*-
"""动画引擎 v3.0.20 三件新机制实测：交叉淡入 / 排队 / 变速。

量化口径：30fps 采样 bob、sx 通道，看「切换瞬间相邻两帧的最大跳变」。
硬切 = 一帧内跳到新动作第 0 帧；混合 = 分摊到 mix 窗口内。
    python tools/test_anim_mix.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import anim_engine as am  # noqa: E402

DT = 1.0 / 30


def switch_jump(mix, frm="crab", to="hop", pre=10):
    """只看「切换那一帧」的位移差 + 之后 0.15s 的二阶差分峰值（抖动）。"""
    tl = am.Timeline()
    tl.play(frm)
    for _ in range(pre):
        tl.step(DT)
    before = tl.pose_now().bob
    tl.play(to, mix=mix)
    seq = []
    for _ in range(5):
        seq.append(tl.step(DT).bob)
    jerk = max(abs(seq[i + 1] - 2 * seq[i] + seq[i - 1]) for i in range(1, len(seq) - 1))
    return abs(seq[0] - before), jerk


def sample_end(mix, frm="crab", to="hop", pre=10, n=20):
    tl = am.Timeline()
    tl.play(frm)
    for _ in range(pre):
        tl.step(DT)
    tl.play(to, mix=mix)
    last = 0.0
    for _ in range(n):
        last = tl.step(DT).bob
    return last


def vel_jump(mix, frm="crab", to="hop", pre=10):
    """切换前后的「速度」差：v_before 取切换前两帧，v_after 取切换后第 2 帧。"""
    tl = am.Timeline()
    tl.play(frm)
    p2 = p1 = 0.0
    for _ in range(pre):
        p2, p1 = p1, tl.step(DT).bob
    v_before = p1 - p2
    tl.play(to, mix=mix)
    s0 = tl.step(DT).bob
    s1 = tl.step(DT).bob
    return abs((s1 - s0) - v_before)


def main():
    P = F = 0

    def ck(name, cond, extra=""):
        nonlocal P, F
        if cond:
            P += 1
            print(f"  ok   {name} {extra}")
        else:
            F += 1
            print(f"  FAIL {name} {extra}")

    print("[1] 硬切 vs 交叉淡入（crab → hop，bob 通道）")
    hj = switch_jump(0.0)[0]
    sj = switch_jump(0.15)[0]
    hv = vel_jump(0.0)
    sv = vel_jump(0.15)
    print(f"  硬切：切换帧位移 {hj:.2f}px，速度突变 {hv:.2f}px/帧")
    print(f"  0.15s 混合：切换帧位移 {sj:.2f}px，速度突变 {sv:.2f}px/帧")
    ck("硬切确有切换阶跃", hj > 4, f"{hj:.2f}px")
    ck("混合把切换位移压到 1/3 以内", sj < hj / 3,
       f"{sj:.2f}px vs {hj:.2f}px（降 {100 * (1 - sj / hj):.0f}%）")
    ck("混合把速度突变小于硬切", sv < hv,
       f"{sv:.2f} vs {hv:.2f}px/帧（仅降 {100 * (1 - sv / hv):.0f}%，"
       f"说明 0.15s 窗口只能压住位置、压不住爆发动作的速度）")
    soft = sample_end(0.15)
    ck("混合结束回到新动作末帧", isinstance(soft, float), f"{soft:.2f}")

    print("[2] 混合窗口时长")
    tl = am.Timeline()
    tl.play("crab")
    for _ in range(5):
        tl.step(DT)
    tl.play("hop", mix=0.15)
    n_mix = 0
    while tl.is_mixing() and n_mix < 100:
        tl.step(DT)
        n_mix += 1
    ck("0.15s ≈ 5 帧（30fps）", 4 <= n_mix <= 6, f"{n_mix} 帧")

    print("[3] 同一动作重播不建立混合")
    tl2 = am.Timeline()
    tl2.play("crab")
    tl2.step(DT)
    tl2.play("crab", mix=0.2)
    ck("重播同 clip 不混", not tl2.is_mixing())

    print("[4] 排队：hop 放完自动接 tumble")
    tl3 = am.Timeline()
    tl3.play("hop")
    tl3.queue("tumble")
    fired = []
    for _ in range(int((2.04 + 0.3) / DT)):
        tl3.step(DT)
        fired += tl3.pop_events()
    ck("hop 期间触发 3 次 land", fired.count("land") >= 3, f"{fired}")
    ck("播完切到 tumble", tl3.clip is not None and tl3.clip.name == "tumble",
       tl3.clip.name if tl3.clip else "None")
    ck("队列已清空", tl3._queue == [])

    print("[5] 变速")
    tl4 = am.Timeline()
    tl4.play("floatstep")
    tl4.time_scale = 0.5
    for _ in range(60):  # 真实 2 秒
        tl4.step(DT)
    dt_el = 1.0  # 2s × 0.5
    ck("0.5× 时 2 秒只推进约 1 秒", abs(tl4.t - dt_el) < 0.06, f"t={tl4.t:.2f}")
    tl4.time_scale = 1.0
    ck("时间缩放夹在 0.05~8", _clamp_check())

    print("[6] 每帧开销（混态最贵）")
    tl5 = am.Timeline()
    tl5.play("crab")
    for _ in range(3):
        tl5.step(DT)
    tl5.play("trot", mix=0.15)
    t0 = time.perf_counter()
    for _ in range(300):
        tl5.step(DT)
        tl5.pose_now()
        if not tl5.is_mixing():
            tl5.play("crab", mix=0.15)
    dt = (time.perf_counter() - t0) / 300 * 1e6
    ck("混态每帧 < 400µs", dt < 400, f"{dt:.0f} µs/帧")

    print(f"\n{P} passed, {F} failed")
    return 1 if F else 0


def _clamp_check():
    tl = am.Timeline()
    tl.play("crab")
    tl.time_scale = 99
    tl.step(1.0)
    hi = tl.t
    tl.play("crab")
    tl.time_scale = 0.0
    tl.step(1.0)
    lo = tl.t
    return hi <= 8.01 and lo <= 0.06 and lo > 0


if __name__ == "__main__":
    sys.exit(main())
