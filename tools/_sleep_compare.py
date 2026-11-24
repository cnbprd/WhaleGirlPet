# -*- coding: utf-8 -*-
"""v2.9.9 对比：抓 idle 一帧 + sleep 一帧，用像素包围盒量化"人有没有真的变矮变宽"。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from PIL import Image

import main as main_mod

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "_matting")


def bbox(path):
    im = Image.open(path).convert("RGBA")
    a = im.getchannel("A")
    return a.getbbox(), im.size


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    pet = ctl.pet
    pet.show()

    def step1():
        pet.grab().save(os.path.join(OUT, "v299-idle.png"))
        pet.do_sleep()
        QTimer.singleShot(4000, step2)

    def step2():
        pet.grab().save(os.path.join(OUT, "v299-sleep-final.png"))
        for name in ("v299-idle.png", "v299-sleep-final.png"):
            bb, size = bbox(os.path.join(OUT, name))
            if bb:
                print(name, "canvas=%dx%d" % size,
                      "body=%dx%d" % (bb[2] - bb[0], bb[3] - bb[1]),
                      "top=%d bottom=%d" % (bb[1], bb[3]))
            else:
                print(name, "empty")
        app.quit()

    QTimer.singleShot(1500, step1)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
