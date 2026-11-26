# -*- coding: utf-8 -*-
"""ASR 输入层验收：默认零采集、SAPI 真音频转写、失败不造假、服务状态收口。

    python tools/test_asr.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QCoreApplication, QObject, Signal

import asr_service
import emotion_bridge as eb
import voice_cmd

WAV = os.path.join(ROOT, "build", "asr_accept.wav")
WAV2 = os.path.join(ROOT, "build", "asr_emotion.wav")
PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def make_wav(path: str, phrase: str = "打开面板"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    script = (
        '$ErrorActionPreference="Stop";'
        'Add-Type -AssemblyName System.Speech;'
        '$sp=New-Object System.Speech.Synthesis.SpeechSynthesizer;'
        f'$sp.SetOutputToWaveFile("{path}");'
        f'$sp.Speak("{phrase}");$sp.Dispose();Write-Output "WAV_OK"'
    )
    subprocess.run([PS, "-NoProfile", "-NonInteractive", "-Command", script],
                   check=True, timeout=30, creationflags=0x08000000)
    assert os.path.getsize(path) > 1024, "WAV fixture too small"


class FakeWorker(QObject):
    done = Signal(dict)
    instances = 0

    def __init__(self, **kwargs):
        super().__init__()
        type(self).instances += 1

    def start(self):
        return None

    def isRunning(self):
        return False


class FakeBackend:
    VoiceWorker = FakeWorker

    @staticmethod
    def recognize(wav_path="", wait_s=1, timeout_s=20):
        return {"ok": True, "text": "打开面板", "conf": 0.5, "reason": ""}


app = QCoreApplication([])

# 1) 默认关闭：连 worker 都不创建
svc = asr_service.AsrService(backend=FakeBackend)
assert not svc.enabled
assert FakeWorker.instances == 0
gate = svc.listen()
assert gate["started"] is False and gate["reason"] == "disabled", gate
assert FakeWorker.instances == 0, "disabled ASR created a worker"
assert svc.recognize_file("whatever.wav")["reason"] == "disabled"

# 2) 显式开启后才创建 worker
svc.set_enabled(True)
started = svc.listen()
assert started["started"] is True, started
assert FakeWorker.instances == 1, "enabled ASR did not create worker"

# 3) 成功结果经 result_ready/text_ready 发出；文件识别后自动关闭
seen, texts = [], []
svc.result_ready.connect(lambda d: seen.append(d))
svc.text_ready.connect(lambda d: texts.append(d))
svc.set_enabled(True)
res = svc.recognize_file("fake.wav")
assert res["ok"] and res["text"] == "打开面板", res
assert seen and seen[-1]["text"] == "打开面板"
assert texts and texts[-1]["text"] == "打开面板"
assert svc.enabled is False, "ASR did not close after one shot"

# 4) 真音频：SAPI 合成一句，再用 SAPI 识别回来
make_wav(WAV)
real = voice_cmd.recognize(wav_path=WAV, wait_s=1, timeout_s=20)
print("real_asr", real)
assert real["ok"] is True, real
assert real["text"], "recognized empty text"
assert "打开" in real["text"], real

# 5) 无语音：不产生假文本
no_speech = voice_cmd.recognize(wav_path="", wait_s=1, timeout_s=2)
print("no_speech", no_speech)
assert no_speech["ok"] is False, no_speech
assert no_speech["text"] == "", no_speech
assert no_speech["reason"] in ("no_speech", "no_mic", "timeout", "low_conf"), no_speech

# 6) ASR 文本 -> 情绪桥：证明识别结果能进入 3D 表情事件，而不是只停在字符串
make_wav(WAV2, "别难过，笑一个")
emo_text = voice_cmd.recognize(wav_path=WAV2, wait_s=1, timeout_s=20)
print("emotion_asr", emo_text)
assert emo_text["ok"] and emo_text["text"], emo_text
bridge = eb.EmotionBridge(enabled=True)
bridge.sender.enabled = False
try:
    sig = bridge.user_text(emo_text["text"])
    assert sig is not None, emo_text
    assert sig.emotion == "happy", sig
    assert sig.source == "P_USER", sig
    print("emotion_sig", sig)
finally:
    bridge.close()

print("asr_ok real_text=%r conf=%s no_speech_reason=%s emotion=%s" %
      (real["text"], real["conf"], no_speech["reason"], sig.emotion))
app.quit()
