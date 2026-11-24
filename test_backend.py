# -*- coding: utf-8 -*-
"""后端切换验证：Ollama 优先 / 无 Ollama 回退 llama.cpp / JSON 强制模式。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import local_llm  # noqa: E402

print("ollama_alive(11434):", local_llm.ollama_alive("http://127.0.0.1:11434"))
print("models 11434:", local_llm.ollama_models("http://127.0.0.1:11434"))
print("models 11435:", local_llm.ollama_models("http://127.0.0.1:11435"))
print("loaded:", local_llm.ollama_loaded("http://127.0.0.1:11435"))

cfg = {"ollama_host": "http://127.0.0.1:11435", "ollama_model": "qwen3.5:4b", "llm_ctx": 4096}
m = local_llm.ServerManager(cfg)
print("backend:", m.backend, "| health:", m.health(), "| start:", m.start())

ok, txt = m.chat([{"role": "user", "content": "用一句话介绍你自己，别超过20字"}], max_tokens=80)
print("chat:", ok, repr(txt))

ok2, j = m.chat(
    [{"role": "system", "content": "只输出JSON：{\"skill\":...,\"parameters\":{}}"},
     {"role": "user", "content": "明天七点提醒我交房租"}],
    max_tokens=120, fmt="json")
print("json:", ok2, repr(j))

# 无 Ollama 时回退
m2 = local_llm.ServerManager({"ollama_host": "http://127.0.0.1:11999"})
print("fallback backend:", m2.backend, "| available:", local_llm.available())
