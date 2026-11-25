# -*- coding: utf-8 -*-
"""联网更新：GitHub Releases 检查 + 安装包下载 + SHA256 校验。

两种来源：
  1. GitHub Release（默认，仓库在 config["update_repo"]，如 "cnbprd/WhaleGirlPet"）
  2. 自建清单 JSON（config["update_url"]，老方式，优先级更高，留为空则走 GitHub）
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import QThread, Signal

from paths import APP_VERSION, data_dir

DEFAULT_REPO = "cnbprd/WhaleGirlPet"
API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
UA = "WhaleGirlPet-Updater"


def url_is_safe(url: str) -> bool:
    """只允许 https 下载；http 仅放行本机回环（自建清单本地调试）。

    起因（v3.0.21 审计）：更新包是会被直接执行的 exe，明文 http 下载等于把安装过程
    交给中间人；老版本只做了 SHA 校验，而 SHA 只在 release 带 .sha256 时才有。
    """
    try:
        p = urllib.parse.urlsplit(str(url or "").strip())
    except ValueError:
        return False
    if p.scheme == "https" and p.hostname:
        return True
    if p.scheme == "http" and p.hostname in ("127.0.0.1", "localhost"):
        return True
    return False


def parse_sha_text(text: str) -> str:
    """从 .sha256 文件里取哈希：兼容 `hash  file`、`SHA256 (file) = hash`、纯 hash。"""
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            line = line.rsplit("=", 1)[-1].strip()
        token = line.split()[0].strip().lower()
        if len(token) == 64 and all(c in "0123456789abcdef" for c in token):
            return token
    return ""



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
    """从 release 资产里挑安装包和**与之同名**的校验文件。

    v3.0.22 修 bug：原来按「第一个 .sha256」取，实际拿到的是 portable.zip 的哈希，
    Setup 下完 62MB 必然校验失败（用户反馈"点了没反应"）。校验文件必须跟安装包同名。
    """
    assets = release.get("assets") or []
    out = {"setup": "", "exe": "", "sha": "", "all": [],
           "setup_id": 0, "exe_id": 0, "sha_id": 0}
    for a in assets:
        name = str(a.get("name") or "")
        url = str(a.get("browser_download_url") or "")
        size = int(a.get("size") or 0)
        aid = int(a.get("id") or 0)
        if not url:
            continue
        out["all"].append({"name": name, "url": url, "size": size, "id": aid})
        low = name.lower()
        if low.endswith(".sha256"):
            continue          # 校验文件放到最后按名字配对
        if low.endswith("setup.exe") or "setup-" in low:
            if not out["setup"]:
                out["setup"], out["setup_id"] = url, aid
        elif low.endswith(".exe") and not out["exe"]:
            out["exe"], out["exe_id"] = url, aid
    chosen = os.path.basename(out["setup"] or out["exe"]).lower()
    if chosen:
        for a in out["all"]:
            if a["name"].lower() == chosen + ".sha256":
                out["sha"], out["sha_id"] = a["url"], a["id"]
                break
    if not out["sha"]:
        for a in out["all"]:
            n = a["name"].lower()
            if n.endswith(".sha256") and "setup" in n:
                out["sha"], out["sha_id"] = a["url"], a["id"]
                break
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
            # v3.0.22：带资产 id，下载优先走 API 资产接口（绕开连不上的 releases/download 域名）
            "setup_id": assets.get("setup_id", 0), "exe_id": assets.get("exe_id", 0),
            "sha_id": assets.get("sha_id", 0),
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


API_ASSET = "https://api.github.com/repos/{repo}/releases/assets/{aid}"


class DownloadWorker(QThread):
    progress = Signal(int, int, int)   # 百分比, 已下载字节, 总字节
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, dest_name: str, sha_url: str = "",
                 asset_id: int = 0, repo: str = "", sha_asset_id: int = 0):
        super().__init__()
        self.url = (url or "").strip()
        self.dest_name = os.path.basename(dest_name or "WhaleGirlPet-Setup.exe")
        self.sha_url = (sha_url or "").strip()
        self.asset_id = int(asset_id or 0)
        self.sha_asset_id = int(sha_asset_id or 0)
        self.repo = (repo or "").strip()
        self._stop = False
        self.verified = False
        self.via = ""      # api / direct，出问题时报给用户看

    def stop(self):
        self._stop = True

    def _open(self, url: str, asset_id: int = 0, extra_headers: dict = None):
        """优先走 API 资产接口，失败再回落到浏览器直链。"""
        hdrs = {"User-Agent": UA}
        if extra_headers:
            hdrs.update(extra_headers)
        if asset_id and self.repo:
            try:
                req = urllib.request.Request(
                    API_ASSET.format(repo=self.repo, aid=asset_id),
                    headers={**hdrs, "Accept": "application/octet-stream"})
                resp = urllib.request.urlopen(req, timeout=45)
                self.via = "api"
                return resp
            except Exception:  # noqa: BLE001  接口不通就直链，别把路走死
                pass
        req = urllib.request.Request(url, headers=hdrs)
        resp = urllib.request.urlopen(req, timeout=45)
        self.via = "direct"
        return resp

    def run(self):
        if not self.url and not self.asset_id:
            self.failed.emit("下载地址为空（发布资产里没找到安装包）")
            return
        if self.url and not url_is_safe(self.url):
            self.failed.emit("下载地址不是 https，已拒绝（更新包会被执行，不接受明文传输）")
            return
        if self.sha_url and not url_is_safe(self.sha_url):
            self.failed.emit("校验文件地址不是 https，已拒绝")
            return
        dest = os.path.join(download_dir(), self.dest_name)
        part = dest + ".part"
        total = 0
        last_err = ""
        done_ok = False
        # v3.0.22：断点续传 —— 大包在移动网络/跨国链路上被掐断是常态，
        # 保留 .part 并用 Range 接着下，最多 6 次；每次都从已有字节处继续。
        for attempt in range(1, 7):
            if self._stop:
                break
            have = os.path.getsize(part) if os.path.exists(part) else 0
            self.resumed_from = have
            try:
                extra = {"Range": f"bytes={have}-"} if have else None
                with self._open(self.url, self.asset_id, extra) as resp:
                    code = int(getattr(resp, "status", 200) or 200)
                    if have and code != 206:
                        have = 0          # 服务器不认 Range，只能从头来
                    cr = str(resp.headers.get("Content-Range") or "")
                    if "/" in cr:
                        total = int(cr.rsplit("/", 1)[-1] or 0)
                    elif resp.headers.get("Content-Length"):
                        total = have + int(resp.headers.get("Content-Length") or 0)
                    got = have
                    with open(part, "ab" if have else "wb") as f:
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
                size_now = os.path.getsize(part) if os.path.exists(part) else 0
                if total and size_now < total:
                    last_err = (f"连接提前中断（{size_now / 1048576:.1f}/{total / 1048576:.1f}MB），"
                                f"第 {attempt} 次自动续传")
                    self.progress.emit(int(size_now * 100 / total), size_now, total)
                    time.sleep(min(6, attempt * 2))
                    continue
                if not total and size_now == 0:
                    raise RuntimeError("服务器返回空内容")
                done_ok = True
                break
            except Exception as e:  # noqa: BLE001
                last_err = f"{type(e).__name__}: {str(e)[:120]}"
                if self._stop:
                    break
                time.sleep(min(6, attempt * 2))
        if not done_ok:
            # 注意：这里故意不删 .part —— 下次点下载会从断点续传
            self.failed.emit(f"{last_err or '下载没完成'}；断点已保留，再点一次会接着下")
            return
        try:
            if self.sha_url:
                expect = ""
                with self._open(self.sha_url, self.sha_asset_id) as r:
                    expect = parse_sha_text(r.read().decode("utf-8", "ignore"))
                actual = _sha256(part)
                if not expect:
                    os.remove(part)
                    self.failed.emit("校验文件里找不到合法 SHA256，已拒绝安装")
                    return
                if actual != expect:
                    os.remove(part)
                    self.failed.emit(f"SHA256 校验失败（期望 {expect[:12]}…，实际 {actual[:12]}…）")
                    return
                self.verified = True
            os.replace(part, dest)
            self.done.emit(dest)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"落盘/校验阶段出错：{type(e).__name__}: {str(e)[:120]}")
