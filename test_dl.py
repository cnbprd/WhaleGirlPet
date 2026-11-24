# -*- coding: utf-8 -*-
"""下载器实网短测：跑 7 秒后取消，验证流式写入 .part 与保留续传。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

app = QCoreApplication(sys.argv)

import model_dl  # noqa: E402
import models_catalog  # noqa: E402
import paths  # noqa: E402

it = models_catalog.by_id("deepseek-1.5b")
dest = os.path.join(paths.runtime_dir(), "models", "_probe.gguf")
part = dest + ".part"
for p in (dest, part):
    if os.path.exists(p):
        os.remove(p)

w = model_dl.ModelDownloader(it["id"], it["url"], dest)
state = {"got": 0, "total": 0, "msg": ""}
w.progress.connect(lambda i, g, t: state.update(got=g, total=t))
w.failed.connect(lambda i, why: state.update(msg=why))
w.start()


def finish():
    size = os.path.getsize(part) if os.path.exists(part) else 0
    print(f"progress got={state['got']} total={state['total']} part={size} msg={state['msg']}")
    print("speed MB/s:", round(w.speed, 2))
    if os.path.exists(part):
        os.remove(part)
    print("PROBE OK")
    app.quit()


QTimer.singleShot(7000, lambda: (w.stop(), QTimer.singleShot(1500, finish)))
app.exec()
