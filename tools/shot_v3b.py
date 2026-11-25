# -*- coding: utf-8 -*-
"""v3.0.0 功能验证：聊天是否只发一次、窗口能否缩放、玩具货架与背包陪玩。"""
import os
import sys
import time

APP = r"F:\WhaleGirlPet\app"
sys.path.insert(0, APP)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import main as main_mod  # noqa: E402

OUT = r"F:\WhaleGirlPet\assets\_matting\v3"
os.makedirs(OUT, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    ctl.open_panel()
    panel = ctl.panel

    def run():
        # ---- 1. 聊天只发一次 ----
        panel.tabs.setCurrentIndex(3)
        panel.clear_chat()          # 先清空内存气泡，只验证这一次发送产生几条
        ctl._chat_plain = lambda t: panel.append_chat("assistant", "收到：" + t)
        panel.chat_input.setPlainText("只发一次测试")
        panel.send_chat()
        app.processEvents()
        user_rows = [it for it in panel._chat_log if it.get("role") == "user"]
        print("USER_BUBBLES =", len(user_rows), "| texts:", [it.get("text") for it in user_rows])
        for _ in range(6):
            app.processEvents()
            time.sleep(0.05)
        panel.grab().save(os.path.join(OUT, "v3-chat-once.png"))

        # ---- 2. 窗口缩放 ----
        panel.resize(520, 620)
        app.processEvents()
        print("PANEL_SIZE_AFTER_RESIZE =", panel.width(), panel.height())
        panel.grab().save(os.path.join(OUT, "v3-panel-small.png"))
        panel.resize(680, 830)
        app.processEvents()

        # ---- 3. 玩具货架 + 背包陪玩 ----
        ctl.state.bag["toy_bubble"] = 2
        ctl.state.bag["toy_yarn"] = 1
        shop = __import__("care_ui").SnackShopWindow(ctl)
        shop.show()
        shop.switch("玩具")
        app.processEvents()
        time.sleep(0.2)
        import snacks
        print("TOY_ITEMS =", [it["name"] for it in snacks.items_of("玩具")])
        shop.grab().save(os.path.join(OUT, "v3-shop-toys.png"))
        bag = __import__("care_ui").BackpackWindow(ctl)
        bag.show()
        app.processEvents()
        time.sleep(0.2)
        bag.grab().save(os.path.join(OUT, "v3-bag-toys.png"))
        k_int0 = ctl.state.intimacy
        ctl.play_toy("toy_bubble")
        app.processEvents()
        print("INTIMACY", round(k_int0, 1), "->", round(ctl.state.intimacy, 1),
              "| mood", round(ctl.state.mood, 1))
        panel.tabs.setCurrentIndex(0)
        ctl.refresh_panel()
        app.processEvents()
        panel.grab().save(os.path.join(OUT, "v3-panel-status2.png"))
        app.quit()

    QTimer.singleShot(1200, run)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
