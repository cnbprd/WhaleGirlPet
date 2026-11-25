# -*- coding: utf-8 -*-
"""第 9/10 条：启动屏动画帧率与重拍。

- 帧率：真实 3 秒内 QTimer 实际触发次数（目标 40fps 左右）
- 单帧绘制成本：render 到 QImage 120 次取均值
- 重拍：docs/splash_v322.png（w 380×580 透明底，人可见）
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import splash as splash_mod  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def main():
    app = QApplication(sys.argv)
    sp = splash_mod.LoadingSplash()
    sp._fade = 1.0
    sp.show()
    app.processEvents()

    ticks = []
    orig = sp._tick

    def counted():
        ticks.append(time.time())
        orig()

    sp._tm.timeout.disconnect()
    sp._tm.timeout.connect(counted)

    def measure_fps():
        el = ticks[-1] - ticks[0] if len(ticks) > 1 else 0
        fps = (len(ticks) - 1) / el if el else 0
        gaps = [(b - a) * 1000 for a, b in zip(ticks, ticks[1:])]
        ck("3 秒内 tick 数", len(ticks) >= 100, f"{len(ticks)} 次｜{fps:.1f} fps")
        if gaps:
            gaps_sorted = sorted(gaps)
            p95 = gaps_sorted[int(len(gaps_sorted) * 0.95)]
            ck("帧间隔 p95", p95 <= 45, f"p95 {p95:.1f}ms｜max {max(gaps):.1f}ms")

        img = QImage(sp.width(), sp.height(), QImage.Format_ARGB32_Premultiplied)
        t0 = time.perf_counter()
        for _ in range(120):
            img.fill(0)
            p = QPainter(img)
            sp.paintEvent(None)
            p.end()
        ms = (time.perf_counter() - t0) * 1000 / 120
        ck("单帧绘制成本", ms < 12, f"{ms:.2f}ms/帧（{1000 / ms:.0f} fps 上限）")

        pix = sp.grab()
        out = os.path.join(ROOT, "docs", "splash_v322.png")
        ok = pix.save(out)
        ck("重拍落盘", ok and os.path.getsize(out) > 10000,
           f"{os.path.getsize(out) / 1024:.0f}KB {pix.width()}×{pix.height()}")

        bad = [x for x in R if not x[1]]
        print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed｜截图 docs/splash_v322.png")
        sp._hard_close()
        QTimer.singleShot(200, app.quit)

    QTimer.singleShot(3000, measure_fps)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
