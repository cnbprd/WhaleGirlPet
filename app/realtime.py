# -*- coding: utf-8 -*-
"""轻量实时监控（v3.0.21）：轮询几个高风险目录，新落地/改动的可执行文件立刻交给扫描。

为什么不用 ReadDirectoryChangesW / watchdog：桌宠是单进程 GUI，原生句柄线程还要处理
缓冲区溢出、重命名与短命文件；这里只看下载 / 临时 / 启动三个目录，2 秒轮询一次
（实测单次 < 3ms），够用，而且不会因为句柄失效而静默漏事件。
"""
import os
import threading

WATCH_EXTS = (".exe", ".dll", ".scr", ".ps1", ".bat", ".cmd", ".vbs", ".js",
              ".hta", ".msi", ".lnk")


def default_dirs() -> list:
    home = os.path.expanduser("~")
    cands = [
        os.path.join(home, "Downloads"),
        os.environ.get("TEMP", ""),
        os.path.join(os.environ.get("APPDATA", ""),
                     r"Microsoft\Windows\Start Menu\Programs\Startup"),
    ]
    return [p for p in cands if p and os.path.isdir(p)]


class DirWatcher(threading.Thread):
    """快照式轮询：记录 (mtime, size)，新增或变化就算事件。"""

    def __init__(self, dirs=None, on_new=None, interval: float = 2.0, exts=WATCH_EXTS):
        super().__init__(daemon=True)
        self.dirs = [d for d in (dirs if dirs is not None else default_dirs())
                     if d and os.path.isdir(d)]
        self.on_new = on_new
        self.interval = max(0.5, float(interval))
        self.exts = tuple(str(e).lower() for e in exts)
        self._stop = threading.Event()
        self._seen = {}
        self.seen_count = 0

    def snapshot(self) -> dict:
        out = {}
        for d in self.dirs:
            try:
                with os.scandir(d) as it:
                    for e in it:
                        try:
                            if not e.is_file(follow_symlinks=False):
                                continue
                            if not e.name.lower().endswith(self.exts):
                                continue
                            st = e.stat()
                            out[e.path] = (st.st_mtime, st.st_size)
                        except OSError:
                            continue
            except OSError:
                continue
        return out

    def prime(self) -> int:
        """先记一遍现状：启动时已有的文件不该当成「刚出现」全部报警。"""
        self._seen = self.snapshot()
        self.seen_count = len(self._seen)
        return self.seen_count

    def poll_once(self) -> list:
        now = self.snapshot()
        new = [p for p, v in now.items() if self._seen.get(p) != v]
        self._seen = now
        for p in new:
            if self.on_new:
                try:
                    self.on_new(p)
                except Exception:  # noqa: BLE001
                    pass
        return new

    def stop(self):
        self._stop.set()

    def run(self):
        self.prime()
        while not self._stop.wait(self.interval):
            self.poll_once()
