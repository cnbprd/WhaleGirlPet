# -*- coding: utf-8 -*-
"""端到端：方言 TTS 合成落盘 + 本地 Qwen3 推理一次。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
import accounts  # noqa: E402

accounts.init_store()

import local_llm  # noqa: E402
import persona  # noqa: E402
from tts import cache_dir, synth  # noqa: E402

p = persona.get("sichuan_sweet")
text = persona.dialectize("鱼片，今天也要好好吃饭哦，莫要熬夜。", "sichuan_sweet")
res = synth(text, p["voice"], p["rate"], p["pitch"])
print("tts text:", text)
print("tts result type:", type(res).__name__, "->", res)
if isinstance(res, str) and os.path.exists(res):
    print("tts file size:", os.path.getsize(res), "bytes")
print("cache dir:", cache_dir())

mgr = local_llm.ServerManager({"llm_port": 8085})
print("server exe:", local_llm.server_exe(), "| available:", local_llm.available())
t0 = time.time()
started = mgr.start()
print("server started:", started, "in %.1fs" % (time.time() - t0), "| err:", mgr.last_error)
if started:
    msgs = [{"role": "system",
             "content": p["system"] + "\n你是桌宠，回答要短。\n/no_think"},
            {"role": "user", "content": "用一句话跟我说句晚安"}]
    t1 = time.time()
    ok, out = mgr.chat(msgs, 120, 0.8)
    print("chat ok:", ok, "%.1fs" % (time.time() - t1))
    print("reply:", out[:160])
mgr.stop()
print("DONE")
