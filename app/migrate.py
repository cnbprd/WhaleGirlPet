# -*- coding: utf-8 -*-
"""数据目录迁移：可断点续传的复制（v3.0.22）。

背景：原实现是 `shutil.copytree(dirs_exist_ok=True)` + 立刻删旧。
模型目录 5~12GB，复制中途断网/断电/关窗口就得从头再来，用户实测要等很久。

这里的规则很简单：
1. 逐文件复制，先写 `<name>.wgp-copy` 再 os.replace，单个文件不会留半截。
2. 目标文件已存在、大小一致、mtime 相差 ≤2s → 视为已完成，跳过。
   所以中断后再点一次「迁移到这里」，只补没复制的部分（续传）。
3. 进度状态写 `migrate_state.json`（源、目标、文件数、字节数），只用于展示与诊断。
"""
import json
import os
import shutil
import time

from PySide6.QtCore import QThread, Signal

TMP_SUFFIX = ".wgp-copy"
STATE_NAME = "migrate_state.json"
MTIME_TOL = 2.0


def _walk(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if os.path.isfile(p) and not fn.endswith(TMP_SUFFIX):
                yield p


def _same(src, dst):
    try:
        s, d = os.stat(src), os.stat(dst)
    except OSError:
        return False
    return s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) <= MTIME_TOL


def plan(src, dst):
    """返回 (文件列表, 总字节, 已存在字节, 待复制字节, 待复制文件数)。"""
    files, total, done_b = [], 0, 0
    for p in _walk(src):
        rel = os.path.relpath(p, src)
        size = os.path.getsize(p)
        files.append((rel, size))
        total += size
        if _same(p, os.path.join(dst, rel)):
            done_b += size
    return files, total, done_b, total - done_b


def copy_resumable(src, dst, progress=None, should_stop=None):
    """把 src 内容复制进 dst（不复制 data_root.txt）。返回统计 dict。"""
    files, total, done_b, todo_b = plan(src, dst)
    copied_files = copied_b = skipped = 0
    t0 = time.time()
    for rel, size in files:
        if should_stop and should_stop():
            break
        s = os.path.join(src, rel)
        d = os.path.join(dst, rel)
        if rel == "data_root.txt" or _same(s, d):
            skipped += 1
            continue
        os.makedirs(os.path.dirname(d), exist_ok=True)
        tmp = d + TMP_SUFFIX
        shutil.copy2(s, tmp)
        os.replace(tmp, d)
        copied_files += 1
        copied_b += size
        done_b += size
        if progress:
            progress(done_b, total, rel)
        time.sleep(0)                      # 让 UI 线程有机会喘气
    stats = {
        "files": len(files), "total_bytes": total, "copied_files": copied_files,
        "copied_bytes": copied_b, "skipped_files": skipped,
        "bytes_before": done_b - copied_b, "seconds": round(time.time() - t0, 1),
    }
    try:
        with open(os.path.join(dst, STATE_NAME), "w", encoding="utf-8") as f:
            json.dump({"src": src, "dst": dst, **stats, "at": time.time()}, f, ensure_ascii=False)
    except OSError:
        pass
    return stats


class MigrateThread(QThread):
    """后台迁移：不卡面板；点「停止」保留已完成文件，下次接着续。"""

    progressed = Signal(int, int, str)     # 已复制字节 / 总字节 / 当前文件
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, src, dst, parent=None):
        super().__init__(parent)
        self.src, self.dst = src, dst
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            stats = copy_resumable(
                self.src, self.dst,
                progress=lambda d, t, rel: self.progressed.emit(d, t, rel),
                should_stop=lambda: self._stop)
            self.finished_ok.emit(stats)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
