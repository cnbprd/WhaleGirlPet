# -*- coding: utf-8 -*-
"""dafeiyu.cpp：托管 dafeiyu-server 子进程，走 OpenAI 兼容 /v1/chat/completions。

（引擎本体是 llama.cpp，本程序内改名为 dafeiyu.cpp；旧目录名 llama 仍兼容。）
模型与推理程序不打进 exe，放在程序同级 runtime/ 目录：
  runtime/dafeiyu/dafeiyu-server.exe
  runtime/models/qwen35-4b-Q4_K_M.gguf

未检测到这两者时 available() 为 False，上层自动回退云端 API。
"""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

from paths import runtime_dir

DEFAULT_PORT = 8085
MODEL_NAME = "Qwen3-4B-Q4_K_M.gguf"
# 优先用 qwen3.5（从 Ollama 的 gguf blob 复制过来，脱离 Ollama 也能跑）
PREFERRED_MODELS = ["qwen35-4b-Q4_K_M.gguf", MODEL_NAME]


def server_exe() -> str:
    """优先 dafeiyu-server.exe，其次旧的 llama-server.exe，最后旧目录。"""
    base = os.path.join(runtime_dir(), "dafeiyu")
    for name in ("dafeiyu-server.exe", "llama-server.exe"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return os.path.join(runtime_dir(), "llama", "llama-server.exe")


def model_path(name: str = "") -> str:
    base = os.path.join(runtime_dir(), "models")
    if name:
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    for pref in PREFERRED_MODELS:
        p = os.path.join(base, pref)
        if os.path.exists(p):
            return p
    # 找不到指定文件名时取目录里第一个 .gguf，方便替换模型
    if os.path.isdir(base):
        for fname in sorted(os.listdir(base)):
            if fname.lower().endswith(".gguf"):
                return os.path.join(base, fname)
    return ""


def available() -> bool:
    return (os.path.exists(server_exe()) and bool(model_path())) or ollama_alive()


# ---------------- Ollama 后端 ----------------
# 有 Ollama 时优先用它：自带显存调度、keep_alive 闲置卸载、模型切换。
# 没装 Ollama 也照样能跑：回退到 runtime/llama/llama-server.exe。
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "qwen3.5:4b"


def _http_json(url: str, timeout: float = 3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def ollama_alive(host: str = OLLAMA_HOST) -> bool:
    data = _http_json(host + "/api/tags", timeout=2.0)
    return isinstance(data, dict) and "models" in data


def ollama_models(host: str = OLLAMA_HOST) -> list:
    data = _http_json(host + "/api/tags", timeout=3.0) or {}
    out = []
    for m in data.get("models") or []:
        out.append({
            "name": str(m.get("name") or ""),
            "size_gb": round(float(m.get("size") or 0) / 1073741824, 2),
            "family": str((m.get("details") or {}).get("family") or ""),
        })
    return out


def ollama_loaded(host: str = OLLAMA_HOST) -> list:
    data = _http_json(host + "/api/ps", timeout=3.0) or {}
    out = []
    for m in data.get("models") or []:
        out.append({
            "name": str(m.get("name") or ""),
            "vram_gb": round(float(m.get("size_vram") or 0) / 1073741824, 2),
            "expires_at": str(m.get("expires_at") or ""),
        })
    return out


def ollama_model_present(name: str, host: str = OLLAMA_HOST) -> bool:
    return any(m["name"] == name for m in ollama_models(host))


class ServerManager:
    """本地推理后端：优先 Ollama，没有就自己拉 llama-server。"""

    def __init__(self, config: dict):
        self.config = config
        self.port = int(config.get("llm_port", DEFAULT_PORT))
        self.proc = None
        self.ready = False
        self.last_error = ""

    @property
    def model_file(self) -> str:
        return str(self.config.get("llm_model_file", "") or "")

    def model(self) -> str:
        return model_path(self.model_file)

    # ---------- 后端选择 ----------
    @property
    def ollama_host(self) -> str:
        return str(self.config.get("ollama_host", OLLAMA_HOST) or OLLAMA_HOST)

    @property
    def backend(self) -> str:
        """auto: 有 Ollama 用 Ollama（GPU），否则 llama.cpp；也可强制 ollama / llama_cpp。

        空闲调度：config.gpu_when_idle 为真时，一旦检测到游戏在跑就把推理退回 CPU 引擎，
        不跟游戏抢显存；否则用 Ollama 吃 GPU。
        """
        want = str(self.config.get("llm_backend", "auto") or "auto")
        if want in ("ollama", "llama_cpp"):
            return want
        if not ollama_alive(self.ollama_host):
            return "llama_cpp"
        if self.config.get("gpu_when_idle", True):
            try:
                import gpu_guard
                if gpu_guard.game_running():
                    return "llama_cpp"
            except Exception:  # noqa: BLE001
                pass
        return "ollama"

    @property
    def ollama_model(self) -> str:
        return str(self.config.get("ollama_model", OLLAMA_DEFAULT_MODEL) or OLLAMA_DEFAULT_MODEL)

    def base_url(self) -> str:
        if self.backend == "ollama":
            return self.ollama_host
        return f"http://127.0.0.1:{self.port}"

    def health(self) -> bool:
        if self.backend == "ollama":
            return ollama_alive(self.ollama_host)
        try:
            with urllib.request.urlopen(self.base_url() + "/health", timeout=3) as r:
                data = json.loads(r.read().decode("utf-8"))
            return (data.get("status") or "") in ("ok", "no slot available")
        except Exception:
            return False

    def start(self) -> bool:
        if self.backend == "ollama":
            if ollama_alive(self.ollama_host):
                self.ready = True
                if not ollama_model_present(self.ollama_model, self.ollama_host):
                    self.last_error = f"Ollama 里没有 {self.ollama_model}，回退其他模型"
                return True
            self.last_error = "Ollama 服务没起来"
            return False
        if self.is_running() and self.health():
            self.ready = True
            return True
        if not available():
            self.last_error = "未找到 runtime/dafeiyu/dafeiyu-server.exe 或 runtime/models/*.gguf"
            return False
        exe, model = server_exe(), self.model()
        if not model:
            self.last_error = "runtime/models 里没有找到 .gguf"
            return False
        ctx = str(int(self.config.get("llm_ctx", 4096)))
        threads = str(max(2, min(8, (os.cpu_count() or 4) // 2)))
        args = [exe, "-m", model, "-c", ctx, "-t", threads, "--port", str(self.port),
                "--host", "127.0.0.1",
                # qwen3.5 / Gemma 默认会先写思考，把 max_tokens 吃光（实测 content 为空）
                "-rea", "off"]
        creationflags = 0
        if os.name == "nt":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        try:
            logf = open(os.path.join(runtime_dir(), "dafeiyu-server.log"), "ab")
            self.proc = subprocess.Popen(args, stdout=logf, stderr=subprocess.STDOUT,
                                         creationflags=creationflags)
        except Exception as e:  # noqa: BLE001
            self.last_error = f"启动失败：{e}"
            return False
        # 最多等 60 秒加载模型
        for _ in range(120):
            if self.proc.poll() is not None:
                self.last_error = "dafeiyu-server 进程已退出，详见 runtime/dafeiyu-server.log"
                return False
            if self.health():
                self.ready = True
                return True
            time.sleep(0.5)
        self.last_error = "加载超时（60s）"
        return False

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        self.ready = False

    # ---------- 推理 ----------
    def _pick_ollama_model(self) -> str:
        """指定模型不在库里时，挑一个能用的（优先 qwen）。"""
        want = self.ollama_model
        names = [m["name"] for m in ollama_models(self.ollama_host)]
        if want in names:
            return want
        for n in names:
            if "qwen" in n.lower():
                return n
        return names[0] if names else want

    def _chat_ollama(self, messages, max_tokens, temperature, timeout, fmt):
        body = {
            "model": self._pick_ollama_model(),
            "messages": messages,
            "stream": False,
            "think": False,      # Gemma 4 默认开思考，会把 token 全吃光
            "options": {"temperature": temperature, "num_predict": max_tokens,
                        "num_ctx": int(self.config.get("llm_ctx", 4096))},
        }
        if fmt:
            body["format"] = fmt
        req = urllib.request.Request(
            self.base_url() + "/api/chat",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
            msg = payload.get("message") or {}
            content = (msg.get("content") or "").strip()
            if not content:
                return False, "local_empty"
            return True, content
        except urllib.error.HTTPError as e:
            return False, f"local_http_{e.code}"
        except urllib.error.URLError:
            return False, "local_offline"
        except Exception:  # noqa: BLE001
            return False, "local_error"

    def chat(self, messages: list, max_tokens: int = 220, temperature: float = 0.7,
             timeout: int = 90, fmt: str | None = None):
        """返回 (ok, text_or_reason)。fmt="json" 时强制结构化输出（仅 Ollama 后端支持）。"""
        if not self.ready and not self.health():
            return False, "local_not_ready"
        if self.backend == "ollama":
            return self._chat_ollama(messages, max_tokens, temperature, timeout, fmt)
        body = {
            "model": "local",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if fmt:  # llama.cpp server 用 GBNF 约束成 json 对象
            body["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            self.base_url() + "/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = json.loads(r.read().decode("utf-8"))
            msg = (payload.get("choices") or [{}])[0].get("message", {})
            content = (msg.get("content") or "").strip()
            if not content:
                content = (msg.get("reasoning_content") or "").strip()
            if not content:
                return False, "local_empty"
            return True, content
        except urllib.error.HTTPError as e:
            return False, f"local_http_{e.code}"
        except urllib.error.URLError:
            return False, "local_offline"
        except Exception:  # noqa: BLE001
            return False, "local_error"


class LocalChatWorker(QThread):
    """带启动检查的推理线程：进程没起来就先拉起再问。"""

    reply_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, manager: ServerManager, messages: list, max_tokens: int = 220,
                 temperature: float = 0.7, fmt: str | None = None):
        super().__init__()
        self.manager = manager
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.fmt = fmt
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if self._stop:
            return
        if not self.manager.is_running() and not self.manager.start():
            self.failed.emit(self.manager.last_error or "local_start_failed")
            return
        ok, out = self.manager.chat(self.messages, self.max_tokens, self.temperature,
                                    fmt=self.fmt)
        if self._stop:
            return
        if ok:
            self.reply_ready.emit(out)
        else:
            self.failed.emit(out)

