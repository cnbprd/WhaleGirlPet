# -*- coding: utf-8 -*-
"""本地音频播放：QMediaPlayer 播放导入的动作音效，音量/静音由配置控制；无音频文件时回退蜂鸣。

音量语义（v2.4 修正）：界面上的 0–100 是"相对系统音量的百分比"。
  QAudioOutput.setVolume 只吃 0.0–1.0，过去直接把 80 传进去等于永远满音量，
  这就是"调小声没用、和系统音量不同步"的原因。现在按 (程序音量% × 系统主音量) 计算。
"""
import json
import math
import os
import shutil
import struct

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat, QAudioOutput, QMediaPlayer

import sysvol
from paths import voice_dir

AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma")


class AudioManager(QObject):
    speechStarted = Signal()
    speechFinished = Signal()

    def __init__(self, config: dict):
        super().__init__()
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
        # v3.0.25：TTS 播放时解出 RMS 包络，给桌宠做伪口型
        self._speech = False
        self._env = []
        self._env_ms = 24.0
        self._decoder = None
        self._apply_volume()

    def _on_play_state(self, st):
        """播完/停下时把优先级归零，别让上一句的高优先级一直压着。"""
        if st != QMediaPlayer.PlayingState:
            self._prio = 0
            if self._speech:
                self._speech = False
                self.speechFinished.emit()

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

    def play_file(self, path: str, priority: int = 0, volume: int = None,
                  speech: bool = False) -> bool:
        """直接播放任意本地音频文件（TTS 合成结果走这里）。priority 越大越优先。

        volume：0–100，给值时按它单独设定这次播放的音量（音色试听/自定义音色用）；
        不给就按全局「音频设置」的音量。
        speech=True 时额外解码音量包络，供桌宠做说话口型；音效预览不传。
        """
        if not self.is_enabled() or not path or not os.path.exists(path):
            return False
        if self._busy_with_higher(priority):
            return False
        try:
            if volume is None:
                self._apply_volume()
            else:
                base = max(0.0, min(100.0, float(volume))) / 100.0
                if self.config["audio"].get("follow_system", True):
                    base *= sysvol.master_volume()
                self.output.setVolume(max(0.0, min(1.0, base)))
            self._prio = priority
            self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.setPosition(0)
            self.player.play()
            if speech:
                self._begin_envelope(path)
                self.speechStarted.emit()
            else:
                self._clear_envelope()
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
            self._clear_envelope()
            return True
        except Exception:
            return False

    # ---------- TTS 音量包络（伪口型） ----------
    def _clear_envelope(self):
        self._speech = False
        self._env = []
        if self._decoder is not None:
            try:
                self._decoder.stop()
                self._decoder.deleteLater()
            except Exception:
                pass
            self._decoder = None

    def _begin_envelope(self, path: str):
        """优先读 .env.json 缓存；没有就用 QAudioDecoder 解一遍。"""
        self._clear_envelope()
        self._speech = True
        cache = path + ".env.json"
        try:
            if os.path.exists(cache):
                with open(cache, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("rms"), list) and data["rms"]:
                    self._env = [float(x) for x in data["rms"]]
                    self._env_ms = float(data.get("ms", 24.0)) or 24.0
                    return
        except Exception:
            self._env = []
        try:
            dec = QAudioDecoder(self)
            dec.setSource(QUrl.fromLocalFile(path))
            dec.bufferReady.connect(lambda: self._read_decode_buffer(dec))
            dec.finished.connect(lambda: self._finish_decode(dec, cache))
            dec.error.connect(lambda *_: self._finish_decode(dec, cache))
            self._decoder = dec
            dec.start()
        except Exception:
            self._decoder = None

    def _read_decode_buffer(self, dec):
        try:
            while dec.bufferAvailable():
                buf = dec.read()
                if not buf.isValid():
                    continue
                fmt = buf.format()
                if fmt.sampleFormat() != QAudioFormat.SampleFormat.Float:
                    continue
                raw = buf.data()
                n = len(raw) // 4
                if n <= 0:
                    continue
                vals = struct.unpack("<%df" % n, raw.tobytes())
                rms = math.sqrt(sum(v * v for v in vals) / n)
                self._env.append(float(rms))
                self._env_ms = max(1.0, buf.duration() / 1000.0)
        except Exception:
            pass

    def _finish_decode(self, dec, cache: str):
        try:
            if dec is self._decoder:
                self._decoder = None
            dec.deleteLater()
        except Exception:
            pass
        if not self._env:
            return
        try:
            with open(cache, "w", encoding="utf-8") as f:
                json.dump({"ms": self._env_ms, "rms": self._env}, f)
        except Exception:
            pass

    def speech_level(self) -> float:
        """0..1 的说话强度；只在 TTS 播放且有包络时有效。"""
        if not self._speech or not self._env or not self.player.isPlaying():
            return 0.0
        try:
            idx = int(self.player.position() / self._env_ms)
        except Exception:
            return 0.0
        if idx < 0 or idx >= len(self._env):
            return 0.0
        # TTS 实测 RMS：静音 0、正常 0.07、爆破 0.22；0.16 作为满幅
        return max(0.0, min(1.0, (self._env[idx] - 0.012) / 0.16))


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
