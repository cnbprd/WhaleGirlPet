# -*- coding: utf-8 -*-
"""第 11 条：更新提醒的 1 小时定时器真跑满一轮。

跑法（建议后台起，别关）：
    python tools/probe_update_reminder.py
日志逐行追加到 tools/_update_reminder_log.txt，含起止时间与点火次数。
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
LOG = os.path.join(ROOT, "tools", "_update_reminder_log.txt")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as m  # noqa: E402

FIRES = []


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = m.Controller(app)
    ctl._arm_update_reminder({"latest": "3.0.22"})
    t = ctl._update_remind
    log(f"定时器已启动 interval={t.interval()}ms 预期 {t.interval() / 3600000:.2f} 小时")

    def on_fire():
        FIRES.append(datetime.datetime.now())
        log(f"第 {len(FIRES)} 次提醒触发（累计 {len(FIRES)} 次）")

    t.timeout.connect(on_fire)

    def finish():
        log(f"收尾：点火 {len(FIRES)} 次；间隔 {[str(b - a) for a, b in zip(FIRES, FIRES[1:])]}")
        print(f"fires={len(FIRES)}")
        ctl.quit_app()

    QTimer.singleShot(62 * 60 * 1000, finish)
    log("开始等待 62 分钟（只等，不做别的事）")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
