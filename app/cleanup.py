# -*- coding: utf-8 -*-
"""安全清理电脑垃圾：只扫临时目录中超过 N 天未占用的临时文件，被占用/无权限的跳过。

明确不触碰：桌面、文档、下载、图片、各软件的数据目录与用户个人文件。
"""
import os
import time

from PySide6.QtCore import QThread, Signal

OLDER_DAYS = 7


def _temp_dirs():
    dirs = []
    t = os.environ.get("TEMP") or os.environ.get("TMP")
    if t:
        dirs.append(t)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "Temp"))
    windir = os.environ.get("WINDIR", r"C:\Windows")
    dirs.append(os.path.join(windir, "Temp"))
    # 去重、保留存在的目录
    seen, out = set(), []
    for d in dirs:
        norm = os.path.normpath(d)
        if os.path.isdir(norm) and norm.lower() not in seen:
            seen.add(norm.lower())
            out.append(norm)
    return out


def _iter_old_files(cutoff: float):
    for base in _temp_dirs():
        for root, _dirs, files in os.walk(base):
            for name in files:
                p = os.path.join(root, name)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_mtime < cutoff:
                    yield p, st.st_size


def scan(older_days: int = OLDER_DAYS):
    cutoff = time.time() - older_days * 86400
    count, total = 0, 0
    for _p, size in _iter_old_files(cutoff):
        count += 1
        total += size
    return {"files": count, "bytes": total, "dirs": _temp_dirs()}


def clean(older_days: int = OLDER_DAYS, progress_cb=None):
    cutoff = time.time() - older_days * 86400
    removed, skipped, freed = 0, 0, 0
    for p, size in _iter_old_files(cutoff):
        try:
            os.remove(p)
            removed += 1
            freed += size
        except OSError:
            skipped += 1
        if progress_cb:
            progress_cb(removed, skipped)
    return {"removed": removed, "skipped": skipped, "bytes": freed}


class CleanWorker(QThread):
    done = Signal(dict)

    def run(self):
        self.done.emit(clean())
