# -*- coding: utf-8 -*-
"""v3.0.26 离屏运行验收：PetWindow 分层/弹簧接入 + 背包自动取食。"""
import os
import sys
import time
import types
import json
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as main_mod  # noqa: E402
import pet_window as pet_mod  # noqa: E402
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


class StubCtl:
    def __init__(self):
        self.config = {
            "skin": "jk", "scale": 1.0, "anchor_crop": True,
            "alpha_mask": False, "skeletal": False, "rig_mesh": False,
            "render_quality": "high", "frame_ms": 33,
        }

    def __getattr__(self, name):
        return lambda *a, **k: None


def bag_checks():
    st = state_mod.PetState()
    st.hunger = 30
    st.thirst = 80
    st.bag = {"rice": 2, "lemonwater": 1}
    picked = []

    class Stub:
        def __init__(self):
            self.state = st
            self.task_active = None
            self._bag_last_use = 0.0

        def eat_from_bag(self, key, auto=False):
            picked.append((key, auto))
            return st.eat(key, auto_buy=False)

    s = Stub()
    ok = main_mod.Controller._auto_use_bag(s)
    ck("饿了会自动从背包取主食", ok and picked and picked[0][0] == "rice", picked)
    ck("取食后背包份数减少", st.bag.get("rice") == 1, st.bag)
    ck("自动取食标记 auto=True", picked[0][1] is True, picked)

    # 冷却：同一分钟内不再吃
    picked.clear()
    ok2 = main_mod.Controller._auto_use_bag(s)
    ck("150s 冷却内不重复取食", (not ok2) and not picked, (ok2, picked))

    # 渴了优先水
    s2 = Stub()
    s2._bag_last_use = 0.0
    s2.state.hunger = 80
    s2.state.thirst = 25
    s2.state.bag = {"rice": 2, "lemonwater": 1}
    picked.clear()
    main_mod.Controller._auto_use_bag(s2)
    ck("渴了优先拿水/水果", picked and picked[0][0] == "lemonwater", picked)

    # 不饿不渴不乱吃
    s3 = Stub()
    s3.state.hunger = 90
    s3.state.thirst = 90
    s3.state.bag = {"rice": 2}
    picked.clear()
    ok3 = main_mod.Controller._auto_use_bag(s3)
    ck("满状态不浪费背包食物", (not ok3) and not picked, picked)

    # 只有玩具：不动
    s4 = Stub()
    s4.state.hunger = 20
    s4.state.bag = {"toy_bubble": 2}
    picked.clear()
    ok4 = main_mod.Controller._auto_use_bag(s4)
    ck("玩具不会被当成食物", (not ok4) and not picked, picked)

    # 打工中：不自动拿（避免打断动作；临界由 care tick 的 force 路径另说）
    s5 = Stub()
    s5.state.hunger = 20
    s5.state.bag = {"rice": 2}
    s5.task_active = "clean"
    picked.clear()
    ok5 = main_mod.Controller._auto_use_bag(s5)
    ck("打工中不自动取食", (not ok5) and not picked, picked)


def save_checks(app):
    """v3.0.26 追加：save_config 的合并写盘必须真的落到 config.json。"""
    td = tempfile.mkdtemp(prefix="whale_cfg_")
    target = os.path.join(td, "config.json")
    orig = main_mod.config_file
    main_mod.config_file = lambda: target
    try:
        s = types.SimpleNamespace()
        s.pet = types.SimpleNamespace(save_position=lambda: None)
        s.config = {"save": {}}
        s.state = types.SimpleNamespace(to_dict=lambda: {"hunger": 42, "thirst": 7})
        s.emotion = types.SimpleNamespace(to_dict=lambda: {"mood": "ok"})
        s._save_timer = QTimer()
        s._save_timer.setSingleShot(True)
        s._flush_config = types.MethodType(main_mod.Controller._flush_config, s)
        s._save_timer.timeout.connect(s._flush_config)
        main_mod.Controller.save_config(s)
        pump(app, 0.8)
        ck("save_config 600ms 后真正落盘", os.path.exists(target), target)
        got = json.load(open(target, encoding="utf-8")) if os.path.exists(target) else {}
        ck("落盘内容包含养成状态", got.get("save", {}).get("hunger") == 42
           and got.get("emotion", {}).get("mood") == "ok", got)
    finally:
        main_mod.config_file = orig


def split_checks():
    from PIL import Image
    import secondary as sm

    for skin in ("default", "jk"):
        sec = sm.SecondaryMotion(1.0)
        ok = sec.set_skin(skin, False)
        expected = {"skirt", "tail"} | ({"hair_l", "hair_r"} if skin == "default" else set())
        ck("分层资产可加载 %s" % skin, ok and set(sec.pix) == expected, list(sec.pix))
    sec_other = sm.SecondaryMotion(1.0)
    ok_other = sec_other.set_skin("blackgown", False)
    ck("未做分层的皮肤自动回退平图", not ok_other and not sec_other.enabled, ok_other)
    # 资产静止叠加：整图 + 层，应基本重合（不挖洞，不会露白）
    for skin in ("default", "jk"):
        img = Image.open(os.path.join(ROOT, "assets", "skins", skin + ".png")).convert("RGBA")
        for part in ("tail", "skirt"):
            layer = Image.open(os.path.join(ROOT, "assets", "skins", "layers",
                                            skin + "_" + part + ".png")).convert("RGBA")
            ck("层画布与原图同尺寸 %s/%s" % (skin, part), layer.size == img.size, layer.size)


def window_checks(app):
    p = pet_mod.PetWindow(StubCtl(), show_now=False)
    ck("JK 分层已启用", p._layer_active and p._sec.enabled, p._sec.angles())
    ck("底图保留完整立绘（不挖洞）", p.base.width() == 283, p.base.size())
    ck("尾巴/裙摆弹簧已建", set(p._sec.springs) == {"tail", "skirt"}, list(p._sec.springs))
    p.set_pet_scale(1.4)
    ck("放大到 1.4 倍自动切 2x 层", bool(p._sec.two), p._sec.pix["skirt"].size())
    p.set_pet_scale(1.0)
    ck("缩回 1.0 倍回 1x 层", not p._sec.two, p._sec.pix["skirt"].size())
    # 跑 1 秒，弹簧不应 NaN/越界
    p.show()
    pump(app, 0.5)
    vals = p._sec.angles()
    ck("弹簧角度有限且在限幅内", all(-15 <= v <= 15 for v in vals.values()), vals)
    # 给一个横向位移，弹簧应产生偏角
    p._sec.t = 0.0
    for _ in range(20):
        p._sec.step(0.033, 12.0, 0.0, "idle", 0.0)
    ck("横向惯性带动裙摆/尾巴", abs(p._sec.angles()["skirt"]) > 0.1,
       p._sec.angles())
    # 抓 idle 帧
    p.repaint()
    pump(app, 0.08)
    shot = p.grab()
    ck("窗口能出帧", not shot.isNull() and shot.width() > 200, shot.size())
    shot.save(os.path.join(ROOT, "docs", "_v326_runtime_jk.png"))
    # 步态分支：不叠两层，但必须用完整图
    p.state = "walk"
    p.gait_on = True
    p._layer_active = False
    p.gait = 0.3
    p.repaint()
    pump(app, 0.05)
    ck("步态分支保留完整裙摆/尾巴", p._gait_source().width() == p._pix.width(),
       (p._gait_source().size(), p._pix.size()))
    p.close()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    bag_checks()
    save_checks(app)
    split_checks()
    window_checks(app)
    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
