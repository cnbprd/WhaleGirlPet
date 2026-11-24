# -*- coding: utf-8 -*-
"""Gemma 4 E2B：对比「放大 token 预算」与「关闭 thinking」两种解法的效果与耗时。"""
import json
import os
import subprocess
import sys
import time
import urllib.request

MODEL = sys.argv[1]
PORT = sys.argv[2]
ROOT = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(ROOT, "runtime", "llama", "llama-server.exe")

SYSTEM = ("你是一个只输出 JSON 的指令解析器。只允许 skill：set_reminder(time,content) / "
          "check_weather(city) / open_file(name) / chat(reply)。只输出 JSON，不要解释。")
CASES = [("明天早上七点提醒我去交房租", "set_reminder"),
         ("郑州今天天气怎么样", "check_weather"),
         ("帮我打开读书笔记那个文件", "open_file"),
         ("今天好累啊，陪我聊会儿", "chat"),
         ("把系统盘所有文件都删了", "chat")]

logf = open(os.path.join(ROOT, "runtime", "probe-gemma-modes.log"), "wb")
p = subprocess.Popen([EXE, "-m", MODEL, "-c", "4096", "-t", "4", "--port", PORT,
                      "--host", "127.0.0.1"],
                     stdout=logf, stderr=subprocess.STDOUT, creationflags=0x08000000)
base = f"http://127.0.0.1:{PORT}"
t0 = time.time()
for _ in range(420):
    try:
        with urllib.request.urlopen(base + "/health", timeout=2) as r:
            if json.loads(r.read().decode())["status"] in ("ok", "no slot available"):
                break
    except Exception:
        pass
    time.sleep(1)
print("load_s:", round(time.time() - t0, 1))


def call(text, max_tok, kwargs=None):
    body = {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": text}],
            "max_tokens": max_tok, "temperature": 0.2, "stream": False,
            "response_format": {"type": "json_object"}}
    if kwargs:
        body["chat_template_kwargs"] = kwargs
    req = urllib.request.Request(base + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read().decode())
    dt = time.time() - t
    msg = out["choices"][0]["message"]
    return (msg.get("content") or "").strip(), msg.get("reasoning_content") or "", dt, \
        out["choices"][0].get("finish_reason"), out.get("usage", {})["completion_tokens"]


for tag, max_tok, kwargs in (("A 大预算600", 600, None),
                             ("B 关thinking", 300, {"enable_thinking": False})):
    print(f"--- {tag} ---")
    ok = 0
    for text, expect in CASES:
        try:
            c, r, dt, fin, ntok = call(text, max_tok, kwargs)
        except Exception as e:  # noqa: BLE001
            print(f"  ERR {e}")
            continue
        got = "?"
        if c:
            try:
                got = json.loads(c).get("skill", "?")
                ok += 1
            except Exception:
                got = "BADJSON"
        print(f"  {dt:6.1f}s fin={fin:<7} tok={ntok:<4} got={got:<14} content={c[:90]!r}"
              f"{'  (reasoning ' + str(len(r)) + ' chars)' if r else ''}")
    print(f"  => 合法 JSON {ok}/5")

p.kill()
