# -*- coding: utf-8 -*-
"""ChatWorker 端到端：三种协议真的发出去、拿到回复；自定义头与参数覆盖真的进请求。

用本机临时服务当"假厂商"，不碰真网。
"""
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QCoreApplication  # noqa: E402

app = QCoreApplication([])
import ai as ai_mod  # noqa: E402

GOT = {"posts": []}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        GOT["posts"].append({"path": self.path, "headers": dict(self.headers), "body": body})
        if self.path.endswith("/chat/completions"):
            out = {"choices": [{"message": {"content": "你好呀"}}]}
        elif self.path.endswith("/v1/messages"):
            out = {"content": [{"type": "text", "text": "我是 Claude"}]}
        elif ":generateContent" in self.path:
            out = {"candidates": [{"content": {"parts": [{"text": "我是 Gemini"}]}}]}
        else:
            out = {}
        data = json.dumps(out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


s = socket.socket()
s.bind(("127.0.0.1", 0))
PORT = s.getsockname()[1]
s.close()
BASE = f"http://127.0.0.1:{PORT}"
srv = HTTPServer(("127.0.0.1", PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

bad = 0


def run_case(name, fmt, extra=None, want="", expect_fail=None, key="key-123"):
    global bad
    box = {"reply": None, "fail": None}
    w = ai_mod.ChatWorker(BASE, "test-model", key, [], "在吗",
                          system_prompt="你是鲸鱼娘", api_format=fmt, **(extra or {}))
    w.reply_ready.connect(lambda c: box.__setitem__("reply", c))
    w.failed.connect(lambda r: box.__setitem__("fail", r))
    w.run()          # 直接调用，不走线程
    if expect_fail:
        ok = box["fail"] == expect_fail
        print(("[ok]  " if ok else "[BAD] ") + f"{name} → failed={box['fail']}")
    else:
        ok = box["reply"] == want
        print(("[ok]  " if ok else "[BAD] ") + f"{name} → {box['reply']!r}")
    if not ok:
        bad += 1


run_case("openai", "openai", want="你好呀")
run_case("anthropic", "anthropic", want="我是 Claude")
run_case("gemini", "gemini", want="我是 Gemini")
run_case("自定义头+参数覆盖", "openai",
         {"extra_headers": '{"X-Title":"whale"}', "params_override": '{"top_p":0.9}'},
         want="你好呀")
run_case("无 key", "anthropic", want=None, expect_fail="no_key", key="")

last = GOT["posts"][-2] if len(GOT["posts"]) >= 2 else {}
print("\n实际发出的请求：")
for p in GOT["posts"]:
    print("  ", p["path"][:70], "| 头:", "|".join(k for k in p["headers"] if k.lower() in
                                                  ("authorization", "x-api-key", "anthropic-version",
                                                   "x-title", "content-type")))
    b = p["body"]
    keys = sorted(b.keys())
    print("     body 键:", keys, "| temperature:", b.get("temperature"), "| top_p:", b.get("top_p"))

srv.shutdown()
print("\n%d 项失败" % bad)
sys.exit(1 if bad else 0)
