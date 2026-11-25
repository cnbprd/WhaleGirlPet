# -*- coding: utf-8 -*-
"""v3.0.22 真机逐页面检：真实窗口显示后切完 13 页，每页抓图并检查不是空白。

    python tools/inspect_all_pages_v322.py
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton, QWidget  # noqa: E402

import main as main_mod  # noqa: E402

OUT = os.path.join(ROOT, "docs", "panel_v322")
R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def screen_stats(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((40, 40))
    px = list(im.getdata())
    uniq = len(set(px))
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
    return uniq, avg


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    ctl.open_panel()
    panel = ctl.panel
    panel.resize(780, 920)
    panel.show()
    panel.raise_()
    panel.activateWindow()
    os.makedirs(OUT, exist_ok=True)

    def run_pages():
        n = panel.tabs.count()
        print(f"真实桌面逐页：共 {n} 页")
        for i in range(n):
            label = panel.side.item(i).text()
            t0 = time.perf_counter()
            panel.tabs.setCurrentIndex(i)
            app.processEvents()
            time.sleep(0.12)
            app.processEvents()
            ms = (time.perf_counter() - t0) * 1000
            page = panel.tabs.widget(i)
            fname = os.path.join(OUT, f"p{i:02d}_{label}.png")
            ok = panel.grab().save(fname)
            uniq, avg = screen_stats(fname)
            buttons = len(page.findChildren(QPushButton))
            widgets = len(page.findChildren(QWidget))
            ck(f"{label}", ok and uniq >= 6,
               f"{ms:.0f}ms｜按钮 {buttons}｜控件 {widgets}｜色阶 {uniq}｜均色 {avg}")
        # 关掉再开一次：验证重复打开不会残留/错位
        panel.close()
        app.processEvents()
        ctl.open_panel()
        ctl.panel.resize(780, 920)
        ctl.panel.show()
        app.processEvents()
        ck("二次打开仍正常", ctl.panel.tabs.count() == n, f"{ctl.panel.tabs.count()} 页")
        bad = [x for x in R if not x[1]]
        print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")
        print("截图目录:", OUT)
        ctl.quit_app()

    QTimer.singleShot(900, run_pages)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
