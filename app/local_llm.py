# -*- coding: utf-8 -*-
"""dafeiyu.cpp：托管 dafeiyu-server 子进程，走 OpenAI 兼容 /v1/chat/completions。

（引擎本体在程序内统一命名为 dafeiyu.cpp，运行目录里不再出现旧引擎名。）
模型与推理程序不打进 exe，放在程序同级 runtime/ 目录：
  runtime/dafeiyu/dafeiyu-server.exe
  runtime/models/qwen35-4b-Q4_K_M.gguf

未检测到这两者时 available() 为 False，上层自动回退云端 API。
"""
import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

from paths import data_dir, runtime_dir

DEFAULT_PORT = 8085
MODEL_NAME = "Qwen3-4B-Q4_K_M.gguf"
# 优先用 qwen3.5（从 Ollama 的 gguf blob 复制过来，脱离 Ollama 也能跑）
PREFERRED_MODELS = ["qwen35-4b-Q4_K_M.gguf", MODEL_NAME]


def server_exe() -> str:
    """本地推理入口：runtime/dafeiyu 下的 dafeiyu-server.exe。

    v2.9.7 起运行目录里的可执行文件统一改成 dafeiyu-* 前缀，
    只保留最后一级旧目录兼容（老版本装过的机器升级上来还能跑）。
    """
    base = os.path.join(runtime_dir(), "dafeiyu")
    for name in ("dafeiyu-server.exe", "dafeiyu.exe"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return os.path.join(runtime_dir(), "dafeiyu", "dafeiyu-server.exe")


GGUF_MAGIC = b"GGUF"
_MAX_DEPTH = 2       # 模型目录递归层数：够覆盖 Ollama 风格的 blobs/子文件夹，又不会扫全盘


def model_dirs(config: dict = None) -> list:
    """所有会去找模型的目录，按优先级排序。

    v3.0.7 实测：用户会把 gguf 放到数据目录（储存位置）下的 workspace/ 或 models/，
    而旧版只认程序目录的 runtime/models —— 放在数据目录里永远扫不到。
    现在同时认：程序 runtime/models、数据目录下的 runtime/models / models / workspace，
    以及用户在 config 里手填的 llm_model_dirs。
    """
    ds = [os.path.join(runtime_dir(), "models")]
    d = data_dir()
    ds += [
        os.path.join(d, "runtime", "models"),
        os.path.join(d, "models"),
        os.path.join(d, "workspace"),
        os.path.join(d, "workspace", "models"),
    ]
    if config:
        extra = config.get("llm_model_dirs") or []
        if isinstance(extra, str):
            extra = [extra]
        ds += [str(x) for x in extra if x]
    seen, out = set(), []
    for p in ds:
        try:
            k = os.path.normcase(os.path.abspath(p))
        except (OSError, ValueError):
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(os.path.normpath(p))
    return out


def _is_gguf(path: str) -> bool:
    """文件名是 .gguf，或者前 4 字节是 GGUF 魔数（Ollama 的 blobs 就没有扩展名）。"""
    name = os.path.basename(path).lower()
    if name.endswith(".gguf"):
        return True
    if not name.endswith((".gguf.part", ".tmp", ".partial")):
        try:
            if os.path.getsize(path) < 1024 * 1024:   # 太小，不可能是权重
                return False
            with open(path, "rb") as f:
                return f.read(4) == GGUF_MAGIC
        except OSError:
            return False
    return False


def scan_models(config: dict = None) -> list:
    """按 model_dirs() 扫出所有可用的 gguf，返回 [{name,path,size_mb,dir}]。

    同一文件在多个目录出现时只保留优先级高的那个（按绝对路径去重）。
    """
    out, seen, seen_same = [], set(), set()
    for base in model_dirs(config):
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            depth = root[len(base):].count(os.sep)
            if depth >= _MAX_DEPTH:
                dirs[:] = []
            for fname in files:
                p = os.path.join(root, fname)
                try:
                    key = os.path.normcase(os.path.abspath(p))
                except (OSError, ValueError):
                    continue
                if key in seen:
                    continue
                if not _is_gguf(p):
                    continue
                size = 0
                try:
                    size = os.path.getsize(p)
                except OSError:
                    continue
                if size < 1024 * 1024:      # 小于 1MB 的“模型”是占位文件，不算
                    continue
                # 同名同体积的副本只列一次（程序目录优先），避免面板里出现两条一样的
                same = (fname.lower(), size)
                if same in seen_same:
                    continue
                seen.add(key)
                seen_same.add(same)
                out.append({"name": fname, "path": p,
                            "size_mb": size / 1048576, "dir": root})
    out.sort(key=lambda m: (-m["size_mb"], m["name"].lower()))
    return out


def resolve_model(name: str = "", config: dict = None) -> str:
    """把文件名 / 绝对路径解析成真实存在的 gguf 路径；找不到返回空串。"""
    name = (name or "").strip()
    if name and os.path.isabs(name) and os.path.exists(name) and _is_gguf(name):
        return name
    found = scan_models(config)
    if name:
        for m in found:
            if m["name"] == name or os.path.normcase(m["path"]) == os.path.normcase(name):
                return m["path"]
    if not name:
        for pref in PREFERRED_MODELS:
            for m in found:
                if m["name"].lower() == pref.lower():
                    return m["path"]
    if name:
        return ""
    return found[0]["path"] if found else ""


def _port_free(port: int) -> bool:
    """端口能不能绑（用来判断被谁占了）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.35)
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def model_path(name: str = "", config: dict = None) -> str:
    """兼容老调用：不给名字时取首选模型 / 第一个模型。"""
    return resolve_model(name, config)


def _has_image(messages) -> bool:
    """v3.0.18：这条消息里带不带图（OpenAI vision 的 content 数组）。"""
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") in ("image_url", "image"):
                    return True
    return False


def available(config: dict = None) -> bool:
    return ((os.path.exists(server_exe()) and bool(model_path("", config)))
            or ollama_alive())


def chat_route(config: dict, has_api: bool, local_ok: bool = None) -> str:
    """决定普通聊天走哪条路：cloud / local / none。

    v3.0.25：`llm_on` 只管“允许本地兜底”，`llm_prefer_local` 才是“优先用本地”。
    以前两者混用，只要本地可用，配了 API 也永远轮不到 API。
    """
    if local_ok is None:
        local_ok = available(config)
    allow_local = bool(config.get("llm_on", True)) and bool(local_ok)
    prefer_local = bool(config.get("llm_prefer_local", False))
    if allow_local and (prefer_local or not has_api):
        return "local"
    if has_api:
        return "cloud"
    if allow_local:
        return "local"
    return "none"


def kill_stray_servers() -> int:
    """清掉上次异常退出留下的推理进程。

    v3.0.4：实测发现桌宠被杀掉后 dafeiyu-server 会变成孤儿，2.39GB 内存一直不放，
    直到重启电脑。程序启动时先把残留的杀掉，再起自己的。
    """
    if os.name != "nt":
        return 0
    killed = 0
    flags = 0x08000000  # CREATE_NO_WINDOW
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq dafeiyu-server.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, encoding="oem", errors="ignore",
            timeout=10, creationflags=flags).stdout or ""
    except Exception:  # noqa: BLE001
        return 0
    for line in out.splitlines():
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) >= 2 and parts[0].lower().endswith("dafeiyu-server.exe"):
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True, timeout=10, creationflags=flags)
                killed += 1
            except Exception:  # noqa: BLE001
                pass
    return killed


# ---------------- Ollama 后端 ----------------
# 有 Ollama 时优先用它：自带显存调度、keep_alive 闲置卸载、模型切换。
# 没装 Ollama 也照样能跑：回退到 runtime/dafeiyu/dafeiyu-server.exe。
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "qwen3.5:4b"


_HTTP_CACHE = {}
_HTTP_TTL = 4.0      # v2.9.9：打开面板会连着问十几次 Ollama 状态，同 URL 4 秒内只发一次


def _http_json(url: str, timeout: float = 3.0):
    now = time.monotonic()
    hit = _HTTP_CACHE.get(url)
    if hit is not None and now - hit[0] < _HTTP_TTL:
        return hit[1]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        data = None
    _HTTP_CACHE[url] = (now, data)
    return data


def ollama_alive(host: str = OLLAMA_HOST) -> bool:
    data = _http_json(host + "/api/tags", timeout=2.0)
    return isinstance(data, dict) and "models" in data


_RT_CACHE = {"t": 0.0, "ok": True}


def ollama_runtime_ok() -> bool:
    """Ollama 的运行库（llama-server.exe）还在不在。

    v3.0.7 实测：这台机 Ollama 0.40.16 的 llama-server.exe 缺失，/api/tags 正常但
    /api/chat 直接 500。这里先做零成本的文件检查，坏的就别让「自动」先白打一次请求
    （省掉那 1～3 秒的首答延迟和一次报错）。找不到安装目录时放行，交给运行时判断。
    """
    now = time.monotonic()
    if now - _RT_CACHE["t"] < 60:
        return _RT_CACHE["ok"]
    roots = []
    home = os.environ.get("OLLAMA_HOME", "")
    if home:
        roots.append(home)
    la = os.environ.get("LOCALAPPDATA", "")
    if la:
        roots.append(os.path.join(la, "Programs", "Ollama"))
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        v = os.environ.get(env, "")
        if v:
            roots.append(os.path.join(v, "Ollama"))
    found_dir = False
    ok = False
    for r in roots:
        if not os.path.isdir(r):
            continue
        found_dir = True
        for cand in (os.path.join(r, "lib", "ollama", "llama-server.exe"),
                     os.path.join(r, "llama-server.exe")):
            if os.path.exists(cand):
                ok = True
                break
        if ok:
            break
    if not found_dir:
        ok = True          # 没装/位置特殊，不误判
    _RT_CACHE.update({"t": now, "ok": ok})
    return ok


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
    """本地推理后端：优先 Ollama，没有就自己拉 dafeiyu-server。"""

    def __init__(self, config: dict):
        self.config = config
        self.port = int(config.get("llm_port", DEFAULT_PORT))
        self.proc = None
        self.ready = False
        self.last_error = ""
        # v3.0.4：最后一次推理时间，用来做"空闲自动卸载"（4B 模型常驻约 2.3GB）
        self.last_used = 0.0
        # Ollama 装了但运行库缺失时会 500；记下来，后续直接用自带 dafeiyu 引擎
        self.ollama_broken = False
        # v3.0.9 调配机制：同一时刻只放一个推理请求（引擎只有 1 个 slot），
        # 其余请求排队，避免两路并发互相抢 slot 导致双双超时。
        self._chat_lock = threading.Lock()
        self.active_model = ""       # 实际加载成功的模型
        self.fallback_note = ""      # 降级说明（首选模型起不来时写这里）
        self.port_auto = False       # 端口被占用时自动换过
        # v3.0.18：一旦做过角色切换或发过多模态请求，就锁定自带引擎（见 backend 注释）
        self._force_local = False
        self.active_role = ""        # 当前生效的角色（brain/fast/tool），重启时沿用

    @property
    def model_file(self) -> str:
        return str(self.config.get("llm_model_file", "") or "")

    def model(self) -> str:
        return self.active_model or model_path(self.model_file, self.config)

    def candidates(self) -> list:
        """启动时的模型候选：用户指定 → 首选名单 → 其余（小的优先，越容易起来）。

        调配的目的：某个模型因内存不足/文件损坏起不来时，自动换下一个能用的，
        而不是让用户看到「本地模型没反应」就没了下文。
        """
        out, sizes = [], []

        def _add(path: str):
            if not path or path in out:
                return
            try:
                sz = os.path.getsize(path)
            except OSError:
                sz = 0
            # 同一份权重的不同文件名（体积几乎相同）不重复当候选，免得白等一轮
            if any(abs(sz - s) < 5 * 1048576 for s in sizes):
                return
            out.append(path)
            sizes.append(sz)

        _add(self.role_model(getattr(self, "active_role", "")))
        _add(model_path(self.model_file, self.config) if self.model_file else "")
        for name in PREFERRED_MODELS:
            _add(model_path(name, self.config))
        rest = sorted(scan_models(self.config), key=lambda m: m["size_mb"])
        for m in rest:
            _add(m["path"])
        return out

    # ---------- 后端选择 ----------
    @property
    def ollama_host(self) -> str:
        return str(self.config.get("ollama_host", OLLAMA_HOST) or OLLAMA_HOST)

    @property
    def backend(self) -> str:
        """auto: 有 Ollama 用 Ollama（GPU），否则 dafeiyu.cpp（CPU）；也可强制 dafeiyu_cpp。

        v3.0.9：界面去掉了「只用 Ollama」，老配置里的 ollama 一律按 auto 处理
        （Ollama 坏过一次就固定走自带引擎，不再反复撞墙）。
        v3.0.18：角色切换 / 多模态一律走自带引擎 —— 这两个能力都是靠 --mmproj 与
        -m 指定权重实现的，Ollama 那边没有对应模型，混着用会打错端点（实测 400）。
        """
        if getattr(self, "_force_local", False):
            return "dafeiyu_cpp"
        want = str(self.config.get("llm_backend", "auto") or "auto")
        if want in ("llama_cpp", "ollama"):   # 老配置值统一降级为自动
            want = "auto"
        if want == "dafeiyu_cpp":
            return "dafeiyu_cpp"
        if self.ollama_broken:
            return "dafeiyu_cpp"
        if not ollama_alive(self.ollama_host):
            return "dafeiyu_cpp"
        if not ollama_runtime_ok():
            return "dafeiyu_cpp"
        if self.config.get("gpu_when_idle", True):
            try:
                import gpu_guard
                if gpu_guard.game_running():
                    return "dafeiyu_cpp"
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

    def health(self, force: bool = False) -> bool:
        """v3.0.22：带 3 秒缓存 + 0.6 秒超时。

        原来每次 refresh 都要在 UI 线程连一次本地服务（超时 3 秒，一次刷新调 2~4 次），
        服务没起来时面板就卡在 1.9~4 秒。健康检查是"状态展示"，不值得阻塞界面。
        """
        now = time.time()
        cached = getattr(self, "_health_cache", None)
        if (not force) and cached is not None and now - getattr(self, "_health_at", 0) < 3.0:
            return cached
        ok = False
        try:
            if self.backend == "ollama":
                ok = ollama_alive(self.ollama_host)
            else:
                with urllib.request.urlopen(self.base_url() + "/health", timeout=0.6) as r:
                    data = json.loads(r.read().decode("utf-8"))
                ok = (data.get("status") or "") in ("ok", "no slot available")
        except Exception:
            ok = False
        self._health_cache = ok
        self._health_at = now
        return ok

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
            self.active_model = self.active_model or self.model()
            return True
        if not available(self.config):
            self.last_error = ("没找到推理程序（runtime/dafeiyu/dafeiyu-server.exe）"
                               "或任何可用的 .gguf 模型")
            return False
        exe = server_exe()
        if not os.path.exists(exe):
            self.last_error = f"推理程序不存在：{exe}"
            return False
        cands = self.candidates()
        if not cands:
            self.last_error = "模型的目录里没有找到可用的 .gguf（会扫 runtime/models、数据目录的 models/workspace）"
            return False
        self._ensure_port()
        # 调配：最多试 2 个候选，第一个起不来（缺内存/文件坏）就换下一个，别让用户干等 2 分钟
        errs = []
        tried = []
        for model in cands[:2]:
            tried.append(model)
            if self._spawn_and_wait(exe, model):
                self.active_model = model
                if model != cands[0]:
                    self.fallback_note = (
                        f"首选 {os.path.basename(cands[0])} 起不来，已自动换成 "
                        f"{os.path.basename(model)}")
                return True
            errs.append(f"{os.path.basename(model)}：{self.last_error}")
        self.last_error = "；".join(errs) if errs else "没有可加载的模型"
        self.active_model = ""
        self.fallback_note = self.last_error
        return False

    def _ensure_port(self) -> int:
        """配置端口被别的程序占了就自动换一个，避免「本地模型连不上」其实只是端口冲突。"""
        if _port_free(self.port):
            return self.port
        for p in range(DEFAULT_PORT, DEFAULT_PORT + 30):
            if p != self.port and _port_free(p):
                self.port_auto = True
                self.fallback_note = (self.fallback_note + "；" if self.fallback_note else "") + \
                    f"端口被占用，已改用 {p}"
                self.port = p
                return p
        return self.port

    def _spawn_and_wait(self, exe: str, model: str) -> bool:
        """起一个引擎进程并等它加载完（最多 60 秒）。"""
        ctx = str(int(self.config.get("llm_ctx", 4096)))
        threads = str(max(2, min(8, (os.cpu_count() or 4) // 2)))
        args = [exe, "-m", model, "-c", ctx, "-t", threads, "--port", str(self.port),
                "--host", "127.0.0.1",
                # qwen3.5 / Gemma 默认会先写思考，把 max_tokens 吃光（实测 content 为空）
                "-rea", "off",
                # v3.0.4：桌宠只会有一个人说话，4 个 slot 白占 KV 内存（实测 -np 1 省 155MB）
                "-np", "1"]
        # v3.0.18：多模态。权重是纯文本的（gemma4 / gemma3n 这类 any-to-any 模型另带
        #   视觉/音频投影），要有匹配的 mmproj 才认得图；没有就不加参数，行为与以前一致。
        mm = self.mmproj_for(model)
        if mm:
            args += ["--mmproj", mm, "-mmdev", "none"]
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
        # v3.0.4：绑进 Job Object，桌宠被杀/崩溃时这个子进程跟着死，不留孤儿进程吃 2.3GB
        try:
            import proc_guard
            proc_guard.attach(self.proc)
        except Exception:  # noqa: BLE001
            pass
        self.last_used = time.monotonic()
        # 最多等 60 秒加载模型
        for _ in range(120):
            if self.proc.poll() is not None:
                self.last_error = (f"{os.path.basename(model)} 加载时进程退出"
                                   "（多半是内存不够或模型文件损坏，详见 runtime/dafeiyu-server.log）")
                self.stop()
                return False
            if self.health():
                self.ready = True
                self.last_error = ""
                return True
            time.sleep(0.5)
        self.last_error = f"{os.path.basename(model)} 加载超时（60s）"
        self.stop()
        return False

    def mmproj_for(self, model: str) -> str:
        """v3.0.18：给这个权重找配套的多模态投影文件；没有就返回空（不传 --mmproj）。

        优先 config["llm_mmproj"] 显式指定；否则在模型同目录找 mmproj*.gguf，
        文件名里带模型主干的（gemma4-e2b-it → e2b）优先；只有一个就用它。
        """
        explicit = str(self.config.get("llm_mmproj", "") or "").strip()
        if explicit and os.path.exists(explicit):
            return explicit
        base = os.path.basename(model or "").lower()
        stem = base[:-5] if base.endswith(".gguf") else base
        d = os.path.dirname(model or "")
        if not stem or not d or not os.path.isdir(d):
            return ""
        cands = []
        try:
            for f in os.listdir(d):
                low = f.lower()
                if low.endswith(".gguf") and low.startswith("mmproj"):
                    cands.append(os.path.join(d, f))
        except OSError:
            return ""
        if not cands:
            return ""
        parts = [p for p in stem.replace("_", "-").replace(".", "-").split("-")
                 if len(p) >= 2]
        for c in cands:
            cl = os.path.basename(c).lower()
            if any(p in cl for p in parts):
                return c
        return cands[0] if len(cands) == 1 else ""

    def _mem_free_mb(self) -> int:
        """可用物理内存（MB）；拿不到就给个很大的数，宁可不拦也别把能用的停掉。"""
        try:
            import psutil
            return int(psutil.virtual_memory().available / 1048576)
        except Exception:  # noqa: BLE001
            return 999999

    def role_model(self, role: str) -> str:
        """v3.0.17：三个角色各自的模型文件（brain 大脑 / fast 快反 / tool 工具人）。"""
        roles = self.config.get("model_roles")
        if not isinstance(roles, dict) or not roles:
            roles = {"brain": "qwen35-4b-Q4_K_M.gguf",
                     "tool": "deepseek-coder-6.7b-instruct.gguf",
                     "fast": "gemma4-e2b-it.gguf"}
        name = str(roles.get(role, "") or "").strip()
        if not name:
            return ""
        try:
            return resolve_model(name, self.config)
        except Exception:  # noqa: BLE001
            return ""

    def ensure_role(self, role: str) -> bool:
        """确保当前加载的就是这个角色该用的模型；本来就是就不动，不是就换（有内存闸）。

        切换 = 停掉再起，秒级到十几秒，所以只在角色真的变了才做；
        可用内存不够装新模型时宁可不切，继续用当前模型（返回 True，不打断这次对话）。
        """
        want = self.role_model(role)
        if not want or not os.path.exists(want):
            return True
        # 角色切换必然是用 -m 指定权重起自带引擎，锁定后端，别让 dispatch 再去问 Ollama
        self._force_local = True
        cur = self.active_model or ""
        if cur and os.path.basename(cur) == os.path.basename(want) and self.health():
            self.active_role = role
            return True
        try:
            need_mb = os.path.getsize(want) / 1048576
        except OSError:
            need_mb = 0
        if need_mb and self._mem_free_mb() < need_mb * 1.15:
            self.fallback_note = (f"可用内存不足 {need_mb:.0f}MB，暂不切换 "
                                  f"{os.path.basename(want)}")
            return True
        with self._chat_lock:
            if self.is_running():
                self.stop()
            self.active_model = ""
            exe = server_exe()
            if not os.path.exists(exe):
                return False
            self._ensure_port()
            ok = self._spawn_and_wait(exe, want)
            if ok:
                self.active_model = want
                self.active_role = role
            return ok

    def dispatch(self, messages: list, max_tokens: int = 220, temperature: float = 0.7,
                 timeout: int = 90, fmt: str | None = None, retry: bool = True):
        """统一调度入口（v3.0.9）：串行化 + 确保就绪 + 失败自愈。

        为什么要串行：引擎只开 1 个 slot（-np 1），聊天和指令解析两路同时打进来时，
        后到的会排队到超时。这里加锁排队，先来的先答，第二个等它答完再发。
        为什么要自愈：引擎进程活着但连接断了（比如被系统回收显卡上下文），
        重启一次通常就好，比直接给用户报错强。
        """
        with self._chat_lock:
            if self.backend == "ollama":
                if not self.health():
                    self.start()
            elif not self.is_running() or not self.health():
                # 进程活着但 /health 不通（显卡上下文被回收、端口被抢）也当没起来，重启一轮
                self.stop()
                if not self.start():
                    return False, self.last_error or "local_start_failed"
            ok, out = self.chat(messages, max_tokens, temperature, timeout, fmt)
            if ok:
                return True, out
            if retry and out in ("local_offline", "local_http_500", "local_http_404",
                                 "local_error", "local_empty", "local_not_ready"):
                self.stop()
                time.sleep(0.4)
                if self.start():
                    ok2, out2 = self.chat(messages, max_tokens, temperature, timeout, fmt)
                    if ok2:
                        return True, out2
                    return False, out2
            return False, out

    def status(self) -> dict:
        """给面板看的调度状态：用哪个模型、端口、有没有降级或排队。"""
        m = self.model()
        return {
            "backend": self.backend,
            "model": os.path.basename(m) if m else "",
            "model_path": m,
            "running": self.is_running(),
            "ready": self.ready,
            "port": self.port,
            "port_auto": self.port_auto,
            "fallback": self.fallback_note,
            "last_error": self.last_error,
            "busy": self._chat_lock.locked(),
            "idle_min": round(self.idle_minutes(), 1),
        }

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
            # v3.0.7 实测：Ollama 的 llama-server.exe 丢了之后，/api/chat 会返回 500 或 404
            # （报 "llama-server binary not found"）。不管哪种，都记一笔、立刻用自带引擎重试，
            # 不能因为 Ollama 坏了就让用户聊不了天。
            body = ""
            try:
                body = (e.read() or b"").decode("utf-8", "ignore")[:180]
            except Exception:  # noqa: BLE001
                pass
            self.last_error = f"ollama_http_{e.code}: {body}"
            self.ollama_broken = True
            try:
                if not self.is_running():
                    self.start()   # backend 已切到 dafeiyu_cpp，这里把自带引擎拉起来
            except Exception:  # noqa: BLE001
                pass
            if self.ready or self.health():
                return self._chat_local(messages, max_tokens, temperature, timeout, fmt)
            return False, f"local_http_{e.code}"
        except urllib.error.URLError:
            return False, "local_offline"
        except Exception:  # noqa: BLE001
            return False, "local_error"

    def chat(self, messages: list, max_tokens: int = 220, temperature: float = 0.7,
             timeout: int = 90, fmt: str | None = None):
        """返回 (ok, text_or_reason)。fmt="json" 时强制结构化输出（Ollama / 自带引擎都支持）。"""
        # v3.0.18：带图的消息只能走自带引擎（Ollama 的 /api/chat 用 images 字段，
        # OpenAI 兼容层的 content 数组格式在两条路径上表现不一致，实测会 400）
        if _has_image(messages):
            self._force_local = True
        if not self.ready and not self.health():
            if not self.ollama_broken:
                return False, "local_not_ready"
            self.start()        # Ollama 已经坏了，先把自带引擎拉起来再说话
        self.last_used = time.monotonic()
        # Ollama 坏过一次就别再问它（用户可能根本没修），直接用自带引擎
        if self.backend == "ollama" and not self.ollama_broken:
            return self._chat_ollama(messages, max_tokens, temperature, timeout, fmt)
        if not self.is_running():
            self.start()
        return self._chat_local(messages, max_tokens, temperature, timeout, fmt)

    # ---------- 空闲卸载 ----------
    def idle_minutes(self) -> float:
        if not self.last_used:
            return 0.0
        return (time.monotonic() - self.last_used) / 60.0

    def should_unload(self, limit_min: float) -> bool:
        """空闲够了就把自带引擎停掉，把 2.3GB 模型内存还给系统。"""
        if limit_min <= 0 or not self.is_running():
            return False
        return self.idle_minutes() >= limit_min

    def _chat_local(self, messages, max_tokens, temperature, timeout, fmt):
        body = {
            "model": "local",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if fmt:  # dafeiyu.cpp server 用 GBNF 约束成 json 对象
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
                 temperature: float = 0.7, fmt: str | None = None, role: str = ""):
        super().__init__()
        self.manager = manager
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.fmt = fmt
        self.role = role          # v3.0.17：brain / fast / tool，空 = 不指定
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if self._stop:
            return
        # v3.0.9：统一走 dispatch（串行排队 + 起不来先拉起 + 断了重启一次）
        # v3.0.17：先按角色换到该用的模型（切不动就继续用现有的，不打断这次回答）
        if self.role:
            try:
                self.manager.ensure_role(self.role)
            except Exception:  # noqa: BLE001
                pass
        ok, out = self.manager.dispatch(self.messages, self.max_tokens, self.temperature,
                                        fmt=self.fmt)
        if self._stop:
            return
        if ok:
            self.reply_ready.emit(out)
        else:
            self.failed.emit(out)

