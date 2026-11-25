# -*- coding: utf-8 -*-
"""面板首次打开耗时拆解：每个页面的构建时间（v3.0.22 优化依据）。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import main as main_mod  # noqa: E402
import panel as panel_mod  # noqa: E402
import panel_v2  # noqa: E402

TIMES = []


def wrap(cls, name, label):
    fn = getattr(cls, name, None)
    if fn is None:
        return
    def timed(*a, **k):
        t0 = time.perf_counter()
        r = fn(*a, **k)
        TIMES.append((label, (time.perf_counter() - t0) * 1000))
        return r
    setattr(cls, name, timed)


for n in dir(panel_mod.ControlPanel):
    if n.startswith("_tab_"):
        wrap(panel_mod.ControlPanel, n, n)
for n in dir(panel_v2):
    if n.startswith("tab_"):
        wrap(panel_v2, n, "panel_v2." + n)


def main():
    app = QApplication([])
    t0 = time.perf_counter()
    ctl = main_mod.Controller(app)
    t_ctrl = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    p = panel_mod.ControlPanel(ctl)
    t_ctor = (time.perf_counter() - t1) * 1000
    t2 = time.perf_counter()
    p.refresh()
    t_ref = (time.perf_counter() - t2) * 1000
    print(f"Controller 初始化 {t_ctrl:.0f}ms｜面板构造 {t_ctor:.0f}ms｜refresh {t_ref:.0f}ms")
    p._theme_mode = None
    t3 = time.perf_counter()
    p.apply_theme()
    print(f"apply_theme（强制重套）{(time.perf_counter() - t3) * 1000:.0f}ms")
    print("页面构建耗时（ms）")
    for label, ms in sorted(TIMES, key=lambda x: -x[1]):
        print(f"  {ms:8.1f}  {label}")
    print(f"  合计 {sum(m for _, m in TIMES):.0f}ms")
    ctl.quit_app()


if __name__ == "__main__":
    main()
