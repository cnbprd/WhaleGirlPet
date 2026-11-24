# -*- coding: utf-8 -*-
"""验收：动作音效是否跟着语音人格走。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402
import persona as pers  # noqa: E402

ctl = Controller(app)
a = ctl.audio
print("动作数:", len(ctl.config["audio"].get("mappings", {})))
for key in pers.PERSONAS:
    p = os.path.join(os.path.dirname(a.action_path("pat") or ""), f"sfx_pat_{key}.mp3") \
        if a.action_path("pat") else ""
    cnt = sum(1 for f in os.listdir(os.path.dirname(p)) if f.startswith("sfx_") and f.endswith(f"_{key}.mp3")) \
        if p else 0
    print(f"  {key:16s} 人格音效 {cnt:2d} 条")

for key in ("sichuan_sweet", "korean_green", "hk_lady"):
    ctl.config["persona"] = key
    print(key, "->", os.path.basename(a.action_path("pat")))
print("play:", a.play("pat"), "| persona =", ctl.config["persona"])
ctl.quit_app()
