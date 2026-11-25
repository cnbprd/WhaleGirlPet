# -*- coding: utf-8 -*-
"""隔离区（v3.0.21）：只做「移走 + 可恢复」，永远不删。

- 目录：`<数据目录>/quarantine`
- 每条：`<sha256 前 16 位>_<净化后的原文件名>.qtn` + 同名 `.json`（原路径 / 时间 / 原因 / 大小）
- 恢复：按 json 记录的原路径放回；原位置已被占用时改放 `<名字>.restored.<扩展名>`，不覆盖
- 清理：只有用户显式点「彻底删除」才真的删副本

动作全部由用户点击触发；扫描本身只读，不会自己动文件。
"""
import datetime
import json
import os
import re
import shutil

import guard_core
import paths


def qdir() -> str:
    d = os.path.join(paths.data_dir(), "quarantine")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _clean_name(name: str) -> str:
    base = os.path.basename(str(name or "sample"))
    base = re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5._-]+", "_", base)[:80] or "sample"
    return base


def _meta_path(item: str) -> str:
    return item + ".json" if not item.endswith(".json") else item


def quarantine_file(path: str, findings=None, reason: str = "") -> dict:
    """把文件移进隔离区。返回 {ok, item, sha, error}。"""
    try:
        if not os.path.isfile(path):
            return {"ok": False, "error": "不是普通文件（目录/链接不收）"}
        if os.path.islink(path):
            return {"ok": False, "error": "符号链接不收"}
        size = os.path.getsize(path)
        sha = guard_core.sha256_of(path)
        if not sha:
            return {"ok": False, "error": "读不到文件内容，无法算哈希"}
        name = _clean_name(path)
        item = os.path.join(qdir(), f"{sha[:16]}_{name}.qtn")
        if os.path.exists(item):
            item = os.path.join(qdir(), f"{sha[:16]}_{int(datetime.datetime.now().timestamp())}_{name}.qtn")
        meta = {
            "sha256": sha, "size": size, "origin": os.path.abspath(path),
            "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": str(reason or "")[:300],
            "rules": [str((f or {}).get("rule", "")) for f in (findings or [])][:20],
            "titles": [str((f or {}).get("title", "")) for f in (findings or [])][:20],
        }
        # 先复制到隔离区并核对，再动原文件：中途失败也不会两头都没有
        shutil.copy2(path, item)
        if guard_core.sha256_of(item) != sha:
            try:
                os.remove(item)
            except OSError:
                pass
            return {"ok": False, "error": "复制后校验不一致，已放弃"}
        with open(_meta_path(item), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        try:
            os.remove(path)
        except OSError as e:
            return {"ok": False, "item": item, "sha": sha,
                    "error": f"副本已存好，但原文件删不掉（{e}）；可先手动处理原文件"}
        return {"ok": True, "item": item, "sha": sha, "size": size}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def list_items() -> list:
    out = []
    d = qdir()
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".qtn"):
            continue
        item = os.path.join(d, fn)
        meta = {}
        try:
            with open(_meta_path(item), "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, ValueError):
            pass
        try:
            size = os.path.getsize(item)
        except OSError:
            size = 0
        out.append({"item": item, "name": fn, "size": size,
                    "origin": meta.get("origin", ""), "at": meta.get("at", ""),
                    "sha256": meta.get("sha256", ""), "reason": meta.get("reason", "")})
    return out


def restore(item: str) -> dict:
    """按记录的原路径放回；原位置已存在就改名，绝不覆盖。"""
    if not os.path.isfile(item) or not item.endswith(".qtn"):
        return {"ok": False, "error": "不是隔离区条目"}
    try:
        with open(_meta_path(item), "r", encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {"ok": False, "error": "缺少元信息，无法确定原路径"}
    origin = str(meta.get("origin") or "").strip()
    if not origin or not os.path.isabs(origin):
        return {"ok": False, "error": "原路径无效"}
    dest = origin
    if os.path.exists(dest):
        root, ext = os.path.splitext(origin)
        dest = f"{root}.restored{ext}"
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(item, dest)
        try:
            os.remove(_meta_path(item))
        except OSError:
            pass
        return {"ok": True, "path": dest}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def delete_item(item: str) -> dict:
    """彻底删除隔离副本。只在用户明确要求时调用。"""
    if not os.path.isfile(item) or not item.endswith(".qtn"):
        return {"ok": False, "error": "不是隔离区条目"}
    try:
        os.remove(item)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    try:
        os.remove(_meta_path(item))
    except OSError:
        pass
    return {"ok": True}
