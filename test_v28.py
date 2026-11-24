# -*- coding: utf-8 -*-
"""v2.8 验收：语音优先级 / 自主权重表 / 夜间池 / 脚底对齐 / 频繁戳抗议。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from main import Controller  # noqa: E402
import paths  # noqa: E402

ctl = Controller(app)

# 1) 权重表：心情分档
for mood in (20, 60, 90):
    ctl.state.mood = mood
    w = ctl.auto_weights()
    print("mood", mood, "->", w, "sum", sum(w.values()))

# 2) 夜间池：把夜间窗口设成覆盖当前小时
h = time.localtime().tm_hour
ctl.config.setdefault("schedule", {})["night_range"] = [h, (h + 1) % 24]
print("is_night", ctl.is_night(), "->", ctl.auto_weights())
ctl.config["schedule"]["night_range"] = [23, 7]
print("is_night(restore)", ctl.is_night())

# 3) 语音优先级抢断
sfx = os.path.join(paths.voice_dir(), "sfx_pat.mp3")
sfx2 = os.path.join(paths.voice_dir(), "sfx_feed.mp3")
print("audio files", os.path.exists(sfx), os.path.exists(sfx2))
ok_hi = ctl.audio.play_file(sfx, 2)
time.sleep(0.4)
playing = ctl.audio.player.isPlaying()
low = ctl.audio.play_file(sfx2, 0)
high = ctl.audio.play_file(sfx2, 3)
print(f"play hi(2)={ok_hi} isPlaying={playing} low(0)={low} high(3)={high} prio={ctl.audio._prio}")

# 4) 脚底对齐：各皮肤裁剪前后的高度
ctrl_w = ctl.pet
for skin in paths.SKINS:
    ctrl_w._controller.config["skin"] = skin
    base = ctrl_w._load_skin(skin)
    foot = ctrl_w._foot_row(base)
    print(f"skin {skin:10s} {base.width()}x{base.height()} foot={foot} crop={base.height()-foot}px")

# 5) 频繁戳：1 秒 7 次触发抗议，不涨好感
ctrl_w._controller.config["skin"] = "default"
ctl.state.mood = 60
pat_before = float(getattr(ctl.state, "mood", 60))
for _ in range(7):
    ctl.on_pat()
print("after 7 pats, mood:", ctl.state.mood, "was", pat_before, "bubble:", ctrl_w.bubble.text_label.text() if hasattr(ctrl_w.bubble, "text_label") else "?")
ctl.quit_app()
