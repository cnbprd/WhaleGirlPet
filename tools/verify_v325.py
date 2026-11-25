# -*- coding: utf-8 -*-
"""v3.0.25 验收：API/本地路由、打工二级页、养成衰减与讨要、表情补丁+口型。"""
import os
import sys
import time
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import local_llm  # noqa: E402
import main as main_mod  # noqa: E402
import state as state_mod  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def pump(app, seconds):
    t0 = time.time()
    while time.time() - t0 < seconds:
        app.processEvents()
        time.sleep(0.01)


def route_checks():
    ck("有 API/本地可用，默认走 API",
       local_llm.chat_route({"llm_on": True}, True, True) == "cloud")
    ck("勾了优先本地，走本地",
       local_llm.chat_route({"llm_on": True, "llm_prefer_local": True}, True, True) == "local")
    ck("无 API，本地兜底",
       local_llm.chat_route({"llm_on": True}, False, True) == "local")
    ck("无 API/无本地，返回 none",
       local_llm.chat_route({"llm_on": True}, False, False) == "none")
    ck("关闭本地且无 API，返回 none",
       local_llm.chat_route({"llm_on": False}, False, True) == "none")


def state_checks():
    s = state_mod.PetState()
    s.hunger = 100
    s.thirst = 100
    t0 = time.time()
    s._last_decay = t0
    for i in range(8 * 60):
        s.decay(now=t0 + (i + 1) * 60)
    ck("连续 8 小时只掉约 58 饱食（不再归零）", 40 <= s.hunger <= 45, round(s.hunger, 1))
    ck("连续 8 小时只掉约 32 水分", 66 <= s.thirst <= 71, round(s.thirst, 1))
    # 关掉程序 8 小时回来：跨休眠最多补 6 小时
    s2 = state_mod.PetState()
    s2.hunger = 100
    s2.thirst = 100
    s2._last_decay = time.time() - 8 * 3600
    s2.decay(now=time.time())
    ck("离线 8 小时只结算 6 小时", 55 <= s2.hunger <= 58, round(s2.hunger, 1))
    s.hunger = 0
    s.thirst = 0
    ck("又饿又渴识别为 both", s.critical_need() == "both")
    s.hunger = 0
    s.thirst = 20
    ck("只饿识别 hungry", s.critical_need() == "hungry")
    s.hunger = 20
    s.thirst = 0
    ck("只渴识别 thirsty", s.critical_need() == "thirsty")


def beg_checks():
    class Pet:
        def set_expression(self, *a, **k):
            pass

    class Emo:
        def apply(self, *a, **k):
            pass

    st = state_mod.PetState()
    st.hunger = 0
    st.thirst = 0
    st.bag = {"rice": 2, "lemonwater": 1}
    chosen = []

    def eat(key):
        chosen.append(key)
        return True, key

    stub = types.SimpleNamespace(
        state=st, _speak=lambda *a, **k: None, pet=Pet(), emotion=Emo(),
        open_shop=lambda: None, eat_from_bag=eat)
    main_mod.Controller.beg_snack(stub, "thirsty", show_shop=False)
    ck("口渴时背包优先拿饮品/水果（柠檬水）", chosen == ["lemonwater"], chosen)


def panel_checks(app, ctl):
    ctl.open_panel()
    app.processEvents()
    pump(app, 0.15)
    p = ctl.panel
    ck("养成页有 2 级 stack", hasattr(p, "status_stack") and p.status_stack.count() == 2)
    ck("默认停在养成主页面", p.status_stack.currentIndex() == 0)
    ctl.open_task_page()
    app.processEvents()
    ck("去打工进入二级页", p.status_stack.currentIndex() == 1)
    p.show_status_page(0)
    ck("返回按钮回主页面", p.status_stack.currentIndex() == 0)
    p.grab().save(os.path.join(ROOT, "docs", "_v325_panel_status.png"))
    ctl.open_task_page()
    app.processEvents()
    p.grab().save(os.path.join(ROOT, "docs", "_v325_panel_work.png"))


def expr_checks(app, ctl):
    p = ctl.pet
    old_skin = ctl.config.get("skin", "default")
    old_base = p.base
    ctl.config["skin"] = "default"
    p.base = p._load_skin("default")
    p.set_expression("happy", 0)
    pump(app, 0.05)
    ck("默认皮肤 happy 用脸补丁，身体不换", p.base.width() == 267, p.base.size())
    ck("happy 有嘴部小块", p._mouth_pix is not None)
    p._mouth_level = 0.0
    p.repaint()
    pump(app, 0.05)
    p.grab().save(os.path.join(ROOT, "docs", "_v325_happy_m0.png"))
    p._mouth_level = 1.0
    p.repaint()
    pump(app, 0.05)
    p.grab().save(os.path.join(ROOT, "docs", "_v325_happy_m1.png"))
    p.set_expression("sleep", 0)
    pump(app, 0.05)
    ck("sleep 保留整图换姿势", p.base.width() != 267 and p._mouth_pix is None, p.base.size())
    # JK 皮肤也吃同一套脸补丁（用户当前用的就是 JK）
    ctl.config["skin"] = "jk"
    p.base = p._load_skin("jk")
    p.set_expression("happy", 0)
    pump(app, 0.05)
    ck("JK 皮肤 happy 只换脸", p.base.width() == 283 and p._mouth_pix is not None, p.base.size())
    p.set_expression("sleep", 0)
    pump(app, 0.05)
    ck("JK sleep 不跳回女仆整图", p.base.width() == 283 and p._mouth_pix is None, p.base.size())
    # 恢复用户当前皮肤，避免测试把界面留在女仆装
    ctl.config["skin"] = old_skin
    p.base = old_base
    p.restore_base_expression()


def audio_checks(ctl):
    p = os.path.join(os.environ.get("LOCALAPPDATA", ""), "..", "..", "")
    cache = r"F:\WhaleGirlPetApp\accounts\default\tts_cache\47b130c854aa71aa8abf6a66.mp3"
    if not os.path.exists(cache):
        ck("TTS 缓存存在", False, cache)
        return
    am = ctl.audio
    ok = am.play_file(cache, 1, 0, speech=True)
    ck("TTS 播放并启动包络", ok, f"env={len(am._env)}")
    levels = []
    t0 = time.time()
    while time.time() - t0 < 1.2:
        levels.append(am.speech_level())
        QApplication.instance().processEvents()
        time.sleep(0.04)
    ck("RMS 包络已解码", len(am._env) > 100, f"points={len(am._env)}")
    ck("播放中口型强度有起伏", max(levels) > 0.3 and any(x > 0 for x in levels),
       f"max={max(levels):.2f}")
    am.player.stop()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    route_checks()
    state_checks()
    beg_checks()
    ctl = main_mod.Controller(app)
    panel_checks(app, ctl)
    expr_checks(app, ctl)
    audio_checks(ctl)
    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
