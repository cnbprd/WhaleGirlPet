# -*- coding: utf-8 -*-
"""模型 API 接入：把三种协议（OpenAI 兼容 / Anthropic / Gemini）收成同一套调用。

职责只有三件：拼请求（URL + 头 + body）、解析回复、拉模型列表。
不碰界面、不读写配置，便于单独测。
"""
import json
import urllib.error
import urllib.request

FORMATS = ("openai", "anthropic", "gemini")
FORMAT_LABELS = {"openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Gemini"}

DEFAULT_ENDPOINTS = {
    "openai": "",   # 留空 → 走项目原有的智谱默认地址
    "anthropic": "https://api.anthropic.com",
    "gemini": "https://generativelanguage.googleapis.com",
}

ANTHROPIC_VERSION = "2023-06-01"
TIMEOUT = 20


class Unsupported(Exception):
    """这种协议不提供该能力（比如 Anthropic 没有模型列表接口）。"""


def _clean(url: str) -> str:
    return (url or "").strip().rstrip("/")


def chat_url(fmt: str, base: str) -> str:
    """按协议把用户填的地址补成完整对话接口。"""
    b = _clean(base) or DEFAULT_ENDPOINTS.get(fmt, "")
    if fmt == "anthropic":
        if b.endswith("/v1/messages"):
            return b
        if b.endswith("/v1"):
            return b + "/messages"
        return b + "/v1/messages"
    if fmt == "gemini":
        return b      # 具体 URL 在 build_request 里拼（要带 model 和 key）
    # openai 兼容
    if b.endswith("/chat/completions"):
        return b
    return b + "/chat/completions"


def build_request(fmt: str, endpoint: str, model: str, api_key: str,
                  messages: list, system_prompt: str = "",
                  max_tokens: int = 300, temperature: float = 0.8):
    """返回 (url, headers, body_dict)。messages 为 [{"role","content"}]。"""
    fmt = fmt if fmt in FORMATS else "openai"
    key = (api_key or "").strip()
    mdl = (model or "").strip()

    if fmt == "anthropic":
        url = chat_url(fmt, endpoint)
        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        convo = [m for m in messages if m.get("role") in ("user", "assistant")]
        body = {
            "model": mdl or "claude-sonnet-4-5",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m["role"], "content": m["content"]} for m in convo],
        }
        if system_prompt:
            body["system"] = system_prompt
        return url, headers, body

    if fmt == "gemini":
        base = _clean(endpoint) or DEFAULT_ENDPOINTS["gemini"]
        prefix = "" if base.endswith("/v1beta") else "/v1beta"
        name = mdl or "gemini-2.5-flash"
        url = f"{base}{prefix}/models/{name}:generateContent?key={key}"
        headers = {"Content-Type": "application/json"}
        contents = []
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
        body = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        return url, headers, body

    # OpenAI 兼容（含智谱、DeepSeek、Moonshot 等）
    url = chat_url("openai", endpoint)
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    body = {
        "model": mdl,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    return url, headers, body


def parse_reply(fmt: str, payload: dict) -> str:
    """从各家不同的返回结构里抠出正文。"""
    fmt = fmt if fmt in FORMATS else "openai"
    if fmt == "anthropic":
        blocks = payload.get("content") or []
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return "".join(texts).strip()
    if fmt == "gemini":
        cands = payload.get("candidates") or []
        if not cands:
            return ""
        parts = (cands[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts).strip()
    choices = payload.get("choices") or []
    if not choices:
        return ""
    return ((choices[0].get("message") or {}).get("content") or "").strip()


def list_models(fmt: str, endpoint: str, api_key: str) -> list:
    """拉取该接入点可用的模型名。openai 走 GET /models，gemini 走 v1beta/models。"""
    fmt = fmt if fmt in FORMATS else "openai"
    key = (api_key or "").strip()
    if not key:
        raise Unsupported("先填 API Key 才能拉模型列表")
    if fmt == "anthropic":
        raise Unsupported("Anthropic 不提供模型列表接口，请手动填写模型名")

    if fmt == "gemini":
        base = _clean(endpoint) or DEFAULT_ENDPOINTS["gemini"]
        prefix = "" if base.endswith("/v1beta") else "/v1beta"
        url = f"{base}{prefix}/models?key={key}"
        headers = {"Content-Type": "application/json"}
    else:
        base = _clean(endpoint) or DEFAULT_ENDPOINTS["openai"]
        base = base.replace("/chat/completions", "")
        url = base + "/models"
        headers = {"Authorization": "Bearer " + key}

    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    if fmt == "gemini":
        names = [str(m.get("name", "")) for m in (payload.get("models") or [])]
        return sorted(n.split("/")[-1] for n in names if n)
    items = payload.get("data") or payload.get("models") or []
    out = []
    for it in items:
        mid = it.get("id") or it.get("name") or ""
        if mid:
            out.append(str(mid))
    return sorted(out)


def test_rule_text(fmt: str) -> str:
    """「查看填写规则」弹出来的说明：各家地址怎么填才对。"""
    if fmt == "anthropic":
        return ("Anthropic：API 地址填 https://api.anthropic.com（会自动补 /v1/messages）。\n"
                "Key 从 console.anthropic.com 创建，形如 sk-ant-xxx。\n"
                "模型名示例：claude-sonnet-4-5（请按你账号可用的模型填）。")
    if fmt == "gemini":
        return ("Gemini：API 地址填 https://generativelanguage.googleapis.com"
                "（会自动补 /v1beta/models/{模型}:generateContent）。\n"
                "Key 从 Google AI Studio 拿，形如 AIza...\n"
                "模型名示例：gemini-2.5-flash")
    return ("OpenAI 兼容：填根地址（如 https://open.bigmodel.cn/api/paas/v4），"
            "程序会自动补 /chat/completions。\n"
            "留空 = 用项目自带的智谱默认地址。\n"
            "Key 放 API Key 里；没填时会去读 ZHIPU_API_KEY 环境变量或 ~/.zhipu_api_key.txt。")
