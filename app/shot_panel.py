# -*- coding: utf-8 -*-
"""开发用：真实桌面启动后打开控制面板，逐标签页抓图，供目检。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod
from paths import APP_VERSION

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "_matting")
os.makedirs(OUT, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    controller = main_mod.Controller(app)
    controller.open_panel()
    panel = controller.panel

    # 注入示例聊天气泡
    panel.append_chat("user", "在吗？新动作和任务都加上了吗")
    panel.append_chat("assistant",
                      "在啦在啦。挥手、跳舞、敲电脑、吹气球、放烟花、舞狮、换衣服，"
                      "螃蟹步、小跑、左右看、吃白饭，都能从右键菜单点；"
                      "清理垃圾、擦桌面、做家务也在打工页啦。")
    panel.append_chat("user", "版本号和更新检查呢？")
    panel.append_chat("assistant", f"当前 v{APP_VERSION}，设置页填好清单地址就能联网检查更新。")

    tabs = panel.tabs
    names = ["status", "tasks", "remind", "chat", "settings"]

    def shot_all():
        for i, name in enumerate(names):
            tabs.setCurrentIndex(i)
            app.processEvents()
            panel.grab().save(os.path.join(OUT, f"v3-panel-{name}.png"))
        controller.pet.grab().save(os.path.join(OUT, "v3-panel-pet.png"))
        app.quit()

    QTimer.singleShot(900, shot_all)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
