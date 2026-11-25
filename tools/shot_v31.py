# -*- coding: utf-8 -*-
"""v3.0.1 验证：启动画面是否「纯人物 + 真在动」，以及首启新人礼包 / 玩具消耗。

输出：
  assets/_matting/v3/v31-splash-t03.png  ~ 0.3s
  assets/_matting/v3/v31-splash-t09.png  ~ 0.9s
  assets/_matting/v3/v31-splash-t18.png  ~ 1.8s
  assets/_matting/v3/v31-splash-t28.png  ~ 2.8s
并打印每帧人物 alpha 质心与包围盒，证明画面在动（不是一张静止图）。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
OUT = os.path.join(ROOT, "assets", "_matting", "v3")
os.makedirs(OUT, exist_ok=True)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def _alpha_stats(img: QImage):
    """返回人物（alpha>8）的包围盒与质心。"""
    w, h = img.width(), img.height()
    total = 0
    sx = sy = 0
    minx, miny, maxx, maxy = w, h, -1, -1
    step = 2
    for y in range(0, h, step):
        for x in range(0, w, step):
            a = img.pixelColor(x, y).alpha()
            if a > 8:
                total += 1
                sx += x
                sy += y
                if x < minx:
                    minx = x
                if y < miny:
                    miny = y
                if x > maxx:
                    maxx = x
                if y > maxy:
                    maxy = y
    if not total:
        return None
    return (round(sx / total, 1), round(sy / total, 1),
            (minx, miny, maxx, maxy), total)


def run_splash():
    from splash import LoadingSplash

    app = QApplication.instance() or QApplication([])
    sp = LoadingSplash()
    sp.show()
    frames = {}

    def snap(tag):
        pm = sp.grab()
        path = os.path.join(OUT, f"v31-splash-{tag}.png")
        pm.save(path)
        img = pm.toImage()
        frames[tag] = _alpha_stats(img)

    for tag, ms in (("t03", 320), ("t09", 900), ("t18", 1800), ("t28", 2800)):
        QTimer.singleShot(ms, lambda t=tag: snap(t))
    QTimer.singleShot(3400, app.quit)
    app.exec()

    print("SPLASH_SIZE", sp.width(), sp.height())
    for tag, st in frames.items():
        print("FRAME", tag, st)


def run_state():
    from state import PetState

    s = PetState()
    s.from_dict({"hunger": 0, "thirst": 0, "mood": 14, "intimacy": 87, "coins": 412})
    print("GIFT1", round(s.hunger, 1), round(s.thirst, 1), round(s.mood, 1),
          "sent=", s._gift_just_sent, "flag=", s.gift_v3)

    d = s.to_dict()
    print("SAVED_KEYS", sorted(d.keys()))
    s2 = PetState()
    s2.from_dict(dict(d, hunger=0, thirst=0, mood=5))
    print("GIFT2_AFTER_STARVE", round(s2.hunger, 1), round(s2.thirst, 1),
          round(s2.mood, 1), "sent=", s2._gift_just_sent)


def run_toy():
    """玩具一次性消耗：连玩两次，第二次应报没货。"""
    import snacks
    from state import PetState

    class FakeBag:
        pass

    s = PetState()
    s.bag = {"toy_yarn": 2}
    print("TOY_BEFORE", s.bag.get("toy_yarn"))
    ok1 = s.take_from_bag("toy_yarn")
    print("TOY_TAKE1", ok1, s.bag.get("toy_yarn"))
    ok2 = s.take_from_bag("toy_yarn")
    print("TOY_TAKE2", ok2, s.bag.get("toy_yarn"))
    ok3 = s.take_from_bag("toy_yarn")
    print("TOY_TAKE3_empty", ok3)


if __name__ == "__main__":
    run_state()
    run_toy()
    run_splash()
