# -*- coding: utf-8 -*-
"""Ollama 官方模型库接入（不依赖 Ollama 进程）。

两个方向：
1. 联网：抓 ollama.com 的库页拿模型名，查 registry manifest 拿权重 blob 直链，
   下载下来就是标准 GGUF，直接喂给自带引擎 dafeiyu-server（全程不启动 Ollama）。
2. 离线：读本机 OLLAMA_MODELS 目录里的 manifests + blobs，把权重 blob 复制成 .gguf。

v3.0.7 实测（本机）：
  - registry.ollama.ai/v2/library/qwen3.5/manifests/4b → 200，layers 里
    application/vnd.ollama.image.model 的 blob 开头就是 b"GGUF"
  - ollama.com/library 页能抓到 272 个模型名
  - ollama.com/library/<name>/tags 页能抓到 tag 与大小（同一 tag 出现两次，去重即可）
"""
import glob
import json
import os
import re
import shutil
import time
import urllib.request

from PySide6.QtCore import QThread, Signal

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ACCEPT_MANIFEST = ("application/vnd.docker.distribution.manifest.v2+json,"
                   "application/vnd.oci.image.manifest.v1+json")

LIB_URL = "https://ollama.com/library"
TAGS_URL = "https://ollama.com/library/{name}/tags"
MANIFEST_URL = "https://registry.ollama.ai/v2/library/{name}/manifests/{tag}"
BLOB_URL = "https://registry.ollama.ai/v2/library/{name}/blobs/{digest}"
MODEL_MEDIA = "application/vnd.ollama.image.model"

_CACHE_TTL = 12 * 3600


def _fetch(url: str, headers: dict = None, timeout: int = 25) -> bytes:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _cache_file() -> str:
    try:
        from paths import data_dir
        return os.path.join(data_dir(), "ollama_library.json")
    except Exception:  # noqa: BLE001
        return ""


# ---------------- 联网：库列表 ----------------

def library(refresh: bool = False) -> list:
    """Ollama 官方库模型名单（联网抓取，带 12 小时缓存）。

    返回 [{"name","desc","source":"ollama"}]。拿不到网络时返回缓存或空列表。
    """
    cf = _cache_file()
    if not refresh and cf and os.path.exists(cf):
        try:
            with open(cf, encoding="utf-8") as f:
                d = json.load(f)
            if time.time() - float(d.get("at", 0)) < _CACHE_TTL and d.get("models"):
                return d["models"]
        except (OSError, ValueError):
            pass
    try:
        html = _fetch(LIB_URL).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        if cf and os.path.exists(cf):
            try:
                with open(cf, encoding="utf-8") as f:
                    return json.load(f).get("models") or []
            except (OSError, ValueError):
                pass
        return []
    out, seen = [], set()
    # 每张卡片：<a href="/library/NAME" ...> <span ...>NAME</span> <p ...>描述</p>
    for m in re.finditer(r'<a href="/library/([a-zA-Z0-9._\-]+)"[^>]*>(.*?)</a>',
                         html, re.S):
        name, block = m.group(1), m.group(2)
        if name in seen:
            continue
        seen.add(name)
        pm = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
        desc = re.sub(r"<[^>]+>", "", pm.group(1)).strip()[:120] if pm else ""
        out.append({"name": name, "desc": desc, "source": "ollama"})
    if out and cf:
        try:
            with open(cf, "w", encoding="utf-8") as f:
                json.dump({"at": time.time(), "models": out}, f, ensure_ascii=False)
        except OSError:
            pass
    return out


def tags(name: str) -> list:
    """某个模型的所有 tag + 体积（GB）。抓不到返回空。"""
    try:
        html = _fetch(TAGS_URL.format(name=name)).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return []
    out, seen = [], set()
    # 每个 tag 出现两次（移动端/桌面端各一份），按出现顺序配体积
    tag_iter = list(re.finditer(rf'href="/library/{re.escape(name)}:([a-zA-Z0-9._\-]+)"', html))
    for m in tag_iter:
        tag = m.group(1)
        if tag in seen:
            continue
        seen.add(tag)
        tail = html[m.end():m.end() + 1200]
        sm = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB)", tail)
        size_gb = 0.0
        if sm:
            v = float(sm.group(1))
            size_gb = v if sm.group(2) == "GB" else v / 1024.0
        out.append({"tag": tag, "size_gb": round(size_gb, 2)})
    return out


def manifest(name: str, tag: str = "latest") -> dict:
    """查 registry manifest，返回权重 blob 的直链与大小。"""
    try:
        raw = _fetch(MANIFEST_URL.format(name=name, tag=tag),
                     {"Accept": ACCEPT_MANIFEST})
        d = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    model = projector = None
    for l in d.get("layers") or []:
        mt = l.get("mediaType") or ""
        if mt == MODEL_MEDIA:
            model = l
        elif "projector" in mt:
            projector = l
    if not model:
        return {}
    return {
        "model_digest": model.get("digest", ""),
        "model_size": int(model.get("size") or 0),
        "model_url": BLOB_URL.format(name=name, digest=model.get("digest", "")),
        "projector_digest": (projector or {}).get("digest", ""),
        "projector_size": int((projector or {}).get("size") or 0),
    }


