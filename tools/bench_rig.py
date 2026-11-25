# -*- coding: utf-8 -*-
"""测网格蒙皮单帧耗时：不同网格分辨率 × 不同外扩，看能不能扛住 30fps。"""
import os
import sys
import time
sys.path.insert(0, r"F:\WhaleGirlPet\app")
sys.path.insert(0, r"F:\WhaleGirlPet\tools")
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
import proto_mesh as pm  # noqa: E402

for gx, gy in ((8, 20), (10, 26), (14, 32)):
    pm.GX, pm.GY = gx, gy
    pm.render(0, 12)                      # 预热
    t0 = time.perf_counter()
    N = 30
    for i in range(N):
        pm.render(0, 10 + (i % 5))
    dt = (time.perf_counter() - t0) / N
    print(f"网格 {gx}x{gy}  单帧 {dt * 1000:.1f} ms  理论帧率 {1 / dt:.0f} fps")
