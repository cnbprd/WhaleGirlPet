# -*- coding: utf-8 -*-
"""v2.9.3 复现：换皮肤/表情时人物是否"消失"。

采样 pet 的 visible / size / alpha / pix 是否为空，定位闪烁来源。
    .venv/Scripts/python.exe test_flash.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as m

app = QApplication([])
ctl = m.Controller(app)

# 关掉会干扰判断的后台行为
ctl.config["tts_on"] = False
ctl.config["fs_hide_on"] = False
ctl.config["power_saver_on"] = False
ctl.config["guard"] = False

pet = ctl.pet
pet.show()
app.processEvents()

samples = []
t0 = [0.0]

STEPS = [
    (0.0, "基线", None),
    (1.2, "切 sleep 表情(6s)", lambda: pet.set_expression("sleep", 6000)),
    (7.5, "回默认皮肤", lambda: pet.restore_base_expression()),
    (8.5, "切 longmaid", lambda: pet.set_skin("longmaid")),
    (9.5, "切 default", lambda: pet.set_skin("default")),
    (10.5, "切 hanfu", lambda: pet.set_skin("hanfu")),
    (11.5, "切回 default", lambda: pet.set_skin("default")),
]

done = {"i": 0}


def sample():
    t0[0] += 0.1
    t = t0[0]
    while done["i"] < len(STEPS) and t >= STEPS[done["i"]][0]:
        label = STEPS[done["i"]][1]
        fn = STEPS[done["i"]][2]
        if fn:
            try:
                fn()
            except Exception as e:  # noqa: BLE001
                print(f"  step '{label}' error: {e}")
        print(f"[{t:5.1f}s] step -> {label}")
        done["i"] += 1
    samples.append({
        "t": round(t, 1),
        "vis": pet.isVisible(),
        "w": pet.width(),
        "h": pet.height(),
        "alpha": round(pet.alpha, 2),
        "pixnull": pet._pix.isNull(),
        "pixw": pet._pix.width(),
        "skin": ctl.config.get("skin"),
        "expr": pet.expr,
    })


timer = QTimer()
timer.setInterval(100)
timer.timeout.connect(sample)
timer.start()
QTimer.singleShot(12500, app.quit)
app.exec()

print("\n== 异常采样（不可见 / 窗口过小 / alpha 低 / pix 空） ==")
bad = [s for s in samples if (not s["vis"]) or s["w"] <= 40 or s["alpha"] < 0.6 or s["pixnull"]]
if not bad:
    print("  无异常")
else:
    for s in bad:
        print("  ", s)

print("\n== 尺寸变化点 ==")
prev = None
for s in samples:
    if prev and (abs(s["h"] - prev["h"]) > 12 or abs(s["w"] - prev["w"]) > 12 or s["skin"] != prev["skin"]):
        print(f"  {prev['t']}s {prev['skin']}/{prev['expr']} {prev['w']}x{prev['h']}"
              f"  ->  {s['t']}s {s['skin']}/{s['expr']} {s['w']}x{s['h']}")
    prev = s

print("\n总采样:", len(samples))
