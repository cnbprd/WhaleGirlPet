# -*- coding: utf-8 -*-
"""联网对话：OpenAI 兼容接口（默认智谱 GLM），后台线程调用，失败由上层回退本地台词。"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from paths import DEFAULT_NAME

def build_system_prompt(name: str) -> str:
    name = (name or "溟月").strip() or "溟月"
    return (
        f"你是 DeepSeek 鲸鱼娘（社区昵称「大肥鱼」），名叫{name}，女仆装少女。"
        "性格：聪明但懒，最爱吃白饭，嘴上嫌弃用户、心里亲近，称呼用户为「鱼片」。"
        "说话简短口语，每次只回 1-3 句，带一点傲娇和鲸鱼/大海的小梗，语气轻松，可用少量颜文字。"
        "禁止长段落、禁止列表、禁止说教；不知道的事就坦白说不知道，不要编造。"
    )

KNOWLEDGE_PROMPT = (
    "你是鲸鱼娘的打工学习助手。请围绕一个轻松的主题（海洋生物、科普冷知识、生活小常识、历史小故事轮换），"
    "用 2-3 句中文讲一个简短有趣的知识点，最后用一句话点出收获。不要列表，不要标题，不要编造不确定的数据。"
)

DEFAULT_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4-flash"
MAX_HISTORY = 10


def read_zhipu_key() -> str:
    key = os.environ.get("ZHIPU_API_KEY", "").strip()
    if key:
        return key
    p = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".zhipu_api_key.txt"
    if p.exists():
        try:
            return p.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


class ChatWorker(QThread):
    reply_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, endpoint: str, model: str, api_key: str, history: list, user_text: str,
                 system_prompt: str = "", max_tokens: int = 300, temperature: float = 0.8):
        super().__init__()
        ep = endpoint.strip().rstrip("/") or DEFAULT_ENDPOINT
        if not ep.endswith("/chat/completions"):
            ep = ep + "/chat/completions"
        self.endpoint = ep
        self.model = (model.strip() or DEFAULT_MODEL).lower()
        self.api_key = api_key.strip() or read_zhipu_key()
        self.history = list(history)[-MAX_HISTORY:]
        self.user_text = user_text
        self.system_prompt = system_prompt or build_system_prompt(DEFAULT_NAME)
        self.max_tokens = max_tokens
        self.temperature = temperature

    def run(self):
        if not self.api_key:
            self.failed.emit("no_key")
            return
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": self.user_text})
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key}
        req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = (payload.get("choices") or [{}])[0].get("message", {}).get("content", "")
            content = content.strip()
            if not content:
                self.failed.emit("empty")
                return
            self.reply_ready.emit(content)
        except urllib.error.HTTPError as e:
            self.failed.emit(f"http_{e.code}")
        except urllib.error.URLError:
            self.failed.emit("offline")
        except (ValueError, KeyError, TimeoutError, OSError):
            self.failed.emit("parse")
