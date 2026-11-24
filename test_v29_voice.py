# -*- coding: utf-8 -*-
"""v2.9.2 真人音色提炼自检：真实拉起 Controller，验证配置落盘、音色档位切换、
以及按档位算出的 pitch 能否真的合成出对应基频的音频。

    .venv/Scripts/python.exe test_v29_voice.py
"""
import os
import subprocess
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import numpy as np
from PySide6.QtWidgets import QApplication

import main as m
import persona as pers
import tts
import voice_profile as vp

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


def f0_of(path):
    w = wave.open(path, "rb")
    sr, n = w.getframerate(), w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    w.close()
    fl, hop = int(0.04 * sr), int(0.01 * sr)
    rms, frames = [], []
    for i in range(0, len(x) - fl, hop):
        f = x[i:i + fl]
        f = f - f.mean()
        frames.append(f)
        rms.append(float(np.sqrt((f ** 2).mean())))
    db = 20 * np.log10(np.array(rms) + 1e-9)
    thr = np.percentile(db, 60)
    vals = []
    for i, d in enumerate(db):
        if d <= thr:
            continue
        f = frames[i]
        ac = np.correlate(f, f, "full")[fl - 1:]
        ac = ac / (ac[0] + 1e-9)
        lo, hi = int(sr / 500), min(int(sr / 70), len(ac) - 1)
        seg = ac[lo:hi]
        k = int(np.argmax(seg)) + lo
        if seg.max() > 0.35:
            vals.append(sr / k)
    return round(float(np.median(vals)), 1) if vals else 0.0


print("== 1. 映射表 ==")
check("两个档位都在", len(vp.profile_names()) >= 2, str(vp.profile_names()))
nom, goal, reach = vp.pitch_for("zh-CN-XiaoxiaoNeural", "linluo")
check("linluo 对 Xiaoxiao 给出 pitch", nom == 27, f"nominal={nom} goal={goal}")
nom2, goal2, reach2 = vp.pitch_for("zh-CN-XiaoxiaoNeural", "jingjing")
check("jingjing 足够接近上限且不越界", nom2 <= 70 and goal2 <= 355.6, f"nominal={nom2} goal={goal2}")

print("== 2. Controller 配置 ==")
app = QApplication([])
ctl = m.Controller(app)
check("档位是合法值", ctl.config.get("voice_profile") in {"linluo", "jingjing", "off"},
      str(ctl.config.get("voice_profile")))
ctl.set_voice_profile("jingjing")
check("切换档位后 config 生效", ctl.config.get("voice_profile") == "jingjing")
pkey = ctl.config.get("persona", pers.DEFAULT_PERSONA)
voice = (pers.PERSONAS.get(pkey) or {}).get("voice")
print("   persona:", pkey, "voice:", voice)

print("== 3. 真合成 + 回采基频 ==")
text = "鱼片，你认真干活的样子，勉勉强强过得去啦。"
prof = ctl.config.get("voice_profile")
delta, goal3, _ = vp.pitch_for(voice, prof)
base_pitch = int((pers.PERSONAS.get(pkey) or {}).get("pitch", 0))
final_pitch = max(-120, min(120, delta))   # 档位模式：pitch 由映射表反解，覆盖人设 pitch
print(f"   base_pitch={base_pitch} profile_delta={delta} final={final_pitch}")
path = tts.synth(text, voice, 0, final_pitch)
check("合成文件落地", os.path.exists(path) and os.path.getsize(path) > 2000, path)

ff = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  ".venv", "Lib", "site-packages", "imageio_ffmpeg", "binaries")
wav16 = os.path.join(os.path.dirname(path), "_verify_16k.wav")
ffex = ""
for n in os.listdir(ff) if os.path.isdir(ff) else []:
    if n.startswith("ffmpeg") and n.endswith(".exe"):
        ffex = os.path.join(ff, n)
if ffex:
    subprocess.run([ffex, "-y", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", "16000", wav16],
                   check=False)
    measured = f0_of(wav16)
    base_f0 = vp.BASE_F0.get(voice, 250.0)
    expect = base_f0 + delta * vp.SLOPE.get(voice, 1.7)
    # 曲线是 45 字长句标定的；短句句末上扬会把中位抬 10~15Hz，所以容差取 20Hz
    ok = abs(measured - expect) <= 20
    check("实测基频落在预期带内", ok, f"measured={measured} expect≈{round(expect,1)}")
    print(f"   参考真源 {vp.get_profile(prof)['f0']}Hz -> 现在 {measured}Hz")
else:
    print("   跳过：没找到 ffmpeg")

print("== 4. 关掉档位 ==")
ctl.set_voice_profile("off")
check("off 生效", ctl.config.get("voice_profile") == "off")
ctl.set_voice_profile("linluo")   # 测试结束恢复默认，别把用户配置留在 off
check("恢复默认 linluo", ctl.config.get("voice_profile") == "linluo")

print()
print("结果:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
ctl.quit_app()
sys.exit(0 if not FAIL else 1)
