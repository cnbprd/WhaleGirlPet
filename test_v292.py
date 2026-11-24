# -*- coding: utf-8 -*-
"""v2.9.2 自检：主题三档、托盘菜单迁移、唤醒词、去蒙版余量、形态切换不发声。

    .venv/Scripts/python.exe test_v292.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication

import main as m
import theme

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)

print("== 1. 主题 ==")
check("系统浅色判定可读", isinstance(theme.system_is_light(), bool), str(theme.system_is_light()))
for mode in ("light", "dark"):
    check(f"{mode} 能取到 qss", len(theme.load_qss(mode)) > 300, f"{len(theme.load_qss(mode))} 字符")
check("auto 解析为 light/dark", theme.resolve("auto") in ("light", "dark"), theme.resolve("auto"))
ctl.config["theme"] = "auto"
before = ctl.config.get("theme")
ctl.set_theme("light")
check("切浅色生效", ctl.config.get("theme") == "light")
ctl.set_theme("dark")
check("切深色生效", ctl.config.get("theme") == "dark")
pal_l, pal_d = theme.palette("light"), theme.palette("dark")
check("两套调色板不同", pal_l["chat_bg"] != pal_d["chat_bg"], f"{pal_l['chat_bg']} vs {pal_d['chat_bg']}")
ctl.set_theme("auto")

print("== 2. 托盘 / 右键菜单 ==")
tray_menu = ctl.tray.contextMenu()
labels = [a.text() for a in tray_menu.actions() if a.text()]
sub = [a.menu().title() for a in tray_menu.actions() if a.menu()]
check("托盘有控制面板", any("控制面板" in x for x in labels), str(labels))
check("托盘有隐藏桌宠", any("隐藏桌宠" in x for x in labels), str(labels))
check("托盘有退出程序", any("退出" in x for x in labels), str(labels))
check("托盘有主题子菜单", any("主题" in x for x in sub), str(sub))

print("== 3. 唤醒词 ==")
words = ctl.wake_words()
print("   候选:", words)
check("含大肥鱼", "大肥鱼" in words)
check("含你好大肥鱼", "你好大肥鱼" in words or "你好，大肥鱼" in words)
name = ctl.config.get("name")
check("含当前角色名", any(name in w for w in words), name)
check("整句唤醒命中", ctl._match_wake_word("大肥鱼") == "大肥鱼")
check("带你好命中", ctl._match_wake_word("你好，大肥鱼") == "你好，大肥鱼", ctl._match_wake_word("你好，大肥鱼"))
check("名字唤醒命中", ctl._match_wake_word("你好，" + name) != "", ctl._match_wake_word("你好，" + name))
check("闲聊不误伤", ctl._match_wake_word("今天天气怎么样") == "")

print("== 4. 去蒙版活动余量 ==")
pad = ctl.pet._pad
check("窗口留有活动余量", pad > 0, f"pad={pad}")
check("蒙版默认关闭", bool(ctl.config.get("alpha_mask", False)) is False)
check("窗口比立绘大", ctl.pet.width() > ctl.pet._pix.width() and ctl.pet.height() > ctl.pet._pix.height(),
      f"win={ctl.pet.width()}x{ctl.pet.height()} pix={ctl.pet._pix.width()}x{ctl.pet._pix.height()}")

print("== 5. 形态切换不发声 ==")
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "main.py"),
           encoding="utf-8").read()
seg = src.split("def on_form_change")[1].split("def ")[0]
check("on_form_change 里没有 _speak", "_speak" not in seg)

print()
print("结果:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
ctl.quit_app()
sys.exit(0 if not FAIL else 1)
