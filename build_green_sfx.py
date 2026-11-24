# -*- coding: utf-8 -*-
"""按两条抖音视频里提炼的说话方式，重做「绿茶」人格的动作音效。

提炼依据（均来自视频 ASR，非猜测）：
  视频一 7.9s：反复「能不能……」「能不能 man 一点」「咕咕嘎嘎的表情包」——短句连发、尾音上扬、撒娇里带挑衅。
  视频二 15.2s：「人生几十年，总会有风雨来陪……慢慢去体会，此刻人生这杯酒最珍贵」——拖长音、放慢、抒情。
用法：python build_green_sfx.py
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))

import paths  # noqa: E402
import tts  # noqa: E402

paths.set_active_account("default")
PERSONA = "korean_green"
VOICE = "ko-KR-SunHiNeural"   # 与 persona.py 里该人格的 voice 保持一致

# 活泼组：短视频一的口气（快、上扬、撒娇式挑刺）
LIVE = {
    "pat": "能不能别一直摸人家头呀，人家会害羞的嘛～",
    "feed": "能不能投喂点好吃的呀？人家不要咕咕嘎嘎的东西～",
    "happy": "嘿嘿，你今天表现还不错嘛，人家有点开心了哦",
    "angry": "你们这些小男生能不能 man 一点呀，人家真的很无语呢",
    "shy": "能不能别这样看人家呀，人家会不好意思的嘛",
    "coin": "金币到账啦，人家可都记着呢，不许赖账哦",
    "done": "搞定啦，人家是不是很厉害呀，夸一句嘛",
    "water": "该喝水啦，能不能乖乖听话一次呀",
    "sedentary": "起来动一动呀，坐那么久人家会心疼的哦",
    "walk": "走啦走啦，人家陪你去看看嘛",
    "wake": "早呀，睡这么久，人家都等你了呢",
    "wave": "你好呀，人家一直在等你说话呢",
    "dance": "跳舞咯，人家心情好才跳给你看哦",
    "change": "换好啦，能不能说一句好看呀",
    "clean": "打扫干净啦，人家做的事你可要看见哦",
    "wipe": "擦得锃亮，人家手都酸了呢",
    "chore": "家务搞定，能不能夸人家一句嘛",
    "panic": "啊啊啊救命，人家真的会怕的呀",
    "error": "咦出错了，不是人家的错哦，你别误会嘛",
}
# 抒情组：短视频二的口气（慢、拖长音），放在安静动作上
SOFT = {
    "sleep": "晚安啦，往事后不后悔，慢慢去体会嘛……",
}

cfg_path = os.path.join(paths.account_dir(), "config.json")
with open(cfg_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
out_dir = paths.voice_dir()
made, failed = 0, []

for act, text in list(LIVE.items()) + list(SOFT.items()):
    soft = act in SOFT
    try:
        src = tts.synth(text, VOICE, rate=(-10 if soft else 10), pitch=(4 if soft else 12))
        if not src or not os.path.exists(src):
            failed.append((act, "empty"))
            continue
        dst = os.path.join(out_dir, f"sfx_{act}_{PERSONA}.mp3")
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
        made += 1
        print(f"{act}: {os.path.getsize(dst)//1024} KB  <- {text}")
    except Exception as e:  # noqa: BLE001
        failed.append((act, str(e)[:70]))

print(f"done: {made} 条绿茶人格音效，失败 {len(failed)}")
for it in failed:
    print("  fail", it)
