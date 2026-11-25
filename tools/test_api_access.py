# -*- coding: utf-8 -*-
"""api_access 协议层单测：三种格式的 URL/头/body 拼装、回复解析、模型列表。

用本机临时 HTTP 服务模拟各家返回，不碰真网。
"""
import json
import os
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import api_access as A  # noqa: E402

SEEN = {"paths": [], "headers": []}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        SEEN["paths"].append(self.path)
        if self.path.startswith("/models"):
            self._send({"data": [{"id": "glm-4-flash"}, {"id": "glm-4-plus"}]})
        elif ":models" in self.path or "/v1beta/models" in self.path:
            self._send({"models": [{"name": "models/gemini-2.5-flash"},
                                   {"name": "models/gemini-2.5-pro"}]})
        else:
            self._send({"data": []})

    def do_POST(self):
        SEEN["paths"].append(self.path)
        SEEN["headers"].append(dict(self.headers))
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        SEEN.setdefault("bodies", []).append(body)
        if self.path.endswith("/chat/completions"):
            self._send({"choices": [{"message": {"content": " 你好呀 "}}]})
        elif self.path.endswith("/v1/messages"):
            self._send({"content": [{"type": "text", "text": "我是 Claude"}]})
        elif ":generateContent" in self.path:
            self._send({"candidates": [{"content": {"parts": [{"text": "我是 Gemini"}]}}]})
        else:
            self._send({})


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


PORT = _free_port()
BASE = f"http://127.0.0.1:{PORT}"
srv = HTTPServer(("127.0.0.1", PORT), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

MSGS = [{"role": "user", "content": "在吗"}]
SYS = "你是鲸鱼娘"
bad = 0


def check(name, got, want):
    global bad
    ok = got == want
    print(("[ok]  " if ok else "[BAD] ") + name)
    if not ok:
        print("    got :", got)
        print("    want:", want)
        bad += 1


# 1) URL 拼接
check("openai 根地址补 /chat/completions",
      A.chat_url("openai", BASE), BASE + "/chat/completions")
check("openai 已带 /chat/completions 不重复",
      A.chat_url("openai", BASE + "/chat/completions"), BASE + "/chat/completions")
check("anthropic 根地址补 /v1/messages",
      A.chat_url("anthropic", BASE), BASE + "/v1/messages")
check("anthropic /v1 补 /messages",
      A.chat_url("anthropic", BASE + "/v1"), BASE + "/v1/messages")

# 2) 请求拼装
url, h, body = A.build_request("openai", BASE, "glm-4-flash", "k1", MSGS, SYS)
check("openai body 原样透传 messages（system 由 ChatWorker 拼）", [m["role"] for m in body["messages"]], ["user"])
check("openai 头带 Bearer", h.get("Authorization"), "Bearer k1")

url, h, body = A.build_request("anthropic", BASE, "claude-sonnet-4-5", "k2", MSGS, SYS, max_tokens=120)
check("anthropic system 提到顶层", body.get("system"), SYS)
check("anthropic messages 不含 system", [m["role"] for m in body["messages"]], ["user"])
check("anthropic 头带 x-api-key", h.get("x-api-key"), "k2")
check("anthropic 头带版本", h.get("anthropic-version"), A.ANTHROPIC_VERSION)

url, h, body = A.build_request("gemini", BASE, "gemini-2.5-flash", "k3", MSGS, SYS, max_tokens=90)
check("gemini URL 带模型与 key",
      url, BASE + "/v1beta/models/gemini-2.5-flash:generateContent?key=k3")
check("gemini systemInstruction", body["systemInstruction"]["parts"][0]["text"], SYS)
check("gemini generationConfig maxOutputTokens",
      body["generationConfig"]["maxOutputTokens"], 90)

# 3) 解析
check("openai 解析", A.parse_reply("openai",
      {"choices": [{"message": {"content": " 你好呀 "}}]}), "你好呀")
check("anthropic 解析", A.parse_reply("anthropic",
      {"content": [{"type": "text", "text": "我是 Claude"}]}), "我是 Claude")
check("gemini 解析", A.parse_reply("gemini",
      {"candidates": [{"content": {"parts": [{"text": "我是 Gemini"}]}}]}), "我是 Gemini")
check("空返回不炸", A.parse_reply("gemini", {}), "")

# 4) 模型列表
check("openai 模型列表", A.list_models("openai", BASE, "k1"), ["glm-4-flash", "glm-4-plus"])
check("gemini 模型列表（去 models/ 前缀）",
      A.list_models("gemini", BASE, "k3"), ["gemini-2.5-flash", "gemini-2.5-pro"])
try:
    A.list_models("anthropic", BASE, "k2")
    check("anthropic 应报不支持", "没抛异常", "抛 Unsupported")
except A.Unsupported as e:
    check("anthropic 应报不支持", str(e)[:6], "Anthro")

# 5) 无 key
try:
    A.list_models("openai", BASE, "")
    check("无 key 应报错", "没抛异常", "抛 Unsupported")
except A.Unsupported:
    check("无 key 应报错", "Unsupported", "Unsupported")

srv.shutdown()
print(f"\n请求记录：{len(SEEN['paths'])} 次，路径示例 {SEEN['paths'][:3]}")
print("%d 项失败" % bad)
sys.exit(1 if bad else 0)
