# -*- coding: utf-8 -*-
"""GGUF 模型下载线程：流式写盘、断点续传（.part）、进度与取消。

只下单文件模型；分片模型在清单里只给仓库页，不走这里。
"""
import os
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

CHUNK = 1 << 20
UA = "WhaleGirlPet/2.0 (+local)"


class ModelDownloader(QThread):
    progress = Signal(str, int, int)   # id, 已下字节, 总字节
    done = Signal(str, str)            # id, 落盘路径
    failed = Signal(str, str)          # id, 原因

    def __init__(self, item_id: str, url: str, dest_path: str, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.url = url
        self.dest = dest_path
        self._stop = False
        self.speed = 0.0

    def stop(self):
        self._stop = True

    def run(self):  # noqa: D102
        tmp = self.dest + ".part"
        os.makedirs(os.path.dirname(self.dest), exist_ok=True)
        pos = 0
        if os.path.exists(tmp):
            pos = os.path.getsize(tmp)
            if pos == 0:
                os.remove(tmp)
        headers = {"User-Agent": UA}
        if pos > 0:
            headers["Range"] = f"bytes={pos}-"
        try:
            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                code = getattr(r, "status", 200)
                if pos > 0 and code == 200:
                    # 服务器不支持断点续传，从头开始
                    pos = 0
                total = int(r.headers.get("Content-Length") or 0) + pos
                mode = "ab" if pos > 0 else "wb"
                import time
                t0 = time.time()
                base = pos
                with open(tmp, mode) as f:
                    while not self._stop:
                        buf = r.read(CHUNK)
                        if not buf:
                            break
                        f.write(buf)
                        pos += len(buf)
                        dt = time.time() - t0
                        self.speed = (pos - base) / dt if dt > 0.5 else 0.0
                        self.progress.emit(self.item_id, pos, total)
            if self._stop:
                self.failed.emit(self.item_id, "已取消（已下部分保留，可续传）")
                return
            if total and pos < total:
                self.failed.emit(self.item_id, "连接提前结束，可重试续传")
                return
            os.replace(tmp, self.dest)
            self.done.emit(self.item_id, self.dest)
        except urllib.error.HTTPError as e:
            self.failed.emit(self.item_id, f"HTTP {e.code}")
        except urllib.error.URLError:
            self.failed.emit(self.item_id, "网络不可用")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(self.item_id, str(e)[:120])


def resolve_gguf_url(url: str):
    """把用户给的地址解析成 (可直下的 .gguf 直链, 文件名)，解析不出返回 ("", "")。

    支持三种形态：
    1. 本身就是 xxx.gguf 直链；
    2. hf-mirror.com / huggingface.co 的仓库页（查 /api/models 的文件清单，优先 Q4 量化）；
    3. 其它网页：抓页面里的 .gguf 链接（取第一个）。
    """
    import json
    import re

    u = (url or "").strip()
    if not u:
        return "", ""
    if u.split("?")[0].lower().endswith(".gguf"):
        return u, u.split("?")[0].rsplit("/", 1)[-1]

    m = re.match(r"https?://(?:www\.)?(hf-mirror\.com|huggingface\.co)/(.+?)/([^/\s?#]+)",
                 u, re.I)
    if m:
        host, org, repo = m.group(1), m.group(2), m.group(3)
        api = f"https://{host}/api/models/{org}/{repo}"
        req = urllib.request.Request(api, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            fnames = [s.get("rfilename", "") for s in data.get("siblings", [])]
        except Exception:  # noqa: BLE001
            fnames = []
        cand = [f for f in fnames if f.lower().endswith(".gguf")]
        if not cand:
            return "", ""
        q4 = [f for f in cand if "q4" in f.lower() and "mmproj" not in f.lower()]
        pick = (q4 or [f for f in cand if "mmproj" not in f.lower()] or cand)[0]
        return f"https://{host}/{org}/{repo}/resolve/main/{pick}", os.path.basename(pick)

    # 兜底：当普通网页抓 .gguf 链接
    req = urllib.request.Request(u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "ignore")
        hits = re.findall(r'https?://[^\s"\'<>]+\.gguf', html)
        if hits:
            return hits[0], hits[0].rsplit("/", 1)[-1]
    except Exception:  # noqa: BLE001
        pass
    return "", ""


def local_models(config: dict = None) -> list:
    """列出所有能扫到的 .gguf（v3.0.7 起跨目录：程序 runtime/models、数据目录 models/workspace）。"""
    try:
        import local_llm
        return local_llm.scan_models(config)
    except Exception:  # noqa: BLE001
        pass
    from paths import runtime_dir
    base = os.path.join(runtime_dir(), "models")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        if name.lower().endswith(".gguf"):
            p = os.path.join(base, name)
            out.append({"name": name,
                        "size_mb": os.path.getsize(p) / (1024 * 1024),
                        "path": p, "dir": base})
    return out
