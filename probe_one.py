# -*- coding: utf-8 -*-
"""单条探针：完整打印 llama-server 的响应结构，判断空输出原因。

用法: python probe_one.py <模型> <端口> <文本> [json|plain]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

MODEL, PORT, TEXT = sys.argv[1], sys.argv[2], sys.argv[3]
MODE = sys.argv[4] if len(sys.argv) > 4 else "json"
ROOT = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(ROOT, "runtime", "llama", "llama-server.exe")

SYSTEM = ("你是一个只输出 JSON 的指令解析器。只允许 skill：set_reminder(time,content) / "
          "check_weather(city) / open_file(name) / chat(reply)。只输出 JSON，不要解释。")

logf = open(os.path.join(ROOT, "runtime", "probe-one.log"), "wb")
p = subprocess.Popen([EXE, "-m", MODEL, "-c", "2048", "-t", "4", "--port", PORT,
                      "--host", "127.0.0.1"],
                     stdout=logf, stderr=subprocess.STDOUT, creationflags=0x08000000)
base = f"http://127.0.0.1:{PORT}"
t0 = time.time()
ready = False
for _ in range(420):
    try:
        with urllib.request.urlopen(base + "/health", timeout=2) as r:
            if json.loads(r.read().decode())["status"] in ("ok", "no slot available"):
                ready = True
                break
    except Exception:
        pass
    time.sleep(1)
print("ready:", ready, "load_s:", round(time.time() - t0, 1))

body = {"messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": TEXT}],
        "max_tokens": 200, "temperature": 0.2, "stream": False}
if MODE == "json":
    body["response_format"] = {"type": "json_object"}
data = json.dumps(body, ensure_ascii=False).encode()
req = urllib.request.Request(base + "/v1/chat/completions", data=data,
                             headers={"Content-Type": "application/json"})
t1 = time.time()
with urllib.request.urlopen(req, timeout=300) as r:
    out = json.loads(r.read().decode())
print("elapsed:", round(time.time() - t1, 1))
print("finish_reason:", out["choices"][0].get("finish_reason"))
print("usage:", out.get("usage"))
msg = out["choices"][0]["message"]
print("content:", repr(msg.get("content", ""))[:400])
print("reasoning:", repr(msg.get("reasoning_content", ""))[:400])
p.kill()
