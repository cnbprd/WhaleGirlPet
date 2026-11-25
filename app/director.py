# -*- coding: utf-8 -*-
"""动作导演（Action Director）：动作调度与仲裁的唯一入口。

v3.0.24 第一阶段：把“谁来决定此刻播哪个动作、能不能抢、会不会碎”
从托盘菜单 / scheduler / 各 act_* 里收回来。渲染、剪辑、表情仍由
pet_window / anim_engine / skeletal 负责，本模块只做决策。

设计口径（与 anim.md 一致）：
- 一张 Action 卡描述一次表演：clip / expr / bubble / 时长 / 优先级 / 冷却。
- 优先级五档：物理 100 > 用户直点 90 > LLM 70 > 自主 50 > 待机噪声 30。
- min_hold_ms：任何动作至少站住一小段，防止鼠标扫过时三个动作各播 60ms。
- 同级不抢，先到先服务；不可打断的动作（摔跤/拖拽）只能被物理动作或显式 force 抢。
- 冷却只拦自主/待机来源，不拦用户直点，避免“点同一动作没反应”。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable, Optional

# 优先级阶梯
P_PHYS = 100
P_USER = 90
P_LLM = 70
P_AUTO = 50
P_IDLE = 30

SOURCE_PRIORITY = {
    "physics": P_PHYS,
    "user": P_USER,
    "llm": P_LLM,
    "auto": P_AUTO,
    "idle": P_IDLE,
    "chain": P_AUTO,
}


@dataclass(frozen=True)
class Action:
    """一张动作卡。加新动作 = 往 CARDS 加一行，不再四头改。"""
    key: str
    clip: Optional[str] = None
    expr: Optional[str] = None
    bubble: Optional[str] = None
    sfx: Optional[str] = None
    dur_ms: int = 800
    mix: float = 0.30
    priority: int = P_AUTO
    interruptible: bool = True
    min_hold_ms: int = 120
    cooldown_ms: int = 0
    hold: bool = False
    then: str = ""
    physical: bool = False
    when: Optional[Callable[[], bool]] = None

    def with_values(self, **kw) -> "Action":
        return replace(self, **kw)


@dataclass
class Active:
    action: Action
    started: int
    source: str


# 动作卡登记表：剪辑 / 表情 / 时长 / 冷却。气泡文案暂由 main.on_action 统一发，
# 下一阶段再并进卡片，避免这一版同时改行为与文案。
CARDS = {
    "wave":      Action("wave", clip=None, expr="happy", dur_ms=3000, cooldown_ms=6000),
    "dance":     Action("dance", clip=None, expr="happy", dur_ms=3000, cooldown_ms=8000, min_hold_ms=240),
    "type":      Action("type", clip=None, expr="curious", dur_ms=3000, cooldown_ms=6000),
    "balloon":   Action("balloon", clip=None, expr="happy", dur_ms=3000, cooldown_ms=6000),
    "fireworks": Action("fireworks", clip=None, expr="happy", dur_ms=3000, cooldown_ms=8000),
    "lion":      Action("lion", clip=None, expr="happy", dur_ms=3000, cooldown_ms=8000),
    "change":    Action("change", clip=None, expr=None, dur_ms=3000, cooldown_ms=1000),
    "crab":      Action("crab", clip="crab", dur_ms=3000, cooldown_ms=5000),
    "floatstep": Action("floatstep", clip="floatstep", dur_ms=3000, cooldown_ms=5000),
    "trot":      Action("trot", clip="trot", dur_ms=3000, cooldown_ms=5000),
    "look":      Action("look", clip="look", dur_ms=3000, cooldown_ms=5000),
    "eatrice":   Action("eatrice", clip="eatrice", expr="eat", dur_ms=3000, cooldown_ms=5000),
    "tumble":    Action("tumble", clip="tumble", expr="angry", dur_ms=2400, priority=P_PHYS,
                        interruptible=False, min_hold_ms=300, physical=True),
    "brawl":     Action("brawl", clip="brawl", expr="happy", dur_ms=2600, cooldown_ms=8000),
    "hop":       Action("hop", clip="hop", expr="happy", dur_ms=2200, cooldown_ms=6000, min_hold_ms=180),
}

DEFAULT_CARD = Action(key="", dur_ms=3000, priority=P_AUTO, cooldown_ms=4000)


def card_for(key: str, dur_ms: int = 0, then: str = "", priority: Optional[int] = None,
             mix: float = 0.30, hold: bool = False) -> Action:
    """按 key 取卡并按本次调用覆盖时长/优先级/接力。"""
    base = CARDS.get(key, DEFAULT_CARD.with_values(key=key))
    p = base.priority if priority is None else int(priority)
    if base.physical:
        p = max(p, P_PHYS)          # 物理动作不能被调用方降级
    return base.with_values(
        key=key,
        dur_ms=int(dur_ms or base.dur_ms),
        then=then or base.then,
        priority=p,
        mix=float(mix),
        hold=bool(hold or base.hold),
    )


class Director:
    """唯一仲裁器。线程不安全，只在 Qt 主线程用。"""

    def __init__(self):
        self.cur: Optional[Active] = None
        self.last_fire: dict[str, int] = {}
        self.rejected: dict[str, str] = {}
        self.accepted = 0
        self.rejected_count = 0

    @staticmethod
    def _now(now_ms: Optional[int]) -> int:
        if now_ms is not None:
            return int(now_ms)
        return int(time.monotonic() * 1000)

    def submit(self, act: Action, now_ms: Optional[int] = None,
               source: str = "auto", force: bool = False) -> tuple[bool, str]:
        """尝试开始一个动作。返回 (是否接受, 原因)。"""
        now = self._now(now_ms)
        if act.when is not None:
            try:
                if not act.when():
                    self._reject(act.key, "when")
                    return False, "when"
            except Exception:  # noqa: BLE001
                self._reject(act.key, "when")
                return False, "when"

        # 冷却只对自主/待机生效：用户连点同一动作不应被拦。
        if not force and source in ("auto", "idle") and act.cooldown_ms > 0:
            last = self.last_fire.get(act.key)
            if last is not None and now - last < act.cooldown_ms:
                self._reject(act.key, "cooldown")
                return False, "cooldown"

        cur = self.cur
        if cur is not None and not force:
            held = now - cur.started
            if held < cur.action.min_hold_ms:
                self._reject(act.key, "min_hold")
                return False, "min_hold"
            if act.priority <= cur.action.priority:
                self._reject(act.key, "priority")
                return False, "priority"
            if not cur.action.interruptible and not act.physical:
                self._reject(act.key, "locked")
                return False, "locked"

        self.last_fire[act.key] = now
        self.cur = Active(action=act, started=now, source=source)
        self.accepted += 1
        self.rejected.pop(act.key, None)
        return True, "ok"

    def release(self, key: Optional[str] = None) -> bool:
        """显式释放 hold/当前动作；key 为空时释放任意当前动作。"""
        if self.cur is None:
            return False
        if key and self.cur.action.key != key:
            return False
        self.cur = None
        return True

    def finish(self, key: str) -> str:
        """动作正常播完：清空当前并返回 then 接力的 key。"""
        cur = self.cur
        if cur is None or cur.action.key != key:
            return ""
        self.cur = None
        return cur.action.then or ""

    def tick(self, now_ms: Optional[int] = None) -> str:
        """兜底超时：返回 then key（正常情况下由 pet_window 的定时器驱动）。"""
        cur = self.cur
        if cur is None or cur.action.hold:
            return ""
        if self._now(now_ms) - cur.started >= cur.action.dur_ms:
            self.cur = None
            return cur.action.then or ""
        return ""

    def current_key(self) -> str:
        return self.cur.action.key if self.cur else ""

    def current_priority(self) -> int:
        return self.cur.action.priority if self.cur else -1

    def snapshot(self) -> dict:
        return {
            "key": self.current_key(),
            "priority": self.current_priority(),
            "source": self.cur.source if self.cur else "",
            "held_ms": (self._now(None) - self.cur.started) if self.cur else 0,
            "accepted": self.accepted,
            "rejected": self.rejected_count,
        }

    def _reject(self, key: str, why: str):
        self.rejected[key] = why
        self.rejected_count += 1
