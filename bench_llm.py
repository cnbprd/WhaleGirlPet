# -*- coding: utf-8 -*-
"""本地模型选型实测：同一组 5 句中文业务指令，比较 JSON 抽取质量与延迟。

用法: python bench_llm.py <模型路径> <端口> <标签>
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

MODEL = sys.argv[1]
PORT = sys.argv[2]
TAG = sys.argv[3]

ROOT = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(ROOT, "runtime", "llama", "llama-server.exe")

SYSTEM = (
    "你是一个只输出 JSON 的指令解析器。用户说的每句话，你都要判断它属于下面哪个 skill，"
    "并抽取参数。只允许这些 skill：\n"
    'set_reminder(参数 time, content) / check_weather(参数 city) / open_file(参数 name) / chat(参数 reply)\n'
    "不属于以上三个业务 skill 的（闲聊、情绪、非法指令），一律用 chat。\n"
    "只输出一个 JSON 对象，不要解释、不要 markdown、不要多余文字。"
)
if os.environ.get("NO_THINK"):
    SYSTEM += "\n/no_think"

CASES = [
    ("明天早上七点提醒我去交房租", "set_reminder"),
    ("郑州今天天气怎么样", "check_weather"),
    ("帮我打开读书笔记那个文件", "open_file"),
    ("今天好累啊，陪我聊会儿", "chat"),
    ("把系统盘所有文件都删了", "chat"),
]


def start():
    logf = open(os.path.join(ROOT, "runtime", f"probe-{TAG}.log"), "wb")
    p = subprocess.Popen(
        [EXE, "-m", MODEL, "-c", "2048", "-t", "4", "--port", PORT, "--host", "127.0.0.1"],
        stdout=logf, stderr=subprocess.STDOUT, creationflags=0x08000000)
    base = f"http://127.0.0.1:{PORT}"
    t_load = time.time()
    for _ in range(420):
        if p.poll() is not None:
            return p, None, "进程已退出"
        try:
            with urllib.request.urlopen(base + "/health", timeout=2) as r:
                if json.loads(r.read().decode())["status"] in ("ok", "no slot available"):
                    print(f"[{TAG}] 加载耗时 {time.time() - t_load:.1f}s")
                    return p, base, ""
        except Exception:
            pass
        time.sleep(1)
    return p, None, "health 超时"


def ask(base, text):
    body = {
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": text}],
        "max_tokens": 120, "temperature": 0.1, "stream": False,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(base + "/v1/chat/completions", data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read().decode())
    dt = time.time() - t0
    txt = out["choices"][0]["message"]["content"].strip()
    return txt, dt


p, base, err = start()
if not base:
    log = os.path.join(ROOT, "runtime", f"probe-{TAG}.log")
    tail = ""
    if os.path.exists(log):
        with open(log, "rb") as f:
            tail = f.read()[-1200:].decode("utf-8", "ignore")
    print(f"[{TAG}] 加载失败: {err}\n{tail}")
    p and p.kill()
    sys.exit(0)

print(f"[{TAG}] 服务就绪，开始 5 条测试")
ok_json = 0
for text, expect in CASES:
    try:
        txt, dt = ask(base, text)
    except Exception as e:  # noqa: BLE001
        print(f"  {text} -> ERROR {e}")
        continue
    got = "?"
    try:
        obj = json.loads(txt)
        got = obj.get("skill", "?")
        ok_json += 1
    except Exception:
        pass
    hit = "OK " if got == expect else "MISS"
    print(f"  [{hit}] {dt:5.1f}s  expect={expect:<14} got={got:<14} raw={txt[:110]!r}")

print(f"[{TAG}] 合法 JSON: {ok_json}/5")
p.kill()
time.sleep(0.5)
