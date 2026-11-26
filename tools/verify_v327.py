# -*- coding: utf-8 -*-
"""v3.0.27 离屏验收：本地模型状态 / 完工富江脸 / 反馈 L0-L3 / 泊松 / thinking。"""
import os
import sys
import time
import types

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import feedback as fb_mod  # noqa: E402
import main as main_mod  # noqa: E402
import panel as panel_mod  # noqa: E402
import pet_window as pet_mod  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def pump(app, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.01)


class StubCtl:
    def __init__(self):
        self.config = {
            "skin": "jk", "scale": 1.0, "anchor_crop": True,
            "alpha_mask": False, "skeletal": False, "rig_mesh": False,
            "render_quality": "high", "frame_ms": 33,
        }

    def __getattr__(self, name):
        return lambda *a, **k: None


class FakePet:
    def __init__(self):
        self.expr = []
        self.actions = []
        self.thinking = []
        self.finished = 0

    def finish_state(self):
        self.finished += 1

    def set_expression(self, name, ms=0):
        self.expr.append((name, ms))

    def do_action(self, key, **kw):
        self.actions.append((key, kw))
        return True

    def begin_thinking(self, text="", ms=0):
        self.thinking.append(("begin", text))
        return True

    def end_thinking(self):
        self.thinking.append(("end", ""))


class FakeCtl:
    def __init__(self):
        self.pet = FakePet()
        self.spoken = []
        self.beeps = []

    def _speak(self, text, ms=0, priority=0):
        self.spoken.append((text, ms, priority))

    def beep(self, kind):
        self.beeps.append(kind)


def status_checks():
    ck("未加载但有文件 → 可启动（没有加载）",
       panel_mod.local_llm_status_text({"available": True, "running": False})
       == "可启动（没有加载）")
    ck("已加载 → 运行中",
       panel_mod.local_llm_status_text({"available": True, "running": True}) == "运行中")
    ck("没装 → 明确说不影响使用",
       "还没装本地模型" in panel_mod.local_llm_status_text({"available": False}))


def level_checks(app):
    c = FakeCtl()
    fb = fb_mod.FeedbackBus(c)
    ck("L0 只记账，不换脸",
       (not fb.emit(fb_mod.L0, "x", expr="happy")) and c.pet.expr == []
       and fb.counts[fb_mod.L0] == 1)
    ck("L1 只换表情，不弹气泡/不响",
       fb.emit(fb_mod.L1, "y", expr="shy") and c.pet.expr[-1][0] == "shy"
       and not c.spoken and not c.beeps)
    ck("L2 表情 + 气泡 + 音效",
       fb.emit(fb_mod.L2, "z", expr="curious", bubble="完工", sfx="done")
       and c.pet.expr[-1][0] == "curious" and c.spoken and c.beeps == ["done"])
    ck("L3 可带动作/高优先级",
       fb.emit(fb_mod.L3, "w", action="hop", expr="angry", bubble="出错",
               sfx="error", source="llm") and c.pet.actions
       and c.pet.actions[-1][1].get("priority") == 70)
    # thinking 定时器
    fb.start_thinking(0)
    pump(app, 0.15)
    ck("thinking 延时到点后进入占位", c.pet.thinking and c.pet.thinking[-1][0] == "begin")
    fb.end_thinking()
    ck("thinking 收回", c.pet.thinking[-1][0] == "end")


def gate_checks():
    import random
    g = fb_mod.PoissonGate(random.Random(3))
    ck("force 绕过节流", g.hit("k", 0, 100, now=1.0, force=True))
    ck("rate=0 不产生自主反馈", not g.hit("k", 0, 0, now=5.0))
    ck("min_gap 内拦截",
       g.hit("k2", 10, 30, now=1.0)
       and not g.hit("k2", 10, 30, now=10.0))
    ck("超过 min_gap 后按泊松可放行",
       g.hit("k2", 10, 30, now=40.0))


def task_checks(app):
    c = FakeCtl()
    c.state = types.SimpleNamespace(
        reward=lambda **kw: True, level=7)
    c.config = {"tasks": {"done_count": {}}}
    c.task_active = {"key": "study"}
    c.task_timer = types.SimpleNamespace(stop=lambda: None)
    c.pet = FakePet()
    c.feedback = fb_mod.FeedbackBus(c)
    c.save_config = lambda: None
    c.panel = None
    c.refresh_panel = lambda: None
    c.bubble_text = []
    c._speak = lambda text, ms=0, priority=0: c.bubble_text.append(text)
    main_mod.Controller._finish_task(c)
    ck("完工调用 finish_state 收回打工态", c.pet.finished == 1, c.pet.finished)
    ck("完工不再调用 happy 脸",
       all(e[0] != "happy" for e in c.pet.expr), c.pet.expr)
    ck("完工走 L2 反馈",
       c.feedback.counts[fb_mod.L2] == 1 and c.bubble_text, c.feedback.counts)


def thinking_window_checks(app):
    p = pet_mod.PetWindow(StubCtl(), show_now=False)
    ck("thinking 能进入",
       p.begin_thinking("想一下", 1000) and p.state == "thinking"
       and p.director.current_key() == "thinking")
    p.end_thinking()
    ck("thinking 收回后回 idle", p.state == "idle" and not p.director.current_key())
    # 用户动作更高优先级，不被 thinking 抢
    p.do_action("wave", source="user")
    ck("用户动作已占用时 thinking 不抢",
       (not p.begin_thinking()) and p.director.current_key() == "wave")
    p.finish_state()
    p.close()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    status_checks()
    level_checks(app)
    gate_checks()
    task_checks(app)
    thinking_window_checks(app)
    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
