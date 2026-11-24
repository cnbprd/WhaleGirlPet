# -*- coding: utf-8 -*-
"""轻量定时任务 + 22:00 休息提醒（含持续催促）。

任务类型：
  once    指定日期时间触发一次（"YYYY-MM-DD HH:MM"）
  daily   每天固定时刻（"HH:MM"）
  weekly  每周固定星期与时刻（weekday 0=周一，when="HH:MM"）

数据存 config["schedule"]["tasks"]（列表），跨重启保留；last_fired 防止重复触发。
"""
import time
import uuid

from PySide6.QtCore import QObject, QTimer, Signal

CHECK_MS = 30_000
NIGHT_HOUR, NIGHT_MIN = 22, 0
SNOOZE_MIN = 15          # 催不睡时，每隔多久再提醒
MAX_SNOOZE = 4           # 最多催几次


def now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def today_str() -> str:
    return time.strftime("%Y-%m-%d")


def weekday_now() -> int:
    return time.localtime().tm_wday


class Scheduler(QObject):
    fire = Signal(dict)      # 任务到点
    night_remind = Signal(int)  # 参数：第几次提醒（0 = 首次）

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.cfg = config.setdefault("schedule", {})
        self.cfg.setdefault("tasks", [])
        self.cfg.setdefault("night_on", True)
        self.cfg.setdefault("night_last_day", "")
        self.cfg.setdefault("night_snooze", 0)
        self.cfg.setdefault("night_last_ts", 0)
        self.timer = QTimer()
        self.timer.setInterval(CHECK_MS)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    # ---------- 任务管理 ----------
    def tasks(self) -> list:
        return self.cfg.setdefault("tasks", [])

    def add(self, kind: str, when: str, text: str, weekday: int = -1) -> dict:
        t = {
            "id": uuid.uuid4().hex[:8],
            "kind": kind,
            "when": when.strip(),
            "text": text.strip(),
            "weekday": weekday,
            "enabled": True,
            "last_fired": "",
        }
        self.tasks().append(t)
        return t

    def remove(self, tid: str) -> bool:
        before = len(self.tasks())
        self.cfg["tasks"] = [t for t in self.tasks() if t["id"] != tid]
        return len(self.cfg["tasks"]) != before

    def toggle(self, tid: str, on: bool) -> bool:
        for t in self.tasks():
            if t["id"] == tid:
                t["enabled"] = bool(on)
                return True
        return False

    # ---------- 触发判断 ----------
    def _due(self, t: dict, now: time.struct_time) -> bool:
        if not t.get("enabled", True):
            return False
        day = time.strftime("%Y-%m-%d", now)
        hm = time.strftime("%H:%M", now)
        kind = t.get("kind")
        if kind == "once":
            target = t.get("when", "")
            # 精确到分钟触发；触发后自动关闭
            if target == f"{day} {hm}" and t.get("last_fired") != target:
                t["last_fired"] = target
                t["enabled"] = False
                return True
            return False
        if kind == "daily":
            if t.get("when") == hm and t.get("last_fired") != f"{day} {hm}":
                t["last_fired"] = f"{day} {hm}"
                return True
            return False
        if kind == "weekly":
            if int(t.get("weekday", -1)) == now.tm_wday and t.get("when") == hm \
                    and t.get("last_fired") != f"{day} {hm}":
                t["last_fired"] = f"{day} {hm}"
                return True
            return False
        return False

    def tick(self):
        now = time.localtime()
        for t in self.tasks():
            if self._due(t, now):
                self.fire.emit(t)
        self._night_check(now)

    # ---------- 22:00 休息提醒 ----------
    def _night_check(self, now: time.struct_time):
        if not self.cfg.get("night_on", True):
            return
        day = time.strftime("%Y-%m-%d", now)
        hm = now.tm_hour * 60 + now.tm_min
        target = NIGHT_HOUR * 60 + NIGHT_MIN
        # 过零点后不再算"当天的 22 点"
        if hm < target:
            if self.cfg.get("night_last_day") != day:
                self.cfg["night_snooze"] = 0
            return
        if hm >= target + 180:  # 22:00 之后 3 小时不再打扰
            return
        last_day = self.cfg.get("night_last_day", "")
        snooze = int(self.cfg.get("night_snooze", 0))
        last_ts = float(self.cfg.get("night_last_ts", 0))
        if last_day != day:
            # 当天首次到点
            self.cfg["night_last_day"] = day
            self.cfg["night_snooze"] = 1
            self.cfg["night_last_ts"] = time.time()
            self.night_remind.emit(0)
            return
        if snooze >= MAX_SNOOZE:
            return
        if time.time() - last_ts >= SNOOZE_MIN * 60:
            self.cfg["night_snooze"] = snooze + 1
            self.cfg["night_last_ts"] = time.time()
            self.night_remind.emit(snooze)

    def snooze_status(self) -> str:
        n = int(self.cfg.get("night_snooze", 0))
        if not self.cfg.get("night_on", True):
            return "已关闭"
        if n == 0:
            return "待触发（每天 22:00）"
        return f"已提醒 {n} 次（最多 {MAX_SNOOZE} 次，间隔 {SNOOZE_MIN} 分钟）"

    def reset_night(self):
        self.cfg["night_last_day"] = ""
        self.cfg["night_snooze"] = 0
        self.cfg["night_last_ts"] = 0
