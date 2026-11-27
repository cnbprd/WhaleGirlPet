#!/usr/bin/env python3
"""Read-only release asset verifier for the 3.2.0-sprite desktop build.

Checks the three release candidates (3D exe, portable ZIP, installer), the
ZIP contents, the embedded 2D card manifest/atlas, the installer checksum
sidecar, and the staging payload used to build the installer.

It never starts whale3d.exe, never installs the installer, never writes into
the payload directories, and never touches the running 24h soak checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zipfile
from datetime import datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def png_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


class Verifier:
    def __init__(self, root: Path, expected_path: Path) -> None:
        self.root = root
        self.expected_path = expected_path
        self.checks: list[dict] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.meta: dict = {}

    def resolve(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else self.root / p

    def add(self, name: str, ok: bool, detail: str, warning: bool = False) -> None:
        self.checks.append({"name": name, "ok": ok, "detail": detail, "warning": warning})
        if not ok:
            (self.warnings if warning else self.errors).append(f"{name}: {detail}")

    def check_asset(self, spec: dict) -> None:
        path = self.resolve(spec["path"])
        name = spec.get("name", spec["path"])
        if not path.is_file():
            self.add(f"{name} 存在", False, f"missing {spec['path']}")
            return
        size = path.stat().st_size
        digest = sha256_file(path)
        size_ok = size == spec["size"]
        self.add(f"{name} 大小", size_ok, str(size) if size_ok else f"{size} != {spec['size']}")
        self.add(f"{name} SHA256", digest == spec["sha256"].upper(), digest)

        sidecar = spec.get("sidecar")
        if sidecar:
            sidecar_path = self.resolve(sidecar)
            if not sidecar_path.is_file():
                self.add(f"{name} .sha256", False, f"missing {sidecar}")
            else:
                text = sidecar_path.read_text(encoding="utf-8", errors="replace").strip()
                token = text.split()[0].upper() if text else ""
                sidecar_name = text.split()[-1].lstrip("*") if text else ""
                ok_hash = token == spec["sha256"].upper()
                ok_name = sidecar_name == path.name
                self.add(
                    f"{name} .sha256",
                    ok_hash and ok_name,
                    f"hash={token[:16]}..., file={sidecar_name}",
                )

        for token in spec.get("must_contain", []):
            self.add(f"{name} 文件名含 {token}", token in path.name, path.name)
        for token in spec.get("must_not_contain", []):
            self.add(f"{name} 文件名不含 {token}", token not in path.name, path.name)

    def check_zip(self, spec: dict) -> zipfile.ZipFile:
        path = self.resolve(spec["path"])
        if not path.is_file():
            self.add("ZIP 存在", False, f"missing {spec['path']}")
            return None
        try:
            zf = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as exc:
            self.add("ZIP 可读", False, str(exc))
            return None
        self.add("ZIP 可读", True, f"{len(zf.namelist())} entries")

        bad = []
        for member in zf.namelist():
            normalized = member.replace("\\", "/")
            if normalized.startswith("/") or ".." in normalized.split("/"):
                bad.append(member)
        self.add("ZIP 路径安全", not bad, ", ".join(bad[:5]) or "ok")

        for entry in spec.get("required_entries", []):
            name = entry["path"]
            try:
                info = zf.getinfo(name)
            except KeyError:
                self.add(f"ZIP {name}", False, "missing")
                continue
            self.add(f"ZIP {name} 大小", info.file_size == entry["size"], str(info.file_size) if info.file_size == entry["size"] else f"{info.file_size} != {entry['size']}")
            digest = hashlib.sha256(zf.read(name)).hexdigest().upper()
            self.add(f"ZIP {name} SHA256", digest == entry["sha256"].upper(), digest)
        return zf

    def check_atlas(self, zf: zipfile.ZipFile, spec: dict) -> None:
        name = spec["path"]
        try:
            data = zf.read(name)
        except KeyError:
            self.add("图集存在", False, f"missing {name}")
            return
        size = png_size(data)
        if size is None:
            self.add("图集 PNG", False, "not a PNG/IHDR")
            return
        self.add(
            "图集尺寸",
            size == (spec["width"], spec["height"]),
            f"{size[0]}x{size[1]}" if size == (spec["width"], spec["height"]) else f"{size[0]}x{size[1]} != {spec['width']}x{spec['height']}",
        )

    def check_card_manifest(self, zf: zipfile.ZipFile, spec: dict) -> None:
        name = spec["path"]
        try:
            data = zf.read(name)
        except KeyError:
            self.add("卡面 manifest 存在", False, f"missing {name}")
            return
        try:
            manifest = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.add("卡面 manifest JSON", False, str(exc))
            return
        self.add("卡面 manifest JSON", True, "parsed")

        sheet = manifest.get("sheet_size")
        self.add(
            "卡面 sheet_size",
            sheet == spec["sheet_size"],
            str(sheet) if sheet == spec["sheet_size"] else f"{sheet} != {spec['sheet_size']}",
        )
        if not (isinstance(sheet, list) and len(sheet) == 2 and all(isinstance(v, int) for v in sheet)):
            self.add("卡面 sheet_size 可用", False, f"bad value: {sheet}")
            return
        self.add(
            "卡面 slot_size",
            manifest.get("slot_size") == spec["slot_size"],
            str(manifest.get("slot_size")),
        )

        cards = manifest.get("cards")
        if not isinstance(cards, list):
            self.add("卡面 cards 类型", False, "not a list")
            return
        ids = [card.get("id") for card in cards if isinstance(card, dict)]
        required = spec["required_ids"]
        self.add("卡面数量", len(cards) == spec["card_count"], str(len(cards)) if len(cards) == spec["card_count"] else f"{len(cards)} != {spec['card_count']}")
        self.add("卡面 id 完整", set(ids) == set(required), f"missing={sorted(set(required) - set(ids))}, extra={sorted(set(ids) - set(required))}")
        self.add("卡面 id 无重复", len(ids) == len(set(ids)), f"{len(ids)} ids")

        bad_rects = []
        bad_slots = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            rect = card.get("rect")
            slot = card.get("slot")
            if not (isinstance(rect, list) and len(rect) == 4 and all(isinstance(v, int) for v in rect)):
                bad_rects.append(f"{card.get('id')}: rect")
                continue
            x, y, w, h = rect
            if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > sheet[0] or y + h > sheet[1]:
                bad_rects.append(f"{card.get('id')}: {rect}")
            if slot is not None:
                if not (isinstance(slot, list) and len(slot) == 4 and all(isinstance(v, int) for v in slot)):
                    bad_slots.append(f"{card.get('id')}: slot")
                else:
                    sx, sy, sw, sh = slot
                    if sx < 0 or sy < 0 or sw <= 0 or sh <= 0 or sx + sw > sheet[0] or sy + sh > sheet[1]:
                        bad_slots.append(f"{card.get('id')}: {slot}")
        self.add("卡面 rect 越界", not bad_rects, "; ".join(bad_rects[:4]) or "ok")
        self.add("卡面 slot 越界", not bad_slots, "; ".join(bad_slots[:4]) or "ok")

    def check_staging(self, spec: dict) -> None:
        base = self.resolve(spec["path"])
        if not base.is_dir():
            self.add("staging 存在", False, f"missing {spec['path']}")
            return
        self.add("staging 存在", True, spec["path"])
        for entry in spec.get("required_entries", []):
            path = base / entry["path"]
            if not path.is_file():
                self.add(f"staging {entry['path']}", False, "missing")
                continue
            size = path.stat().st_size
            digest = sha256_file(path)
            self.add(f"staging {entry['path']} 大小", size == entry["size"], str(size) if size == entry["size"] else f"{size} != {entry['size']}")
            self.add(f"staging {entry['path']} SHA256", digest == entry["sha256"].upper(), digest)

    def run(self) -> int:
        if not self.expected_path.is_file():
            self.add("期望清单存在", False, f"missing {self.expected_path}")
            return 1
        try:
            expected = json.loads(self.expected_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.add("期望清单 JSON", False, str(exc))
            return 1
        self.add("期望清单 JSON", True, str(self.expected_path))

        self.meta = {
            "release": expected.get("release", {}),
            "expected_manifest": str(self.expected_path),
        }

        for asset in expected.get("assets", []):
            self.check_asset(asset)

        zf = self.check_zip(expected.get("zip", {}))
        if zf is not None:
            try:
                if expected.get("atlas"):
                    self.check_atlas(zf, expected["atlas"])
                if expected.get("card_manifest"):
                    self.check_card_manifest(zf, expected["card_manifest"])
            finally:
                zf.close()

        if expected.get("staging"):
            self.check_staging(expected["staging"])

        return 0 if not self.errors else 1

    def report(self) -> dict:
        return {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "release": self.meta.get("release", {}),
            "root": str(self.root),
            "expected_manifest": str(self.expected_path),
            "ok": not self.errors,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def write_reports(result: dict, json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status = "PASS" if result["ok"] else "FAIL"
    release = result.get("release", {})
    lines = [
        "# Release 资产校验",
        "",
        f"生成时间：{result['generated_at']}",
        f"版本：`{release.get('version', '?')}` / tag `{release.get('tag', '?')}`",
        f"结论：**{status}**（{result['error_count']} errors, {result['warning_count']} warnings）",
        "",
        "> 只读校验：未启动 3D、未安装安装器、未构建、未修改生产 checkpoint。",
        "",
        "| 状态 | 检查 | 详情 |",
        "|---|---|---|",
    ]
    for check in result["checks"]:
        if check["ok"]:
            mark = "PASS"
        elif check.get("warning"):
            mark = "WARN"
        else:
            mark = "FAIL"
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {mark} | {check['name']} | {detail} |")
    lines += [
        "",
        "## 限制",
        "",
        "- 安装器内部 payload 未解包核对；本脚本核对安装器文件本身、`.sha256` sidecar 和构建 staging。",
        "- 真实 24h 完成、17 卡目检、真实点击穿透仍需在浸泡结束后执行。",
        "",
    ]
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Read-only release asset verifier")
    parser.add_argument("--root", default=str(repo_root), help="repository root")
    parser.add_argument("--expected", default="docs/release-assets-3.2.0-sprite.json", help="expected manifest")
    parser.add_argument("--json-out", default="docs/release-asset-verify.json", help="JSON report path")
    parser.add_argument("--md-out", default="docs/release-asset-verify.md", help="Markdown report path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    expected_path = Path(args.expected)
    if not expected_path.is_absolute():
        expected_path = root / expected_path
    verifier = Verifier(root, expected_path)
    code = verifier.run()
    result = verifier.report()
    write_reports(result, root / args.json_out, root / args.md_out)

    print(f"release asset verify: {'PASS' if result['ok'] else 'FAIL'}")
    for error in result["errors"]:
        print(f"  ERROR {error}")
    for warning in result["warnings"]:
        print(f"  WARN  {warning}")
    print(f"  checks={len(result['checks'])} errors={result['error_count']} warnings={result['warning_count']}")
    return code


if __name__ == "__main__":
    sys.exit(main())
