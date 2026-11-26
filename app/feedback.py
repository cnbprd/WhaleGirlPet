# -*- coding: utf-8 -*-
"""v3.0.27 anim 第四阶段：反馈分级 + 泊松节流 + thinking 占位。

设计口径：
- L0 静默：只记账，不表情/不动作/不出声；适合重复刺激、内部状态。
- L1 微反馈：只换表情（最多带一个极小状态），不弹气泡、不响；适合自主表情/环境提示。
- L2 普通反馈：表情 + 可选动作/气泡/音效；走自主优先级，不抢用户动作。
- L3 强反馈：高优先级动作 + 气泡/音效；用于错误、碰撞、需要立刻被看见的事。
- 泊松节流：自主/环境反馈按每分钟次数做泊松抽样，另加 min_gap；用户直点/物理事件可 force 绕过。
- thinking：聊天等待超过 delay 才进入，回复/失败时收回；不覆盖用户正在播的动作。
"""
from __future__ import annotations

import math
import random
import time
from typing import Optional

from PySide6.QtCore import QTimer

import director as director_mod

L0 = 0
L1 = 1
L2 = 2
L3 = 3

LEVEL_LABELS = {L0: "L0 静默", L1: "L1 微反馈", L2: "L2 普通反馈", L3: "L3 强反馈"}
LEVEL_PRIORITY = {L1: director_mod.P_IDLE, L2: director_mod.P_AUTO, L3: director_mod.P_LLM}


class PoissonGate:
    """按 key 的泊松节流器。

    在同一 key 上以 rate_per_min 的强度做 Bernoulli 抽样（间隔 dt 的概率
    1-exp(-rate*dt/60)），再叠一个 min_gap。这样既不会均匀得像节拍器，
    也不会因为某几次密集调用突然刷屏；force 只给用户直点/物理事件用。
    """

    def __init__(self, rng: Optional[random.Random] = None):
        self._last = {}
        self._rng = rng or random

    def hit(self, key: str, rate_per_min: float, min_gap_s: float = 0.0,
            now: Optional[float] = None, force: bool = False) -> bool:
        now = time.monotonic() if now is None else float(now)
        last = self._last.get(key)
        self._last[key] = now
        if force:
            return True
        if last is None:
            return True
        dt = max(0.0, now - last)
        if dt < max(0.0, min_gap_s):
            return False
        rate = max(0.0, float(rate_per_min))
        if rate <= 0:
            return False
        p = 1.0 - math.exp(-rate * dt / 60.0)
        return self._rng.random() < p


class FeedbackBus:
    """Controller 持有的反馈总线；所有视觉/听觉反馈尽量从这里过。"""

    def __init__(self, controller):
        self.ctl = controller
        self.gate = PoissonGate()
        self.counts = {L0: 0, L1: 0, L2: 0, L3: 0}
        self.last = {}
        self._thinking_wanted = False
        self._thinking_timer = QTimer()
        self._thinking_timer.setSingleShot(True)
        self._thinking_timer.timeout.connect(self._begin_thinking)

    # ---------- 节流 ----------
    def allow(self, key: str, rate_per_min: float = 4.0, min_gap_s: float = 0.0,
              force: bool = False, now: Optional[float] = None) -> bool:
        ok = self.gate.hit(key, rate_per_min, min_gap_s, now=now, force=force)
        self.last[key] = time.monotonic() if now is None else float(now)
        return ok

    # ---------- 反馈分级 ----------
    def emit(self, level: int, key: str = "", *, action: str = "", expr: str = "",
             bubble: str = "", sfx: str = "", source: str = "auto",
             priority: Optional[int] = None, rate_per_min: float = 0.0,
             min_gap_s: float = 0.0, force: bool = False,
             expr_ms: int = 2400, bubble_ms: int = 2800) -> bool:
        """发一条反馈；返回是否真的产生了可见/可听反馈。"""
        level = int(level)
        self.counts[level] = self.counts.get(level, 0) + 1
        if level <= L0:
            return False
        if rate_per_min > 0 and not force:
            if not self.allow(key or f"L{level}", rate_per_min, min_gap_s):
                return False

        pet = getattr(self.ctl, "pet", None)
        if pet is None:
            return False
        started = False
        if level >= L1 and expr:
            try:
                pet.set_expression(expr, max(0, int(expr_ms)))
            except Exception:  # noqa: BLE001
                pass
        if action:
            try:
                pri = (priority if priority is not None
                       else LEVEL_PRIORITY.get(level, director_mod.P_AUTO))
                started = bool(pet.do_action(action, source=source, priority=pri,
                                             force=bool(force and level >= L3)))
            except Exception:  # noqa: BLE001
                started = False
            if not started and level >= L2:
                # 动作被仲裁拒绝时，至少不要把气泡/音效盖在别人动作上
                return False
        if level >= L2 and bubble:
            try:
                self.ctl._speak(bubble, bubble_ms, priority=1)
            except Exception:  # noqa: BLE001
                pass
        if level >= L2 and sfx:
            try:
                self.ctl.beep(sfx)
            except Exception:  # noqa: BLE001
                pass
        return True

    # ---------- thinking 占位 ----------
    def start_thinking(self, delay_ms: int = 700):
        """聊天已发出，等 delay 还没有结果才占位；立刻回复不会闪一下。"""
        self._thinking_wanted = True
        self._thinking_timer.start(max(0, int(delay_ms)))

    def _begin_thinking(self):
        if not self._thinking_wanted:
            return
        pet = getattr(self.ctl, "pet", None)
        if pet is None:
            return
        try:
            pet.begin_thinking("让我想一下…", 1500)
        except Exception:  # noqa: BLE001
            pass

    def end_thinking(self):
        self._thinking_wanted = False
        try:
            self._thinking_timer.stop()
        except Exception:  # noqa: BLE001
            pass
        pet = getattr(self.ctl, "pet", None)
        if pet is not None:
            try:
                pet.end_thinking()
            except Exception:  # noqa: BLE001
                pass

    def snapshot(self) -> dict:
        return {
            "counts": dict(self.counts),
            "thinking": bool(self._thinking_wanted),
            "gates": dict(self.last),
        }
