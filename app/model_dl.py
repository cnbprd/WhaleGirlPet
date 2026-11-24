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


def local_models() -> list:
    """列出 runtime/models 下已有的 .gguf。"""
    from paths import runtime_dir
    base = os.path.join(runtime_dir(), "models")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        if name.lower().endswith(".gguf"):
            out.append({
                "name": name,
                "size_mb": os.path.getsize(os.path.join(base, name)) / (1024 * 1024),
                "path": os.path.join(base, name),
            })
    return out
