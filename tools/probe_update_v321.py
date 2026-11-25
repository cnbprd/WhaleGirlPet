# -*- coding: utf-8 -*-
"""更新链路探针：检查更新 → 下载 → 校验，哪一步断了一目了然。

    python tools/probe_update_v321.py [--full]
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QCoreApplication, QTimer  # noqa: E402

import updater  # noqa: E402

QCoreApplication([])


def wait_thread(t, timeout_s=240):
    """跑事件循环等 QThread 信号回来，返回 (payload, 错误)。"""
    out = {}

    def ok(*a):
        out["done"] = a

    def bad(msg):
        out["failed"] = msg

    t.done.connect(ok)
    t.failed.connect(bad)
    t.start()
    t0 = time.time()
    while not out and time.time() - t0 < timeout_s:
        QCoreApplication.processEvents()
        time.sleep(0.05)
    if not out:
        try:
            t.stop()
        except Exception:  # noqa: BLE001
            pass
        t.wait(4000)
    return out


def main():
    full = "--full" in sys.argv
    print("[1] 检查更新（直连 GitHub latest）")
    info = {}
    w = updater.UpdateWorker("cnbprd/WhaleGirlPet")
    w.result.connect(lambda d: info.update(d))
    w.start()
    t0 = time.time()
    while not info and time.time() - t0 < 30:
        QCoreApplication.processEvents()
        time.sleep(0.05)
    w.wait(2000)
    print("    status =", info.get("status"), "| latest =", info.get("latest"),
          "| newer =", info.get("newer"))
    print("    setup  =", info.get("setup"))
    print("    sha    =", info.get("sha"))
    print("    size   =", f"{int(info.get('size') or 0) / 1048576:.1f} MB")

    print("[2] 下载 .sha256 小文件（验证 https 白名单 + 重定向 + 落盘）")
    sha_url = info.get("sha") or ""
    if not sha_url:
        print("    FAIL 没有 sha 资产 URL")
    else:
        print("    sha 文件 =", sha_url.split("/")[-1])
        name = sha_url.split("/")[-1]
        r = wait_thread(updater.DownloadWorker(
            sha_url, name, asset_id=int(info.get("sha_id") or 0),
            repo=str(info.get("repo") or ""), sha_asset_id=0), 90)
        if "done" in r:
            p = r["done"][0]
            print("    ok", p, os.path.getsize(p), "bytes")
            print("    内容 =", open(p, encoding="utf-8").read().strip()[:80])
        else:
            print("    FAIL", r.get("failed"))

    if full and info.get("setup"):
        print("[3] 下载安装包（真实大小，验证完整链路 + 校验）")
        name = info["setup"].split("/")[-1]
        r = wait_thread(updater.DownloadWorker(
            info["setup"], name, info.get("sha") or "",
            asset_id=int(info.get("setup_id") or 0), repo=str(info.get("repo") or ""),
            sha_asset_id=int(info.get("sha_id") or 0)), 900)
        if "done" in r:
            p = r["done"][0]
            print("    ok", p, f"{os.path.getsize(p) / 1048576:.1f} MB")
        else:
            print("    FAIL", r.get("failed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
