# -*- coding: utf-8 -*-
"""v3.0.24 动作导演验收：纯仲裁逻辑 + 真实 PetWindow 接线。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import anim_engine as anim  # noqa: E402
import director as d  # noqa: E402
import main as main_mod  # noqa: E402
from pet_window import ALL_ACTIONS  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def card(key, **kw):
    return d.card_for(key, **kw)


def pure_checks():
    # 1. 五档阶梯常量
    ck("优先级五档", (d.P_PHYS, d.P_USER, d.P_LLM, d.P_AUTO, d.P_IDLE) == (100, 90, 70, 50, 30))

    # 2. 同级不抢 + min_hold
    x = d.Director()
    ck("自动 hop 入队", x.submit(card("hop"), 1000, "auto")[0])
    r1 = x.submit(card("walk"), 1010, "auto")[1]
    ck("10ms 内先被 min_hold 拦", r1 == "min_hold", r1)
    x6 = d.Director()
    x6.submit(card("hop"), 0, "auto")
    r6 = x6.submit(card("walk"), 200, "auto")[1]
    ck("过了 min_hold 后同级不抢", r6 == "priority", r6)
    r2 = x.submit(card("wave", priority=90), 1050, "user")[1]
    ck("120ms 内用户也抢不动", r2 == "min_hold", r2)
    ck("过 min_hold 后用户抢成功", x.submit(card("wave", priority=90), 1200, "user")[0],
       f"priority={x.current_priority()}")

    # 3. 摔跤物理级、不可打断
    x2 = d.Director()
    ok = x2.submit(card("tumble"), 0, "user")[0]
    ck("tumble 物理优先级 100", ok and x2.current_priority() == 100)
    r3 = x2.submit(card("hop", priority=90), 400, "user")[1]
    ck("tumble 不可被普通动作打断", r3 in ("priority", "locked"), r3)

    # 4. 冷却只拦自主，不拦用户
    x3 = d.Director()
    ck("自主首播", x3.submit(card("dance"), 0, "auto")[0])
    x3.finish("dance")
    ck("自主 6s 内重播被冷却", x3.submit(card("dance"), 200, "auto")[1] == "cooldown")
    ck("用户连点绕过冷却", x3.submit(card("dance", priority=90), 300, "user")[0])

    # 5. then 接力
    x4 = d.Director()
    x4.submit(card("hop", then="wave"), 0, "auto")
    ck("播完返回 then", x4.finish("hop") == "wave")
    ck("then 按 50 级入队", x4.submit(card("wave"), 10, "chain")[0], f"priority={x4.current_priority()}")

    # 6. 拖拽锁
    x5 = d.Director()
    x5.submit(d.Action("drag", priority=100, physical=True, hold=True,
                       interruptible=False, min_hold_ms=0, dur_ms=0), 0, "physics", force=True)
    ck("拖拽期间用户动作被拒", x5.submit(card("wave", priority=90), 200, "user")[1] == "priority")
    x5.release("drag")
    ck("松手后恢复可播", x5.submit(card("wave", priority=90), 300, "user")[0])

    return {
        "min_hold": 120,
        "cooldown": 6000,
        "cards": len(d.CARDS),
    }


def real_checks(app):
    ctl = main_mod.Controller(app)
    p = ctl.pet

    ck("hop/tumble 均在剪辑库", all(k in anim.CLIPS for k in ("hop", "tumble")))
    ck("hop/tumble 均在动作表", all(k in ALL_ACTIONS for k in ("hop", "tumble")))
    ck("PetWindow 持有 Director", hasattr(p, "director"))

    # 自动 hop 起步，用户 0ms 抢不动，160ms 后可抢
    ok1 = p.do_action("hop", source="auto")
    ck("真实窗口：自动 hop 起播", ok1, p.director.snapshot())
    bad = p.do_action("wave", source="user")
    ck("真实窗口：min_hold 内用户被拒", not bad, p.director.snapshot())
    pump(app, 0.17)
    ok2 = p.do_action("wave", source="user")
    ck("真实窗口：用户动作抢过自动", ok2 and p.director.current_priority() == 90,
       p.director.snapshot())

    pump(app, 0.17)
    ok3 = p.do_action("tumble", source="user")
    ck("真实窗口：tumble 起播", ok3 and p.director.current_priority() == 100,
       p.director.snapshot())
    pump(app, 0.34)
    bad2 = p.do_action("hop", source="user")
    ck("真实窗口：摔跤中普通动作被拒", not bad2, p.director.snapshot())

    # then 接力：brawl 播完自动接 look（避开前面的 cooldown 记录）
    p.finish_state()
    pump(app, 0.05)
    okc = p.do_action("brawl", then="look", source="user")
    ck("真实窗口：then 动作起播", okc, p.director.snapshot())
    pump(app, 2.85)
    ck("真实窗口：then 接力到 look", p.director.current_key() == "look" or p.state == "look",
       f"key={p.director.current_key()} state={p.state}")

    p.finish_state()
    pump(app, 0.05)
    ck("真实窗口：收尾回 idle", p.state == "idle" and p.director.current_key() == "",
       f"state={p.state} key={p.director.current_key()}")
    return p.director.snapshot()


def pump(app, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.01)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    meta = pure_checks()
    snap = real_checks(app)
    print("\ncards=%d  min_hold=%dms  cooldown=%dms" %
          (meta["cards"], meta["min_hold"], meta["cooldown"]))
    print("director snapshot:", snap)
    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
