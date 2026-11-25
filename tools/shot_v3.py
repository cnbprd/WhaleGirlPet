# -*- coding: utf-8 -*-
"""v3.0.0 目检脚本：启动屏 / 面板（养成、定时任务、聊天）/ 桌宠五个打工动作，逐张抓图。"""
import os
import sys
import time

APP = r"F:\WhaleGirlPet\app"
sys.path.insert(0, APP)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as main_mod  # noqa: E402
import splash as splash_mod  # noqa: E402

OUT = r"F:\WhaleGirlPet\assets\_matting\v3"
os.makedirs(OUT, exist_ok=True)


def _grab_on_dark(widget, path, bg=(24, 30, 42)):
    """透明窗口直接 grab 是透明底，垫一层深色再存，方便看清边缘和阴影。"""
    pm = widget.grab()
    if pm.isNull():
        return
    img = QImage(pm.size(), QImage.Format_ARGB32)
    img.fill(QColor(*bg))
    p = QPainter(img)
    p.drawPixmap(0, 0, pm)
    p.end()
    img.save(path)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    sp = splash_mod.LoadingSplash()
    sp.show()
    state = {"ctl": None}

    def after_splash():
        _grab_on_dark(sp, os.path.join(OUT, "v3-splash.png"), bg=(18, 22, 30))
        sp.close()
        state["ctl"] = main_mod.Controller(app)
        state["ctl"].open_panel()
        QTimer.singleShot(2500, after_panel)

    def after_panel():
        controller = state["ctl"]
        panel = controller.panel
        panel.tabs.setCurrentIndex(0)
        app.processEvents()
        panel.grab().save(os.path.join(OUT, "v3-panel-status.png"))
        panel._on_name_edit()
        app.processEvents()
        panel.grab().save(os.path.join(OUT, "v3-panel-status-edit.png"))
        panel._on_name_save()
        app.processEvents()
        panel.tabs.setCurrentIndex(2)
        app.processEvents()
        panel.grab().save(os.path.join(OUT, "v3-panel-remind.png"))
        panel.tabs.setCurrentIndex(3)
        panel.append_chat("user", "在吗？")
        panel.append_chat("assistant", "在呢，我看着你。")
        app.processEvents()
        panel.grab().save(os.path.join(OUT, "v3-panel-chat.png"))
        shot_work()

    def shot_work():
        controller = state["ctl"]
        for st in ("work_study", "work_clean", "work_wipe", "work_chores", "work_rest"):
            controller.pet.do_task_work(st)
            for _ in range(18):
                app.processEvents()
                time.sleep(0.02)
            _grab_on_dark(controller.pet, os.path.join(OUT, f"v3-pet-{st}.png"))
        controller.pet.finish_state()
        app.quit()

    QTimer.singleShot(1500, after_splash)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
