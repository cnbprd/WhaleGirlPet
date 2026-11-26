# -*- coding: utf-8 -*-
"""ASR 输入层（v3.2 最后一项）

默认关闭：构造后不录音；只有显式 `arm_once()` / `set_enabled(True)` 后
`listen()` 才会创建 SAPI `VoiceWorker`。一次识别结束自动回到关闭态，
不做常驻监听。

后端仍是 `voice_cmd.py` 的 Windows 离线 SAPI，不引入外部模型，也不上传音频。
识别结果只作为文本事件交给 `main._on_voice()`，不直接碰 3D 渲染。
"""
from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

import voice_cmd


class AsrService(QObject):
    result_ready = Signal(dict)   # 成功/失败都发；失败 text 为空，reason 有值
    text_ready = Signal(dict)     # 仅成功文本
    state_changed = Signal(bool)  # True=正在听 / False=关闭

    def __init__(self, parent=None, backend: Any = None):
        super().__init__(parent)
        self._backend = backend or voice_cmd
        self._enabled = False
        self._worker = None
        self.last_result = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def worker(self):
        return self._worker

    def is_listening(self) -> bool:
        return bool(self._worker is not None and self._worker.isRunning())

    def set_enabled(self, on: bool):
        """显式开关；关闭时只影响下一次 listen，不伪造录音。"""
        self._enabled = bool(on)
        self.state_changed.emit(self._enabled)

    def arm_once(self):
        """按钮/热键按下时调用：只给下一次 listen 开门。"""
        self.set_enabled(True)

    def listen(self, wait_s: int = 4, timeout_s: int = 14) -> dict:
        """启动后台一句识别；默认关闭时直接返回 disabled，不创建 worker。"""
        if not self._enabled:
            return {"started": False, "ok": False, "text": "", "conf": 0.0,
                    "reason": "disabled"}
        if self.is_listening():
            return {"started": False, "ok": False, "text": "", "conf": 0.0,
                    "reason": "busy"}
        try:
            self._worker = self._backend.VoiceWorker(
                wait_s=wait_s, timeout_s=timeout_s)
            self._worker.done.connect(self._on_done)
            self._worker.start()
        except Exception as e:  # noqa: BLE001
            self._worker = None
            self._enabled = False
            res = {"ok": False, "text": "", "conf": 0.0,
                   "reason": f"spawn:{str(e)[:80]}"}
            self._emit(res)
            return {"started": False, **res}
        return {"started": True, "ok": True, "text": "", "conf": 0.0, "reason": ""}

    def recognize_file(self, wav_path: str, wait_s: int = 1,
                       timeout_s: int = 20) -> dict:
        """同步识别 WAV，供验收/自测；也必须先显式开启。"""
        if not self._enabled:
            return {"ok": False, "text": "", "conf": 0.0, "reason": "disabled"}
        try:
            res = self._backend.recognize(
                wav_path=wav_path, wait_s=wait_s, timeout_s=timeout_s)
        except Exception as e:  # noqa: BLE001
            res = {"ok": False, "text": "", "conf": 0.0, "reason": f"spawn:{e}"}
        self._emit(res, close=True)
        return res

    def _emit(self, res: dict, close: bool = True):
        self.last_result = dict(res or {})
        if close:
            self._enabled = False
            self.state_changed.emit(False)
        self.result_ready.emit(self.last_result)
        if self.last_result.get("ok") and self.last_result.get("text"):
            self.text_ready.emit(self.last_result)

    def _on_done(self, res: dict):
        self._worker = None
        self._emit(res, close=True)
