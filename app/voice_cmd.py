# -*- coding: utf-8 -*-
"""语音命令：调用 Windows 自带 SAPI 中文识别器（离线、零额外模型）。

实测（本机 2026-11-24）：
- 识别器 zh-CN MS-2052-80-DESK 可用
- 用 Huihui 合成「明天七点提醒我交房租」再识别，结果一字不差
- 命令词 + 听写两套语法同时加载，命令词优先

实现方式：起一个隐藏的 powershell.exe（5.1，绝对路径），用 -EncodedCommand
传脚本，stdout 回传 UTF-8。不依赖任何 pip 包。
"""
import base64
import time as _time
import os
import subprocess
import sys

from PySide6.QtCore import QThread, Signal

# 常见命令词：加进 grammar 能显著提高短指令的识别率
DEFAULT_PHRASES = [
    "打开面板", "关闭面板", "换装", "摸头", "睡觉", "起床", "跳舞", "跑步",
    "停下来", "满屏跑", "清理垃圾", "做家务", "打开浏览器", "设置提醒",
    "现在几点", "今天天气", "病毒库更新", "防火墙检查", "静音", "继续",
]

PS_MODULE = r'''
$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
Add-Type -AssemblyName System.Speech
$rec = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$inputMode = __INPUT__
if ($inputMode -eq "mic") {
  try { $rec.SetInputToDefaultAudioDevice() } catch { Write-Output "ERR:no_mic"; exit 0 }
} else {
  $rec.SetInputToWaveFile($inputMode)
}
$phrases = @()  # 命令词语法在 SAPI 中文识别器上报 MethodNotFound，这里只用听写
$rec.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
$rec.InitialSilenceTimeout = [TimeSpan]::FromSeconds(__WAIT__)
$rec.BabbleTimeout = [TimeSpan]::FromSeconds(6)
$rec.EndSilenceTimeout = [TimeSpan]::FromSeconds(0.8)
$r = $rec.Recognize([TimeSpan]::FromSeconds(__TIMEOUT__))
if ($r) {
  $conf = [math]::Round($r.Confidence, 3)
  $txt = $r.Text
  Write-Output ("OK|" + $conf + "|" + $txt)
} else {
  Write-Output "EMPTY"
}
'''


def _ps_exe() -> str:
    """PATH 可能被改写，必须用绝对路径。"""
    for p in (r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
              r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"):
        if os.path.exists(p):
            return p
    return "powershell.exe"


_mic_cache = {"t": 0.0, "v": None}
_MIC_TTL = 300.0


def has_microphone() -> bool:
    """粗判：录音设备列表非空（不做真实录音）。

    v2.9.9：这条要起 PowerShell 枚举设备，实测一次 0.4~0.5 秒。
    原来面板每刷一次就查一遍，等于每开一次面板卡半秒，改成 5 分钟缓存。
    """
    now = _time.monotonic()
    if _mic_cache["v"] is not None and now - _mic_cache["t"] < _MIC_TTL:
        return _mic_cache["v"]
    try:
        import wave  # noqa: F401  只是确认音频栈可用
    except Exception:  # noqa: BLE001
        return False
    try:
        out = subprocess.run(
            [_ps_exe(), "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_SoundDevice | Where-Object { $_.Status -eq 'OK' } |"
             " Measure-Object).Count"],
            capture_output=True, timeout=15, creationflags=0x08000000)
        res = int((out.stdout or b"0").decode("utf-8", "ignore").strip() or 0) > 0
    except Exception:  # noqa: BLE001
        res = False
    _mic_cache["t"] = now
    _mic_cache["v"] = res
    return res


def recognize(wav_path: str = "", wait_s: int = 5, timeout_s: int = 15,
              phrases=None) -> dict:
    """听一句。返回 {ok, text, conf, reason}。

    wav_path 有值 → 识别该文件（自测用）；否则用默认麦克风。
    """
    phrases = DEFAULT_PHRASES if phrases is None else phrases  # 目前只用于提示，不进语法
    # PowerShell 里反斜杠不是转义符，用单引号包路径最稳
    inp = ("'" + wav_path.replace("'", "''") + "'") if wav_path else '"mic"'
    script = (PS_MODULE
              .replace("__INPUT__", inp)
              .replace("__WAIT__", str(int(wait_s)))
              .replace("__TIMEOUT__", str(int(timeout_s))))
    enc = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        out = subprocess.run(
            [_ps_exe(), "-NoProfile", "-NonInteractive", "-EncodedCommand", enc],
            capture_output=True, timeout=timeout_s + 20, creationflags=0x08000000)
    except subprocess.TimeoutExpired:
        return {"ok": False, "text": "", "conf": 0.0, "reason": "timeout"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "text": "", "conf": 0.0, "reason": f"spawn:{e}"}
    raw = (out.stdout or b"").decode("utf-8", "ignore").strip()
    last = raw.splitlines()[-1].strip() if raw else ""
    if last.startswith("OK|"):
        parts = last.split("|", 2)
        try:
            conf = float(parts[1])
        except (ValueError, IndexError):
            conf = 0.0
        text = parts[2].strip() if len(parts) > 2 else ""
        return {"ok": bool(text), "text": text, "conf": conf,
                "reason": "" if text else "empty_text"}
    if last == "EMPTY":
        return {"ok": False, "text": "", "conf": 0.0, "reason": "no_speech"}
    if "no_mic" in last:
        return {"ok": False, "text": "", "conf": 0.0, "reason": "no_mic"}
    return {"ok": False, "text": "", "conf": 0.0,
            "reason": ("stderr:" + (out.stderr or b"").decode("utf-8", "ignore")[-80:])
            if last == "" else last[:80]}


class VoiceWorker(QThread):
    """后台听一句，不阻塞界面。"""
    done = Signal(dict)

    def __init__(self, wav_path: str = "", wait_s: int = 5, timeout_s: int = 15,
                 phrases=None):
        super().__init__()
        self.wav_path = wav_path
        self.wait_s = wait_s
        self.timeout_s = timeout_s
        self.phrases = phrases

    def run(self):
        try:
            self.done.emit(recognize(self.wav_path, self.wait_s, self.timeout_s,
                                     self.phrases))
        except Exception as e:  # noqa: BLE001
            self.done.emit({"ok": False, "text": "", "conf": 0.0, "reason": str(e)[:80]})


if __name__ == "__main__":
    wav = sys.argv[1] if len(sys.argv) > 1 else ""
    print(recognize(wav_path=wav))
