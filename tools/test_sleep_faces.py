# -*- coding: utf-8 -*-
"""第 21 条：8 套皮肤睡觉时是否真的换成闭眼差分。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import main as m  # noqa: E402
from paths import SKINS  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def main():
    app = QApplication(sys.argv)
    ctl = m.Controller(app)
    pet = ctl.pet
    for key in SKINS:
        pet.set_skin(key)
        normal = pet._pix.cacheKey()
        has = bool(pet._sleep_rel())
        pet.do_sleep()
        slept = pet._pix.cacheKey()
        ck(f"{key} 有闭眼差分", has)
        ck(f"{key} 睡觉换图", slept != normal)
        pet.wake()
        ck(f"{key} 醒来还原", pet._pix.cacheKey() != slept and pet.state != "sleep")
    bad = [x for x in R if not x[1]]
    print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")
    ctl.quit_app()


if __name__ == "__main__":
    main()
