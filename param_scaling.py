# -*- coding: utf-8 -*-
"""参数规模退化实测：1/2/3/4 个字段，各 5 条不同说法，统计完整 JSON 通过率。

判定通过 = JSON 可解析 + finish_reason=stop + 所有要求字段存在且非空。
用法: python param_scaling.py <模型> <端口> <gemma|qwen>
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

BASE_SYS = ("你是一个只输出 JSON 的指令解析器。可用 skill 只有一个：set_reminder，"
            "它支持这些字段：time、content、repeat、priority。"
            "按用户话里实际出现的信息填字段，不要编造没有提到的字段。"
            "只输出一个 JSON 对象，不要解释、不要 markdown。")

LEVELS = {
    1: (["content"], [
        "提醒我交房租",
        "提醒我去拿快递",
        "记得提醒我买牛奶",
        "提醒我给妈妈打个电话",
        "帮我记一下要交水电费",
    ]),
    2: (["time", "content"], [
        "明天早上七点提醒我去交房租",
        "今晚九点提醒我吃药",
        "后天下午三点提醒我开会",
        "明天中午提醒我取外卖",
        "周五早上八点提醒我体检",
    ]),
    3: (["time", "content", "repeat"], [
        "明天早上七点提醒我去交房租，每周重复一次",
        "每天八点提醒我吃维生素，一直重复",
        "今晚九点提醒我吃药，每天都要提醒",
        "每周一早上九点提醒我交周报，按周重复",
        "每天早上六点半提醒我跑步，天天都要",
    ]),
    4: (["time", "content", "repeat", "priority"], [
        "明天早上七点提醒我去交房租，每周重复一次，优先级高",
        "每天八点提醒我吃维生素，每天重复，优先级低",
        "今晚九点提醒我吃药，天天重复，这件事很重要",
        "每周一早上九点提醒我交周报，按周重复，优先级最高",
        "早上六点半提醒我跑步，每天重复，优先级普通",
    ]),
}

logf = open(os.path.join(ROOT, "runtime", f"scale-{FAMILY}.log"), "wb")
p = subprocess.Popen([EXE, "-m", MODEL, "-c", "2048", "-t", "4", "--port", PORT,
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
print(f"[{FAMILY}] load_s={time.time()-t0:.1f}")


def ask(text, max_tok):
    sysmsg = BASE_SYS + ("\n/no_think" if FAMILY == "qwen" else "")
    body = {"messages": [{"role": "system", "content": sysmsg},
                         {"role": "user", "content": text}],
            "max_tokens": max_tok, "temperature": 0.2, "stream": False,
            "response_format": {"type": "json_object"}}
    if FAMILY == "gemma":
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(base + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.loads(r.read().decode())
    msg = out["choices"][0]["message"]
    return (msg.get("content") or "").strip(), out["choices"][0].get("finish_reason"), time.time() - t


for lv in (1, 2, 3, 4):
    fields, cases = LEVELS[lv]
    ok = 0
    times = []
    fails = []
    for text in cases:
        try:
            c, fin, dt = ask(text, 400 if FAMILY == "gemma" else 260)
        except Exception as e:  # noqa: BLE001
            fails.append(f"ERR:{e}")
            continue
        times.append(dt)
        obj = None
        try:
            obj = json.loads(c)
        except Exception:
            fails.append("BADJSON:" + c[:40])
        if obj is not None:
            args = obj.get("parameters") or obj.get("args") or obj
            if isinstance(args, dict) and all(
                    str(args.get(k, "")).strip() not in ("", "None") for k in fields):
                if fin == "stop":
                    ok += 1
                else:
                    fails.append(f"TRUNC({fin})")
            else:
                miss = [k for k in fields if not str(args.get(k, "")).strip()] if isinstance(args, dict) else ["no-dict"]
                fails.append("MISS:" + ",".join(miss) + " | " + c[:50])
    avg = sum(times) / len(times) if times else 0
    print(f"  {lv} 参数: {ok}/{len(cases)}  平均 {avg:.1f}s")
    for f in fails[:3]:
        print(f"       - {f}")

p.kill()
