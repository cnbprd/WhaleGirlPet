# -*- coding: utf-8 -*-
"""v2.9.9 目检：让桌宠进入 sleep 状态，连抓 4 帧看姿态是否真的"蹲坐打盹"。
不依赖桌面截图，直接 grab 窗口内容，避免被浏览器挡住。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import main as main_mod

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")
os.makedirs(OUT, exist_ok=True)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    pet = ctl.pet
    pet.show()
    pet.do_sleep()

    frames = []

    def cap(i=0):
        try:
            frames.append({k: getattr(pet, k) for k in ("sy", "sx", "rot", "alpha", "bob", "state")})
            pet.grab().save(os.path.join(OUT, "v299-sleep-%d.png" % i))
        except Exception as e:  # noqa: BLE001
            print("GRAB ERROR:", type(e).__name__, e)
        if i < 3:
            QTimer.singleShot(1500, lambda: cap(i + 1))
        else:
            for k, f in enumerate(frames):
                print("frame%d" % k, f)
            app.quit()

    QTimer.singleShot(1200, cap)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
