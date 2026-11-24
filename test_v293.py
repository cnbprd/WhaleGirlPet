# -*- coding: utf-8 -*-
"""v2.9.3 自检：托盘右键不再隐藏、静音模式、面板 macOS 侧边栏、切换类动作静默。

    .venv/Scripts/python.exe test_v293.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication, QTabWidget, QSystemTrayIcon

import main as m
import panel as pl

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)

print("== 1. 托盘右键 bug（右键只弹菜单，不该藏桌宠）==")
ctl.pet.show()
ctx = QSystemTrayIcon.ActivationReason.Context
ctl._on_tray_activated(ctx)
app.processEvents()
check("右键后桌宠仍然可见", ctl.pet.isVisible(), f"visible={ctl.pet.isVisible()}")
check("右键不动 _user_hidden", ctl._user_hidden in (False, None), str(ctl._user_hidden))
ctl.pet.show()
ctl._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
app.processEvents()
check("左键单击才切换（此轮应隐藏）", not ctl.pet.isVisible(), f"visible={ctl.pet.isVisible()}")
ctl.pet.show()

print("== 2. 托盘菜单 ==")
menu = ctl.tray.contextMenu()
labels = [a.text() for a in menu.actions() if a.text()]
check("托盘有静音模式", any("静音" in x for x in labels), str(labels))
check("隐藏桌宠不再重复两项", sum(1 for x in labels if x.strip() == "隐藏桌宠") <= 1, str(labels))
check("托盘仍有退出", any("退出" in x for x in labels))

print("== 3. 静音模式：闲聊不发声，有事照常 ==")
import tts as tts_mod
calls = []
real_say = ctl.tts.say
ctl.tts.say = lambda *a, **k: calls.append(a[0])
ctl.config["tts_on"] = True
ctl.config["tts_online"] = True
ctl.config["mute_idle"] = True
calls.clear()
ctl._speak("闲聊测试", 200, priority=0)
check("priority0 不发声", len(calls) == 0, f"calls={len(calls)}")
calls.clear()
ctl._speak("有事测试", 200, priority=2)
check("priority2 照常发声", len(calls) == 1, f"calls={len(calls)}")
calls.clear()
ctl.set_mute_idle(False)
ctl._speak("关掉静音后闲聊", 200, priority=0)
check("关静音后 priority0 发声", len(calls) == 1, f"calls={len(calls)}")
ctl.set_mute_idle(True)
ctl.tts.say = real_say

print("== 4. 切换类动作静默 ==")
calls.clear()
ctl.tts.say = lambda *a, **k: calls.append(a[0])
ctl.config["tts_on"] = True
ctl.on_action("change")
check("换装动作不播台词", len(calls) == 0, f"calls={len(calls)}")
check("SILENT_ACTIONS 含 change", "change" in ctl.SILENT_ACTIONS, str(ctl.SILENT_ACTIONS))
ctl.tts.say = real_say

print("== 5. 面板 macOS 侧边栏 ==")
p = pl.ControlPanel(ctl)
app.processEvents()
check("侧边栏是列表控件", hasattr(p, "side") and p.side.count() >= 8, f"items={p.side.count()}")
check("侧边栏宽度可控", p.side.width() >= 130, f"w={p.side.width()}")
check("内容区页数一致", p.stack.count() == p.side.count(),
      f"pages={p.stack.count()} / side={p.side.count()}")
p.side.setCurrentRow(3)
app.processEvents()
check("点侧边栏能切页", p.stack.currentIndex() == 3, f"idx={p.stack.currentIndex()}")
p.side.setCurrentRow(0)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "_matting")
os.makedirs(out, exist_ok=True)
for mode in ("light", "dark"):
    ctl.config["theme"] = mode
    p.apply_theme()
    p.resize(760, 720)
    p.show()
    app.processEvents()
    for _ in range(6):
        app.processEvents()
    p.grab().save(os.path.join(out, f"v293-panel-{mode}.png"))
check("两套面板截图已生成", os.path.exists(os.path.join(out, "v293-panel-light.png")))
p.hide()

print()
print("结果:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
ctl.quit_app()
sys.exit(0 if not FAIL else 1)
