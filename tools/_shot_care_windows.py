# -*- coding: utf-8 -*-
"""v2.9.7 目检：零食商城 / 背包 / 状态栏 / 动作提问 四个窗口的真实渲染。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import care_ui
import main as main_mod

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")


def run():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)

    # 造点数据：背包里放两样，金币给够
    ctl.state.coins = 120
    ctl.state.hunger = 30
    ctl.state.add_to_bag("fish", 2)
    ctl.state.add_to_bag("cake", 1)

    shop = care_ui.SnackShopWindow(ctl)
    shop.show()
    bag = care_ui.BackpackWindow(ctl)
    bag.show()
    status = care_ui.StatusBarWindow(ctl)
    status.show_need("hungry")
    status.show()
    ask = care_ui.ActionAskBubble(ctl, [("wave", "挥挥手"), ("dance", "跳个舞")])
    ask.show()

    def grab():
        for name, w in (("shop", shop), ("bag", bag), ("status", status), ("ask", ask)):
            app.processEvents()
            w.grab().save(os.path.join(OUT, f"v297-win-{name}.png"))
        app.quit()

    QTimer.singleShot(1200, grab)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
