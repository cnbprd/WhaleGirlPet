# -*- coding: utf-8 -*-
"""联网更新：GitHub Releases 检查 + 安装包下载 + SHA256 校验。

两种来源：
  1. GitHub Release（默认，仓库在 config["update_repo"]，如 "cnbprd/WhaleGirlPet"）
  2. 自建清单 JSON（config["update_url"]，老方式，优先级更高，留为空则走 GitHub）
"""
import hashlib
import json
import os
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

from paths import APP_VERSION, data_dir

DEFAULT_REPO = "cnbprd/WhaleGirlPet"
API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
UA = "WhaleGirlPet-Updater"


def parse_version(v: str):
    out = []
    for part in str(v).strip().lstrip("vV").split("."):
        num = "".join(ch for ch in part if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple(out)


def _get_json(url: str, timeout: int = 15) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _pick_assets(release: dict) -> dict:
    """从 release 资产里挑安装包与校验文件。"""
    assets = release.get("assets") or []
    out = {"setup": "", "exe": "", "sha": "", "all": []}
    for a in assets:
        name = str(a.get("name") or "")
        url = str(a.get("browser_download_url") or "")
        size = int(a.get("size") or 0)
        if not url:
            continue
        out["all"].append({"name": name, "url": url, "size": size})
        low = name.lower()
        if low.endswith(".sha256"):
            out["sha"] = out["sha"] or url
        elif low.endswith("setup.exe") or "setup-" in low:
            out["setup"] = out["setup"] or url
        elif low.endswith(".exe"):
            out["exe"] = out["exe"] or url
    return out


class UpdateWorker(QThread):
    result = Signal(dict)

    def __init__(self, repo: str = "", manifest_url: str = ""):
        super().__init__()
        self.repo = (repo or "").strip()
        self.manifest_url = (manifest_url or "").strip()

    def run(self):
        if self.manifest_url:
            self._manifest()
        else:
            self._github()

    def _manifest(self):
        try:
            data = _get_json(self.manifest_url)
        except urllib.error.HTTPError as e:
            self.result.emit({"status": f"http_{e.code}", "current": APP_VERSION})
            return
        except urllib.error.URLError:
            self.result.emit({"status": "offline", "current": APP_VERSION})
            return
        except (ValueError, TimeoutError, OSError):
            self.result.emit({"status": "parse", "current": APP_VERSION})
            return
        latest = str(data.get("version", "")).strip()
        self.result.emit({
            "status": "ok", "source": "manifest", "current": APP_VERSION,
            "latest": latest, "notes": str(data.get("notes", "")),
            "url": str(data.get("url", "")), "setup": str(data.get("url", "")),
            "sha": "",
            "newer": bool(latest) and parse_version(latest) > parse_version(APP_VERSION),
        })

    def _github(self):
        repo = self.repo or DEFAULT_REPO
        try:
            rel = _get_json(API_LATEST.format(repo=repo))
        except urllib.error.HTTPError as e:
            self.result.emit({"status": f"http_{e.code}", "current": APP_VERSION, "repo": repo})
            return
        except urllib.error.URLError:
            self.result.emit({"status": "offline", "current": APP_VERSION, "repo": repo})
            return
        except (ValueError, TimeoutError, OSError):
            self.result.emit({"status": "parse", "current": APP_VERSION, "repo": repo})
            return
        latest = str(rel.get("tag_name") or "").strip()
        assets = _pick_assets(rel)
        html = str(rel.get("html_url") or "")
        self.result.emit({
            "status": "ok", "source": "github", "repo": repo,
            "current": APP_VERSION, "latest": latest,
            "notes": str(rel.get("body") or "")[:2000],
            "url": html, "setup": assets["setup"], "exe": assets["exe"],
            "sha": assets["sha"], "assets": assets["all"],
            "size": next((a["size"] for a in assets["all"]
                          if a["url"] == (assets["setup"] or assets["exe"])), 0),
            "newer": bool(latest) and parse_version(latest) > parse_version(APP_VERSION),
        })


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_dir() -> str:
    d = os.path.join(data_dir(), "updates")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


class DownloadWorker(QThread):
    progress = Signal(int, int, int)   # 百分比, 已下载字节, 总字节
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, dest_name: str, sha_url: str = ""):
        super().__init__()
        self.url = (url or "").strip()
        self.dest_name = os.path.basename(dest_name or "WhaleGirlPet-Setup.exe")
        self.sha_url = (sha_url or "").strip()
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        if not self.url:
            self.failed.emit("下载地址为空")
            return
        dest = os.path.join(download_dir(), self.dest_name)
        part = dest + ".part"
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp, open(part, "wb") as f:
                total = int(resp.headers.get("Content-Length") or 0)
                got = 0
                while True:
                    if self._stop:
                        raise RuntimeError("已取消")
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    pct = int(got * 100 / total) if total else 0
                    self.progress.emit(pct, got, total)
            if self.sha_url:
                expect = ""
                with urllib.request.urlopen(
                        urllib.request.Request(self.sha_url, headers={"User-Agent": UA}),
                        timeout=15) as r:
                    expect = r.read().decode("utf-8", "ignore").split()[0].strip().lower()
                actual = _sha256(part)
                if expect and actual != expect:
                    os.remove(part)
                    self.failed.emit(f"SHA256 校验失败（期望 {expect[:12]}…，实际 {actual[:12]}…）")
                    return
            os.replace(part, dest)
            self.done.emit(dest)
        except Exception as e:  # noqa: BLE001
            try:
                if os.path.exists(part):
                    os.remove(part)
            except OSError:
                pass
            self.failed.emit(str(e)[:160])
