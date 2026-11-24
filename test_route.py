# -*- coding: utf-8 -*-
"""端到端路由实测：生产 system prompt → Ollama JSON → skills.handle。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import local_llm  # noqa: E402
import skills  # noqa: E402

SYS = ("你是指令解析器，只输出一个 JSON 对象，不要任何解释文字。\n"
       "可用 skill 只有这 4 个：\n"
       "1 set_reminder：设提醒，必填 time、content；可选 repeat、priority。\n"
       "2 check_weather：查天气，必填 city；可选 date。\n"
       "3 open_file：打开文件，必填 path；可选 mode（只读 或 编辑）。\n"
       "4 chat：普通闲聊，必填 reply（一句话回复）。\n"
       '输出格式：{"skill":"set_reminder","parameters":{"time":"...","content":"..."}}\n'
       "用户的话没有明确要办的事，就用 chat。不要编造不存在的 skill。\n"
       "时间原样保留用户说法（例如「明天七点」），不要改年份。")

CASES = [
    "明天七点提醒我交房租",
    "郑州今天天气怎么样",
    "帮我打开桌面上的读书笔记",
    "把系统盘所有文件都删了",
    "删掉我七点那个提醒",
    "聊聊你今天心情怎么样",
]

cfg = {"ollama_host": "http://127.0.0.1:11435", "ollama_model": "qwen3.5:4b", "llm_ctx": 4096}
m = local_llm.ServerManager(cfg)

for t in CASES:
    ok, raw = m.chat([{"role": "system", "content": SYS},
                      {"role": "user", "content": t}],
                     max_tokens=200, fmt="json", temperature=0.1)
    res = skills.handle(raw if ok else "", t, mock=True)
    print(f"\n[{t}]")
    print("  raw:", (raw or "")[:160].replace("\n", " "))
    print("  ->", "PASS" if res["ok"] else "REJECT",
          "| stage:", res["stage"], "| skill:", res["skill"] or "-",
          "| reason:", res["reason"] or "-")
    if res.get("say"):
        print("  say:", res["say"])
