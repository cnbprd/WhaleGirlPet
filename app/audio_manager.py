# -*- coding: utf-8 -*-
"""本地音频播放：QMediaPlayer 播放导入的动作音效，音量/静音由配置控制；无音频文件时回退蜂鸣。

音量语义（v2.4 修正）：界面上的 0–100 是"相对系统音量的百分比"。
  QAudioOutput.setVolume 只吃 0.0–1.0，过去直接把 80 传进去等于永远满音量，
  这就是"调小声没用、和系统音量不同步"的原因。现在按 (程序音量% × 系统主音量) 计算。
"""
import os
import shutil

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

import sysvol
from paths import voice_dir

AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma")


class AudioManager:
    def __init__(self, config: dict):
        self.config = config
        audio = config.setdefault("audio", {})
        audio.setdefault("on", True)
        audio.setdefault("volume", 80)
        audio.setdefault("follow_system", True)
        audio.setdefault("mappings", {})

        self.player = QMediaPlayer()
        self.output = QAudioOutput()
        self.player.setAudioOutput(self.output)
        self._prio = 0                     # 当前正在播的语音优先级
        self.player.playbackStateChanged.connect(self._on_play_state)
        self._apply_volume()

    def _on_play_state(self, st):
        """播完/停下时把优先级归零，别让上一句的高优先级一直压着。"""
        if st != QMediaPlayer.PlayingState:
            self._prio = 0

    # ---------- 音量 ----------
    def _apply_volume(self):
        """程序音量百分比 × 系统主音量（可关），最终夹在 0..1。"""
        a = self.config["audio"]
        base = max(0, min(100, int(a.get("volume", 80)))) / 100.0
        if a.get("follow_system", True):
            base *= sysvol.master_volume()
        self.output.setVolume(max(0.0, min(1.0, base)))

    def set_follow_system(self, on: bool):
        self.config["audio"]["follow_system"] = bool(on)
        self._apply_volume()

    # ---------- 开关 / 音量 ----------
    def set_enabled(self, on: bool):
        self.config["audio"]["on"] = bool(on)
        if not on:
            self.player.stop()

    def set_volume(self, v: int):
        v = max(0, min(100, int(v)))
        self.config["audio"]["volume"] = v
        self._apply_volume()

    def is_enabled(self) -> bool:
        return bool(self.config["audio"].get("on", True))

    # ---------- 播放 ----------
    def _busy_with_higher(self, priority: int) -> bool:
        """正在播更高优先级的语音时，低优先级请求不该打断它（v2.8 语音抢断）。"""
        if not self.player.isPlaying():
            return False
        return priority < self._prio

    def play_file(self, path: str, priority: int = 0) -> bool:
        """直接播放任意本地音频文件（TTS 合成结果走这里）。priority 越大越优先。"""
        if not self.is_enabled() or not path or not os.path.exists(path):
            return False
        if self._busy_with_higher(priority):
            return False
        try:
            self._apply_volume()
            self._prio = priority
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.setPosition(0)
            self.player.play()
            return True
        except Exception:
            return False

    def _persona_sfx(self, action: str) -> str:
        """当前语音人格专属的音效（sfx_<action>_<persona>.mp3），没有就返回空。"""
        key = str(self.config.get("persona", "") or "").strip()
        if not key:
            return ""
        p = os.path.join(voice_dir(), f"sfx_{action}_{key}.mp3")
        return p if os.path.exists(p) else ""

    def play(self, action: str, priority: int = 2) -> bool:
        """播放指定动作的本地音频；成功返回 True，无文件/被关闭返回 False（由上层回退蜂鸣）。
        动作音效属于即时交互反馈，默认优先级 2，可以打断正在播的闲聊语音。"""
        if not self.is_enabled():
            return False
        path = self._persona_sfx(action) or self.config["audio"].get("mappings", {}).get(action, "")
        if not path or not os.path.exists(path):
            return False
        if self._busy_with_higher(priority):
            return False
        try:
            self._apply_volume()
            self._prio = priority
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.setPosition(0)
            self.player.play()
            return True
        except Exception:
            return False


    # ---------- 导入 / 清除 ----------
    def import_action(self, action: str, src_path: str) -> str:
        if not src_path or not os.path.exists(src_path):
            return ""
        ext = os.path.splitext(src_path)[1].lower()
        if ext not in AUDIO_EXTS:
            ext = ".mp3"
        dst = os.path.join(voice_dir(), f"{action}{ext}")
        try:
            shutil.copyfile(src_path, dst)
        except OSError:
            return ""
        self.config["audio"].setdefault("mappings", {})[action] = dst
        return dst

    def clear_action(self, action: str):
        self.config["audio"].get("mappings", {}).pop(action, None)

    def action_path(self, action: str) -> str:
        return self._persona_sfx(action) or self.config["audio"].get("mappings", {}).get(action, "")
