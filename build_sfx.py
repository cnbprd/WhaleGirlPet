# -*- coding: utf-8 -*-
"""批量生成动作音效，并按语音人格分版本。

- 不带参数：给「当前人格」生成 sfx_<action>_<persona>.mp3，同时补一份通用 sfx_<action>.mp3（回退用）
- `--all`：8 个人格全生成一遍（每人格用自己的 voice / rate / pitch + 方言化台词）
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))

import paths  # noqa: E402
import persona as pers  # noqa: E402
import tts  # noqa: E402

paths.set_active_account("default")

LINES = {
    "pat": "摸摸头，好舒服",
    "feed": "谢谢投喂，好吃",
    "happy": "嘿嘿，开心",
    "angry": "哼，生气了",
    "shy": "别、别这样啦",
    "coin": "金币到账",
    "done": "搞定啦",
    "water": "该喝水啦",
    "sedentary": "起来动一动",
    "walk": "走啦走啦",
    "sleep": "晚安",
    "wake": "早啊",
    "wave": "你好呀",
    "dance": "跳舞咯",
    "change": "换好啦",
    "clean": "打扫干净了",
    "wipe": "擦得锃亮",
    "chore": "家务搞定",
    "panic": "啊啊啊救命",
    "error": "咦，出错了",
}

cfg_path = os.path.join(paths.account_dir(), "config.json")
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
maps = cfg.setdefault("audio", {}).setdefault("mappings", {})
out_dir = paths.voice_dir()
os.makedirs(out_dir, exist_ok=True)

ALL = "--all" in sys.argv
cur = str(cfg.get("persona", pers.DEFAULT_PERSONA) or pers.DEFAULT_PERSONA)
targets = list(pers.PERSONAS.keys()) if ALL else [cur]

made, failed = 0, []
for key in targets:
    p = pers.get(key)
    voice = p.get("voice", "zh-CN-XiaoyiNeural")
    rate = int(p.get("rate", 0))
    pitch = int(p.get("pitch", 0))
    for act, text in LINES.items():
        try:
            say = pers.dialectize(text, key)
            src = tts.synth(say, voice, rate=rate, pitch=pitch)
            if not src or not os.path.exists(src):
                failed.append((key, act, "synth empty"))
                continue
            dst = os.path.join(out_dir, f"sfx_{act}_{key}.mp3")
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
            made += 1
            print(f"{key}/{act}: {os.path.getsize(dst)//1024} KB  <- {say}")
        except Exception as e:  # noqa: BLE001
            failed.append((key, act, str(e)[:70]))

# 通用回退版本：只在缺文件时补一份（用当前人格的音色），不覆盖已有的
if not ALL:
    p = pers.get(cur)
    for act, text in LINES.items():
        dst = os.path.join(out_dir, f"sfx_{act}.mp3")
        if os.path.exists(dst):
            continue
        try:
            src = tts.synth(pers.dialectize(text, cur), p.get("voice"), p.get("rate", 0), p.get("pitch", 0))
            if src and os.path.exists(src):
                shutil.copyfile(src, dst)
                maps[act] = dst
        except Exception:  # noqa: BLE001
            pass

with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print(f"done: {made} 条人格音效，失败 {len(failed)}")
for item in failed[:10]:
    print("  fail", item)
