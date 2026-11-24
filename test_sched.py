# -*- coding: utf-8 -*-
"""定时器逻辑验证：22:00 催促序列 + 每天任务触发（把触发时间调到当前分钟）。"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

import scheduler  # noqa: E402

now = time.localtime()
hm = time.strftime("%H:%M", now)
scheduler.NIGHT_HOUR = now.tm_hour
scheduler.NIGHT_MIN = now.tm_min

cfg = {}
sched = scheduler.Scheduler(cfg)
fired = []
nights = []
sched.fire.connect(lambda t: fired.append(t))
sched.night_remind.connect(lambda n: nights.append(n))

task = sched.add("daily", hm, "喝水")
sched.tick()
print("daily fired:", [t["text"] for t in fired])
print("night #1:", nights, "| status:", sched.snooze_status())

cfg["schedule"]["night_last_ts"] = time.time() - (scheduler.SNOOZE_MIN * 60 + 10)
sched.tick()
print("night #2:", nights)

cfg["schedule"]["night_last_ts"] = time.time() - (scheduler.SNOOZE_MIN * 60 + 10)
sched.tick()
print("night #3:", nights)

cfg["schedule"]["night_last_ts"] = time.time() - (scheduler.SNOOZE_MIN * 60 + 10)
sched.tick()
print("night #4:", nights, "| 到上限后不再加:", sched.snooze_status())

# 同一天重复 tick 不会重复触发 daily
sched.tick()
print("daily after repeat:", len(fired))

# once 任务：触发后自动停用
once = sched.add("once", time.strftime("%Y-%m-%d ", now) + hm, "一次性提醒")
sched.tick()
print("once fired:", [t["text"] for t in fired], "| enabled:", once["enabled"])
print("DONE")
