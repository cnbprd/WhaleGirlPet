# -*- coding: utf-8 -*-
"""v2.8 语音抢断逻辑单测：用假播放器，绕开没有音频设备的问题。"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
import paths  # noqa: E402
from audio_manager import AudioManager  # noqa: E402


class FakePlayer:
    def __init__(self):
        self.playing = False
        self.src = ""

    def isPlaying(self):
        return self.playing

    def stop(self):
        self.playing = False

    def setSource(self, url):
        self.src = url.toString()

    def setPosition(self, pos):
        pass

    def play(self):
        self.playing = True

    def setAudioOutput(self, out):
        pass


cfg = {"audio": {"on": True, "volume": 80, "follow_system": False, "mappings": {}}}
am = AudioManager(cfg)
am.player = FakePlayer()

VD = os.path.join(os.environ["APPDATA"], "WhaleGirlPet", "accounts", "default", "voices")
sfx = os.path.join(VD, "sfx_pat.mp3")
sfx2 = os.path.join(VD, "sfx_feed.mp3")
print("voices", VD)
print("exists", os.path.exists(sfx), os.path.exists(sfx2), "enabled", am.is_enabled())

r1 = am.play_file(sfx, 2)          # 起播高优先级
print("play hi=2 ->", r1, "prio", am._prio, "playing", am.player.isPlaying())
r2 = am.play_file(sfx2, 0)         # 低优先级，应被拒
print("play lo=0 ->", r2, "(期望 False)")
r3 = am.play_file(sfx2, 3)         # 更高优先级，应抢断
print("play hi=3 ->", r3, "(期望 True) prio", am._prio)
am.player.playing = False
am._on_play_state(0)               # 模拟播完
print("after finish prio", am._prio, "(期望 0)")
r4 = am.play_file(sfx2, 0)
print("play lo=0 after finish ->", r4, "(期望 True)")