def dest_name(name: str, tag: str) -> str:
    """落盘文件名：qwen3.5-4b.gguf（带 tag，避免不同量化互相覆盖）。"""
    safe = re.sub(r"[^\w.\-]+", "_", f"{name}-{tag}")
    return safe + ".gguf"


# ---------------- 离线：本机 Ollama 的模型 ----------------

def ollama_models_root() -> str:
    env = (os.environ.get("OLLAMA_MODELS") or "").strip()
    if env and os.path.isdir(env):
        return env
    home = os.path.join(os.path.expanduser("~"), ".ollama", "models")
    return home if os.path.isdir(home) else ""


def local_installs() -> list:
    """本机 Ollama 里已下载的模型（读 manifests，不启动 Ollama）。

    返回 [{"name","tag","blob","size_mb","model_path"}]，blob 为空表示权重缺失。
    manifests 与 manifests-v2 可能重复登记同一个模型，按 (name, tag) 去重。
    """
    root = ollama_models_root()
    if not root:
        return []
    blobs = os.path.join(root, "blobs")
    out, seen = [], set()
    for base in (os.path.join(root, "manifests"),
                 os.path.join(root, "manifests-v2")):
        if not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "**", "*"), recursive=True):
            if not os.path.isfile(path):
                continue
            rel = os.path.relpath(path, base).replace("\\", "/").split("/")
            if len(rel) < 3:      # registry/library/<name>/<tag>
                continue
            tag = rel[-1]
            name = rel[-2]
            if name.startswith("sha256"):   # manifests-v2 另有布局，跳过
                continue
            key = (name, tag)
            if key in seen:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, ValueError):
                continue
            blob = ""
            size = 0
            for l in d.get("layers") or []:
                if (l.get("mediaType") or "") == MODEL_MEDIA:
                    dg = (l.get("digest") or "").replace("sha256:", "sha256-")
                    blob = os.path.join(blobs, dg)
                    try:
                        size = int(l.get("size") or 0)
                    except (TypeError, ValueError):
                        size = 0
                    break
            if not size and blob and os.path.exists(blob):
                size = os.path.getsize(blob)
            seen.add(key)
            out.append({"name": name, "tag": tag, "model_path": "",
                        "blob": blob if os.path.exists(blob) else "",
                        "size_mb": size / 1048576})
    out.sort(key=lambda m: (-m["size_mb"], m["name"]))
    return out


def import_all(models_dir: str, skip_existing: bool = True,
               skip_dirs: list = None) -> dict:
    """把本机 Ollama 的权重 blob 复制成 <models_dir>\\<name>-<tag>.gguf。

    不启动 Ollama、不联网。skip_dirs 里已经有同名文件的也算「已存在」，
    免得同一份 2.5GB 权重在两个目录各存一份。
    """
    stats = {"copied": 0, "skipped": 0, "bytes": 0, "items": [], "errors": []}
    try:
        os.makedirs(models_dir, exist_ok=True)
    except OSError as e:
        stats["errors"].append(f"建目录失败：{e}")
        return stats
    for m in local_installs():
        if not m["blob"]:
            stats["errors"].append(f"{m['name']}:{m['tag']} 缺权重 blob")
            continue
        fname = dest_name(m["name"], m["tag"])
        dst = os.path.join(models_dir, fname)
        exists = os.path.exists(dst)
        for d in (skip_dirs or []):
            try:
                exists = exists or os.path.exists(os.path.join(d, fname))
            except (OSError, TypeError):
                continue
        if skip_existing and exists:
            stats["skipped"] += 1
            stats["items"].append({"name": m["name"], "tag": m["tag"],
                                   "path": dst, "action": "已存在"})
            continue
        try:
            tmp = dst + ".part"
            shutil.copyfile(m["blob"], tmp)
            os.replace(tmp, dst)
            stats["copied"] += 1
            stats["bytes"] += os.path.getsize(dst)
            stats["items"].append({"name": m["name"], "tag": m["tag"],
                                   "path": dst, "action": "已导入"})
        except OSError as e:
            stats["errors"].append(f"{m['name']}:{m['tag']} 复制失败：{e}")
    return stats


class OllamaImportWorker(QThread):
    """后台把 Ollama 权重搬到自带引擎的模型目录（2~10GB，不能卡界面）。"""
    done_stats = Signal(dict)

    def __init__(self, models_dir: str, skip_dirs: list = None, parent=None):
        super().__init__(parent)
        self.models_dir = models_dir
        self.skip_dirs = skip_dirs or []

    def run(self):  # noqa: D102
        try:
            self.done_stats.emit(import_all(self.models_dir, True, self.skip_dirs))
        except Exception as e:  # noqa: BLE001
            self.done_stats.emit({"copied": 0, "skipped": 0, "bytes": 0,
                                  "items": [], "errors": [str(e)[:120]]})
