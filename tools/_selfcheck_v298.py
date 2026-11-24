# -*- coding: utf-8 -*-
"""v2.9.8 自检：换装动作不换衣、睡觉姿态、六类资讯、金币只来自打工。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import ambient
import main as main_mod

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main_mod.Controller(app, defer_show=True)
res = {}


def step1():
    # 换装后做动作：base 不能被动作帧替换（否则就是"换衣服"）
    ctl.set_skin("hanfu")
    b0 = ctl.pet.base.cacheKey()
    ctl.pet.do_action("wave", 3000)
    res["hanfu_base_unchanged"] = (b0 == ctl.pet.base.cacheKey())
    res["hanfu_state"] = ctl.pet.state

    # 默认女仆装仍可用动作帧
    ctl.set_skin("default")
    b1 = ctl.pet.base.cacheKey()
    ctl.pet.do_action("dance", 3000)
    res["default_uses_sprite"] = (b1 != ctl.pet.base.cacheKey())

    # 睡觉：换回汉服，姿态要真的变（alpha 在 tick 里降）
    ctl.set_skin("hanfu")
    ctl.pet.do_sleep()
    res["sleep_state"] = ctl.pet.state


def step2():
    res["sleep_alpha"] = round(ctl.pet.alpha, 2)
    res["sleep_rot"] = round(ctl.pet.rot, 1)
    # 六类资讯实抓
    for cat in ("news", "sports", "ent", "tech", "finance", "politics"):
        try:
            res["feed_" + cat] = len(ambient.fetch_news(3, cat))
        except Exception as e:  # noqa: BLE001
            res["feed_" + cat] = "ERR " + str(e)[:40]
    # 金币只靠打工：确认没有 coin_timer
    res["has_coin_timer"] = hasattr(ctl, "coin_timer")
    print(res)
    ok = (res["hanfu_base_unchanged"] and res["default_uses_sprite"]
          and res["sleep_state"] == "sleep" and res["sleep_alpha"] < 0.9
          and not res["has_coin_timer"])
    print("RESULT:", "ALL PASS" if ok else "HAS FAIL")
    app.quit()


QTimer.singleShot(2600, step1)
QTimer.singleShot(4200, step2)
sys.exit(app.exec())
