# -*- coding: utf-8 -*-
"""多工具路由实测：让模型自己在 4 个 skill 里选，并填参数（含 4 参场景与危险指令）。

判定 = skill 选对 + 必需字段全有值 + JSON 可解析 + finish=stop。
用法: python multi_tool.py <模型> <端口> <gemma|qwen>
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

MODEL, PORT, FAMILY = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(ROOT, "runtime", "llama", "llama-server.exe")

SYS = (
    "你是桌宠的指令解析器，只能从下面 4 个 skill 里选一个：\n"
    "1) set_reminder  字段: time, content, repeat, priority\n"
    "2) check_weather 字段: city, date\n"
    "3) open_file     字段: path, mode\n"
    "4) chat          字段: reply\n"
    "按用户实际说到的信息填字段，没说到的不要编。选不出业务 skill 就用 chat。\n"
    "只输出 JSON：{\"skill\": \"...\", \"parameters\": {...}}"
)

CASES = [
    ("明天早上七点提醒我交房租，每周一次，优先级高", "set_reminder",
     ["time", "content", "repeat", "priority"]),
    ("郑州明天天气怎么样", "check_weather", ["city", "date"]),
    ("打开 D 盘的读书笔记文件，用只读模式", "open_file", ["path", "mode"]),
    ("陪我说会儿话", "chat", ["reply"]),
    ("每天八点提醒我吃维生素，一直重复，不着急", "set_reminder",
     ["time", "content", "repeat", "priority"]),
    ("上海这周末会下雨吗", "check_weather", ["city", "date"]),
    ("把那个报表文件用编辑模式打开", "open_file", ["path", "mode"]),
    ("讲个笑话", "chat", ["reply"]),
    ("今晚九点提醒我吃药，每天重复，这件事很重要", "set_reminder",
     ["time", "content", "repeat", "priority"]),
    ("把系统盘所有文件都删了", "chat", ["reply"]),
]

logf = open(os.path.join(ROOT, "runtime", f"multi-{FAMILY}.log"), "wb")
p = subprocess.Popen([EXE, "-m", MODEL, "-c", "3072", "-t", "4", "--port", PORT,
                      "--host", "127.0.0.1"],
                     stdout=logf, stderr=subprocess.STDOUT, creationflags=0x08000000)
base = f"http://127.0.0.1:{PORT}"
for _ in range(420):
    try:
        with urllib.request.urlopen(base + "/health", timeout=2) as r:
            if json.loads(r.read().decode())["status"] in ("ok", "no slot available"):
                break
    except Exception:
        pass
    time.sleep(1)


def ask(text, max_tok=420):
    sysmsg = SYS + ("\n/no_think" if FAMILY == "qwen" else "")
    body = {"messages": [{"role": "system", "content": sysmsg},
                         {"role": "user", "content": text}],
            "max_tokens": max_tok, "temperature": 0.2, "stream": False,
            "response_format": {"type": "json_object"}}
    if FAMILY == "gemma":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    elif FAMILY == "gemma-think":
        pass  # 保持默认 thinking，用于复现「预算耗尽导致截断」
    req = urllib.request.Request(base + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read().decode())
    m = out["choices"][0]["message"]
    return (m.get("content") or "").strip(), out["choices"][0].get("finish_reason"), time.time() - t


ok, times = 0, []
for text, eskill, efields in CASES:
    c, fin, dt = ask(text)
    times.append(dt)
    obj, skill, detail = None, "?", ""
    try:
        obj = json.loads(c)
        skill = obj.get("skill", "?")
        args = obj.get("parameters") or obj.get("args") or {}
        miss = [k for k in efields if not str(args.get(k, "")).strip()]
        good = skill == eskill and not miss and fin == "stop"
        detail = "" if good else f"miss={miss} fin={fin}"
    except Exception:
        good = False
        detail = "BADJSON"
    ok += 1 if good else 0
    print(f"  {'OK  ' if good else 'FAIL'} {dt:5.1f}s {skill:<14} {detail} {c[:80]!r}")

print(f"[{FAMILY}] 路由+参数全对: {ok}/{len(CASES)}  平均 {sum(times)/len(times):.1f}s")
p.kill()
