# -*- coding: utf-8 -*-
"""v2.9.3b 自检：外部浏览器（Tabbit）接入。

    .venv/Scripts/python.exe test_v293b.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QGuiApplication

import main as m
import paths

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)

print("== 1. 浏览器探测 ==")
exe = paths.find_browser()
check("找到外部浏览器", bool(exe) and os.path.exists(exe), exe)
check("是 Tabbit", os.path.basename(exe).lower().startswith("tabbit"), os.path.basename(exe))

print("== 2. 托盘入口 ==")
labels = [a.text() for a in ctl.tray.contextMenu().actions() if a.text()]
check("托盘有 Tabbit 搜索项", any("Tabbit" in x for x in labels), str(labels))

print("== 3. 调用参数（拦截 startDetached，不真开窗口）==")
captured = {}
real_detach = m.QProcess.startDetached


def fake_detach(program, args, *a, **k):
    captured["program"] = program
    captured["args"] = list(args)
    return True


m.QProcess.startDetached = staticmethod(fake_detach)
QGuiApplication.clipboard().setText("鲸鱼娘 桌宠  更新")
ctl.search_in_browser()
check("调用了 startDetached", captured.get("program", "").endswith("Tabbit Browser.exe"), captured.get("program"))
url = (captured.get("args") or [""])[0]
check("URL 编码正确", url.startswith("https://www.bing.com/search?q=") and "%E9%B2%B8%E9%B1%BC%E5%A8%98" in url, url)
check("多空格被压成一个", "%20%20" not in url)

captured.clear()
QGuiApplication.clipboard().setText("   ")
bubble = []
real_bubble = ctl.pet.bubble.show_text
ctl.pet.bubble.show_text = lambda t, ms=0: bubble.append(t)
ctl.search_in_browser()
check("空剪贴板不启动浏览器", "program" not in captured, str(captured))
check("空剪贴板给提示", bubble and "复制" in bubble[0], str(bubble))
ctl.pet.bubble.show_text = real_bubble
m.QProcess.startDetached = real_detach

print()
print("结果:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
ctl.quit_app()
sys.exit(0 if not FAIL else 1)
