# -*- coding: utf-8 -*-
"""第 15 条：打工选项 10 秒超时，真等满 10 秒看会不会自己开工。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as m  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = m.Controller(app)
    ctl.task_active = None
    t0 = time.time()
    ctl.offer_work()
    print("已弹出打工三选一，不点，等 10 秒…")

    def after_wait():
        el = time.time() - t0
        ck("10 秒内没有自动开工", el >= 9.0, f"{el:.2f}s")
        ck("10 秒后自己开工了", ctl.task_active is not None,
           f"选了 {ctl.task_active.get('key') if ctl.task_active else '无'}｜{time.time() - t0:.2f}s")
        if ctl.task_active:
            print(f"  工种：{ctl.task_active['key']}｜总时长 {ctl.task_active['total']}s")
        bad = [x for x in R if not x[1]]
        print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")
        ctl.quit_app()

    QTimer.singleShot(11500, after_wait)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
