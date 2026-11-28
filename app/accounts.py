# -*- coding: utf-8 -*-
"""本地多档案账号：每个账号一个独立目录，养成 / 情绪 / 记忆 / 知识库全部在本机。

目录结构（安装版默认在 exe 同目录；不可写时回退 %APPDATA%\\WhaleGirlPet\\）：
  accounts.json              账号列表 + 当前账号
  accounts/<slug>/config.json  该账号的配置与存档
  accounts/<slug>/memory.db    该账号的记忆库（SQLite）
  accounts/<slug>/kb/          该账号的知识库文档
  accounts/<slug>/voices/      该账号导入的语音文件
  accounts/<slug>/tts_cache/   方言合成缓存

首次运行会把旧版单档案 config.json 迁移为第一个账号「默认」，原文件保留不动。
"""
import json
import os
import re
import shutil
import time

import paths


def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def slugify(name: str) -> str:
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", (name or "").strip())[:24]
    return base or "account"


class AccountStore:
    """账号列表读写；账号数据本身由 config_file() 按 slug 定位。"""

    def __init__(self, base_dir: str = ""):
        self.base = base_dir or paths.data_dir()
        self.file = os.path.join(self.base, "accounts.json")
        self._data = None

    # ---------- 持久化 ----------
    def _load(self):
        if self._data is not None:
            return self._data
        raw = _read_json(self.file, None)
        if not isinstance(raw, dict) or not raw.get("accounts"):
            raw = self._migrate_legacy()
        self._data = raw
        return raw

    def _migrate_legacy(self) -> dict:
        """把旧版单档案 config.json 迁移成第一个账号。"""
        legacy = os.path.join(self.base, "config.json")
        slug = "default"
        d = os.path.join(self.base, "accounts", slug)
        os.makedirs(d, exist_ok=True)
        target = os.path.join(d, "config.json")
        if os.path.exists(legacy) and not os.path.exists(target):
            try:
                shutil.copy2(legacy, target)
            except OSError:
                pass
        data = {
            "current": slug,
            "accounts": [{
                "slug": slug,
                "name": "默认",
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            }],
        }
        try:
            _write_json(self.file, data)
        except OSError:
            pass
        return data

    def save(self):
        try:
            _write_json(self.file, self._load())
        except OSError:
            pass

    # ---------- 查询 ----------
    def all(self) -> list:
        return list(self._load()["accounts"])

    def current(self) -> dict:
        data = self._load()
        slug = data.get("current", "")
        for a in data["accounts"]:
            if a["slug"] == slug:
                return a
        return data["accounts"][0]

    def current_slug(self) -> str:
        return self.current()["slug"]

    def dir_of(self, slug: str) -> str:
        return paths.account_dir(slug)

    def exists(self, slug: str) -> bool:
        return any(a["slug"] == slug for a in self.all())

    # ---------- 变更 ----------
    def activate(self, slug: str) -> bool:
        if not self.exists(slug):
            return False
        self._load()["current"] = slug
        paths.set_active_account(slug)
        self.save()
        return True

    def create(self, name: str, copy_from: str = "") -> dict:
        name = (name or "").strip() or "新账号"
        slug = slugify(name)
        n = 1
        while self.exists(slug):
            n += 1
            slug = slugify(name) + f"_{n}"
        d = paths.account_dir(slug)
        src = ""
        if copy_from and self.exists(copy_from):
            src = os.path.join(paths.account_dir(copy_from), "config.json")
        dst = os.path.join(d, "config.json")
        if src and os.path.exists(src):
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass
        rec = {"slug": slug, "name": name, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
        self._load()["accounts"].append(rec)
        self.save()
        return rec

    def rename(self, slug: str, name: str) -> bool:
        for a in self.all():
            if a["slug"] == slug:
                a["name"] = (name or "").strip() or a["slug"]
                self.save()
                return True
        return False

    def delete(self, slug: str) -> bool:
        accounts = self._load()["accounts"]
        if len(accounts) <= 1:
            return False
        if not self.exists(slug):
            return False
        d = paths.account_dir(slug)
        try:
            shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass
        self._data["accounts"] = [a for a in accounts if a["slug"] != slug]
        if self._data.get("current") == slug:
            self._data["current"] = self._data["accounts"][0]["slug"]
            paths.set_active_account(self._data["current"])
        self.save()
        return True


STORE = None


def init_store() -> AccountStore:
    """程序启动时调用：定位当前账号并写入 paths 的活跃 slug。"""
    global STORE
    STORE = AccountStore()
    STORE.activate(STORE.current_slug())
    return STORE
