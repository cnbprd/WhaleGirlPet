# -*- coding: utf-8 -*-
"""脱离 Ollama 验证：强制 dafeiyu_cpp 后端，加载 runtime/models/qwen35-4b-Q4_K_M.gguf。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import local_llm  # noqa: E402

print("model_path:", local_llm.model_path())
m = local_llm.ServerManager({"llm_backend": "dafeiyu_cpp", "llm_ctx": 4096})
print("backend:", m.backend, "| port:", m.port)

t0 = time.time()
ok = m.start()
print(f"start: {ok} in {time.time()-t0:.1f}s | err: {m.last_error}")

t0 = time.time()
r1 = m.chat([{"role": "user", "content": "用一句话介绍你自己，20字以内"}],
            max_tokens=64, temperature=0.3)
print("chat:", r1[0], "|", repr(r1[1]), f"| {time.time()-t0:.1f}s")

SYS = ('只输出JSON。可用 skill：set_reminder(time,content) / check_weather(city,date) / '
       'open_file(path,mode) / chat(reply)。格式 {"skill":...,"parameters":{}}')
t0 = time.time()
r2 = m.chat([{"role": "system", "content": SYS},
             {"role": "user", "content": "明天七点提醒我交房租"}],
            max_tokens=120, temperature=0.1, fmt="json")
print("json:", r2[0], "|", repr(r2[1]), f"| {time.time()-t0:.1f}s")

import skills  # noqa: E402
print("handle:", skills.handle(r2[1], "明天七点提醒我交房租", mock=True))
m.stop()
print("DONE")

