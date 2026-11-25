# -*- coding: utf-8 -*-
"""鲸鱼娘安全管家 · 自研启发式扫描核心（v3.0.10）

定位：只读体检 + 启发式研判，**只报不杀**。不删文件、不改注册表、不隔离；
真需要处置时把可疑路径交给 Windows Defender 深扫，由官方引擎决定。

三层结构
1. PE 静态解析（纯 Python，零第三方依赖）：DOS/NT 头、节区表、节区熵、
   可写且可执行节、入口点落在异常节、证书目录是否存在、时间戳。
2. 迷你规则引擎：JSON 规则（字符串 / 正则 / 十六进制），作用域
   file / path / cmdline，带权重与等级；内置一批针对常见投毒与无文件攻击的启发式规则，
   也可把自定义规则放进 <数据目录>/rules/guard/*.json。
3. 持久化审计：Run/RunOnce、启动文件夹、计划任务、服务、IFEO 劫持。

输出：findings（等级 / 权重 / 理由 / 证据）、0-100 风险分、Markdown + JSON 报告。
"""
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

# ---------------- 常量 ----------------
SCAN_EXTS = (".exe", ".dll", ".scr", ".sys", ".com", ".bat", ".cmd", ".ps1",
             ".vbs", ".vbe", ".js", ".jse", ".hta", ".msi", ".lnk")
MAX_FILE_MB = 60
MAX_FILES = 320
MAX_SECTIONS = 96
SUSPICIOUS_DIR_HINTS = ("\\temp\\", "\\tmp\\", "\\appdata\\local\\temp", "\\downloads\\",
                        "\\desktop\\", "\\public\\", "\\appdata\\roaming\\",
                        "\\recycle", "$recycle.bin")
# 这些前缀下的程序即便命令行含 temp 字样也只减分，不当可疑（否则 Defender 自己的任务会被误报）
TRUSTED_PREFIXES = ("c:\\windows\\", "c:\\program files\\", "c:\\program files (x86)\\",
                    "c:\\programdata\\microsoft\\windows defender\\")
LOLBINS = ("powershell", "pwsh", "mshta", "certutil", "bitsadmin",
           "msbuild", "installutil", "cmstp", "curl", "wget")

# 内置规则：scope 支持 cmdline / path / file；kind 支持 regex / str / hex
DEFAULT_RULES = [
    {"id": "H001", "name": "PowerShell 编码命令", "level": "high", "weight": 38,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)powershell.{0,60}-(enc|encodedcommand|e\s)",
     "why": "编码命令是无文件攻击与远控落地最常见的手法"},
    {"id": "H002", "name": "certutil 解码", "level": "high", "weight": 34,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)certutil.{0,30}(-decode|-urlcache|-split)",
     "why": "用系统自带 certutil 下载/解码载荷，典型白加黑"},
    {"id": "H003", "name": "mshta 远程脚本", "level": "high", "weight": 34,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)mshta.{0,60}(https?:|vbscript:|javascript:)",
     "why": "mshta 执行远程 HTA，常被用作加载器"},
    {"id": "H004", "name": "rundll32 远程 DLL", "level": "high", "weight": 32,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)rundll32.{0,80}(https?:|\\\\[a-z0-9_.\-]+\\)",
     "why": "rundll32 直接拉远程/共享路径 DLL，绕过落地检测"},
    {"id": "H005", "name": "regsvr32 静默注册远程脚本", "level": "high", "weight": 32,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)regsvr32.{0,60}(/s|/u|/i).{0,60}(https?:|scrobj)",
     "why": "Squiblydoo：regsvr32 加载远程 scriptlet"},
    {"id": "H006", "name": "bitsadmin 下载", "level": "medium", "weight": 26,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)bitsadmin.{0,40}(/transfer|/addfile)",
     "why": "后台传输服务常被用来悄悄下载载荷"},
    {"id": "H007", "name": "隐藏窗口 + 命令行链", "level": "medium", "weight": 22,
     "scope": "cmdline", "kind": "regex", "pattern": r"(?i)(-windowstyle\s+hidden|/windowstyle\s+min|start\s+/b)",
     "why": "隐藏窗口运行是持久化脚本的常见做法"},
    {"id": "H008", "name": "cmd /c 串联系统工具", "level": "medium", "weight": 20,
     "scope": "cmdline", "kind": "regex",
     "pattern": r"(?i)cmd(\.exe)?\s+/c.{0,80}(powershell|bitsadmin|certutil|mshta|curl|wmic)",
     "why": "cmd 串联解释器/下载器，常见批处理落地"},
    {"id": "H009", "name": "从临时/下载目录启动", "level": "medium", "weight": 24,
     "scope": "path", "kind": "regex",
     "pattern": r"(?i)(\\temp\\|\\tmp\\|\\downloads\\|\\public\\|\\appdata\\roaming\\)",
     "why": "正规软件极少把常驻程序放在临时/下载/漫游目录"},
    {"id": "H010", "name": "脚本内反射执行", "level": "high", "weight": 30,
     "scope": "file", "kind": "regex",
     "pattern": r"(?i)(invoke-expression|iex\s*\(|frombase64string|downloadstring|assembly\.load)",
     "why": "脚本里内联解码/反射加载，是无文件攻击特征"},
    {"id": "H011", "name": "脚本内持久化写入", "level": "medium", "weight": 24,
     "scope": "file", "kind": "regex",
     "pattern": r"(?i)(currentversion\\run|schtasks\s+/create|new-itemproperty.{0,40}run)",
     "why": "脚本自行写自启动项，常见于流氓安装器与挖矿"},
    {"id": "H012", "name": "可疑混淆长串", "level": "medium", "weight": 14,
     "scope": "file", "kind": "regex",
     "pattern": r"[A-Za-z0-9+/]{200,}={0,2}",
     "exclude_ext": [".js", ".json", ".css", ".html", ".htm", ".map", ".min.js"],
     "why": "超长 base64 样字符串，多为混淆后的载荷（源码文件豁免，避免误伤前端包）"},
    {"id": "H013", "name": "RAT 关键字", "level": "medium", "weight": 20,
     "scope": "file", "kind": "regex",
     "pattern": r"(?i)(keylog|screenshot.{0,20}(capture|hook)|reverse.{0,10}shell|meterpreter|njrat|quasar)",
     "why": "远控/窃密常见功能关键字"},
    {"id": "H014", "name": "勒索信特征", "level": "high", "weight": 34,
     "scope": "file", "kind": "regex",
     "pattern": r"(?i)((all\s+)?your files (have been|are)\s+encrypted|"
              r"files have been encrypted|readme.*(decrypt|recover).*files|"
              r"\.wncry|\.locky|\.cerber)",
     "why": "勒索软件落地后的勒索信/加密后缀（.crypt 这类泛指不算，容易误伤正常代码）"},
    {"id": "H015", "name": "挖矿矿池地址", "level": "medium", "weight": 24,
     "scope": "file", "kind": "regex",
     "pattern": r"(?i)(stratum\+tcp|minexmr|nanopool|xmrpool|supportxmr)",
     "why": "挖矿木马内置矿池连接串"},
    {"id": "AV-EICAR", "name": "EICAR 杀毒测试串", "level": "high", "weight": 40,
     "scope": "file", "kind": "str",
     "pattern": "EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
     "why": "业界通用杀毒能力测试样本，正常文件不会出现此串；命中即证明检测链路有效"},
]


# ---------------- 工具 ----------------
def _log(msg: str):
    try:
        print(f"[guard] {msg}")
    except Exception:  # noqa: BLE001
        pass


def _read_head(path: str, n: int = 512) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def entropy(buf: bytes) -> float:
    """香农熵（0-8）。>7 通常意味着加壳/加密/压缩。"""
    if not buf:
        return 0.0
    freq = {}
    for b in buf:
        freq[b] = freq.get(b, 0) + 1
    n = len(buf)
    ent = 0.0
    for c in freq.values():
        p = c / n
        ent -= p * math.log2(p)
    return round(ent, 2)


def _u16(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 2], "little") if len(b) >= o + 2 else 0


def _u32(b: bytes, o: int) -> int:
    return int.from_bytes(b[o:o + 4], "little") if len(b) >= o + 4 else 0


def pe_info(path: str) -> dict:
    """纯 Python 解析 PE 头/节区。返回 {is_pe, ...}，解析失败给 error 不抛异常。"""
    info = {"is_pe": False, "error": ""}
    try:
        size = os.path.getsize(path)
    except OSError as e:
        info["error"] = f"读不到大小：{e}"
        return info
    info["size"] = size
    if size < 64:
        info["error"] = "文件过小"
        return info
    head = _read_head(path, 4096)
    if head[:2] != b"MZ":
        return info
    e_lfanew = _u32(head, 0x3C)
    if not (0 < e_lfanew < 4096) or len(head) < e_lfanew + 24:
        info["error"] = "e_lfanew 异常"
        return info
    if head[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        info["error"] = "MZ 但无 PE 签名"
        return info
    coff = e_lfanew + 4
    machine = _u16(head, coff)
    nsec = _u16(head, coff + 2)
    td_stamp = _u32(head, coff + 4)
    size_opt = _u16(head, coff + 16)
    opt = coff + 20
    magic = _u16(head, opt)
    is64 = magic == 0x20b
    if magic not in (0x10b, 0x20b):
        info["error"] = f"OptionalHeader magic 异常 0x{magic:x}"
        return info
    entry_rva = _u32(head, opt + 16)
    # DataDirectory：PE32 从 opt+96 起，PE32+ 从 opt+112 起；Security 是第 5 个（index 4）
    dd = opt + (112 if is64 else 96)
    sec_dir_off = _u32(head, dd + 4 * 8)
    sec_dir_size = _u32(head, dd + 4 * 8 + 4)
    sec_off = opt + size_opt
    sections = []
    for i in range(min(nsec, MAX_SECTIONS)):
        o = sec_off + i * 40
        if len(head) < o + 40:
            break
        name = head[o:o + 8].rstrip(b"\0").decode("latin-1", "replace")
        vsize = _u32(head, o + 8)
        vaddr = _u32(head, o + 12)
        raw_size = _u32(head, o + 16)
        raw_ptr = _u32(head, o + 20)
        chars = _u32(head, o + 36)
        execu = bool(chars & 0x20000000)
        writ = bool(chars & 0x80000000)
        ent = 0.0
        if raw_size and raw_ptr and raw_size < 8 * 1024 * 1024 and raw_ptr < size:
            try:
                with open(path, "rb") as f:
                    f.seek(raw_ptr)
                    ent = entropy(f.read(min(raw_size, 512 * 1024)))
            except OSError:
                ent = 0.0
        sections.append({"name": name or f"<{i}>", "vsize": vsize, "vaddr": vaddr,
                         "raw_size": raw_size, "raw_ptr": raw_ptr,
                         "exec": execu, "write": writ, "entropy": ent,
                         "entry": bool(vaddr <= entry_rva < vaddr + max(vsize, raw_size))})
    info.update({
        "is_pe": True, "machine": hex(machine), "is64": is64, "sections": sections,
        "nsec": nsec, "entry_rva": entry_rva, "timestamp": td_stamp,
        "signed_dir": sec_dir_size > 0 and sec_dir_off > 0,
        "sec_dir_off": sec_dir_off, "sec_dir_size": sec_dir_size,
        "writable_exec_sections": [s["name"] for s in sections if s["exec"] and s["write"]],
        "high_entropy_sections": [s["name"] for s in sections if s["entropy"] >= 7.2 and s["raw_size"] > 0],
        "entry_in_write_section": any(s["entry"] and s["write"] for s in sections),
        "section_names": [s["name"] for s in sections],
        "created": datetime.datetime.utcfromtimestamp(td_stamp).strftime("%Y-%m-%d %H:%M")
        if td_stamp else "",
    })
    return info


# ---------------- 规则引擎 ----------------
def rules_dir(data_dir: str = "") -> str:
    d = os.path.join(data_dir or _data_root(), "rules", "guard")
    return d


def _data_root() -> str:
    try:
        import paths
        return paths.data_dir()
    except Exception:  # noqa: BLE001
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_rules(data_dir: str = "") -> list:
    """内置规则 + 用户目录 rules/guard/*.json 追加（同 id 覆盖）。"""
    rules = [dict(r) for r in DEFAULT_RULES]
    d = rules_dir(data_dir)
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), "r", encoding="utf-8") as f:
                    extra = json.load(f)
                if isinstance(extra, dict):
                    extra = extra.get("rules") or []
                for r in extra:
                    if not isinstance(r, dict) or not r.get("id"):
                        continue
                    rules = [x for x in rules if x.get("id") != r["id"]]
                    rules.append(r)
            except Exception as e:  # noqa: BLE001
                _log(f"规则文件 {fn} 读取失败：{e}")
    out = []
    for r in rules:
        r.setdefault("weight", 15)
        r.setdefault("level", "medium")
        r.setdefault("scope", "file")
        r.setdefault("kind", "regex")
        if r["kind"] == "regex":
            try:
                r["_re"] = re.compile(r.get("pattern", ""))
            except re.error as e:
                _log(f"规则 {r['id']} 正则无效：{e}")
                continue
        out.append(r)
    return out


def _match(r: dict, text: str) -> bool:
    kind = r.get("kind", "regex")
    if kind == "regex":
        rx = r.get("_re")
        return bool(rx and rx.search(text))
    if kind == "str":
        return str(r.get("pattern", "")) in text
    if kind == "hex":
        return False  # 二进制级 hex 匹配在文件里做，这里不参与文本
    return False


def _hex_hit(r: dict, path: str) -> bool:
    if r.get("kind") != "hex":
        return False
    try:
        pat = bytes.fromhex(str(r.get("pattern", "")).replace(" ", "").replace("0x", ""))
    except ValueError:
        return False
    if not pat:
        return False
    try:
        with open(path, "rb") as f:
            return pat in f.read(min(os.path.getsize(path), 8 * 1024 * 1024))
    except OSError:
        return False


# ---------------- 哈希名单（借鉴 Loki / ClamAV 的 hash IOC 思路） ----------------
# Loki 的判定链是「hash → filename → YARA → 行为」，hash 排第一：成本最低、零误报。
# 本机没有 YARA 引擎，就把第一环直接用上——SHA256 黑名单命中即判高危，白名单直接跳过。
EICAR_TEXT = ("X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
HASH_DIR_NAME = "hashes"
_HASH_CACHE = {"stamp": None, "black": {}, "white": {}}


def hash_dir(data_dir: str = "") -> str:
    return os.path.join(data_dir or _data_root(), HASH_DIR_NAME)


def sha256_of(path: str) -> str:
    """流式算 SHA256（大文件不整读进内存）。失败返回空串。"""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
    except OSError:
        return ""
    return h.hexdigest()


def _list_sig(d: str) -> str:
    if not os.path.isdir(d):
        return ""
    parts = []
    for fn in sorted(os.listdir(d)):
        try:
            parts.append(f"{fn}:{int(os.path.getmtime(os.path.join(d, fn)))}")
        except OSError:
            pass
    return "|".join(parts)


def load_hash_lists(data_dir: str = "") -> dict:
    """读 hashes/black.txt、hashes/white.txt：每行 `<sha256>  # 备注`。按目录 mtime 缓存。"""
    d = hash_dir(data_dir)
    sig = _list_sig(d)
    if _HASH_CACHE["stamp"] == sig:
        return {"black": _HASH_CACHE["black"], "white": _HASH_CACHE["white"]}
    out = {"black": {}, "white": {}}
    for kind in ("black", "white"):
        fn = os.path.join(d, f"{kind}.txt")
        if not os.path.isfile(fn):
            continue
        try:
            with open(fn, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    raw = line.strip()
                    if not raw or raw.startswith("#"):
                        continue
                    note = raw.split("#", 1)[1].strip() if "#" in raw else ""
                    s = raw.split("#", 1)[0].strip().lower()
                    if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
                        out[kind][s] = note
        except OSError:
            continue
    _HASH_CACHE.update({"stamp": sig, "black": out["black"], "white": out["white"]})
    return out


def hash_verdict(path: str, data_dir: str = "") -> dict:
    """命中名单返回 {kind, sha, label}，否则 {}。名单为空时不算哈希（省 IO）。"""
    lists = load_hash_lists(data_dir)
    if not lists["black"] and not lists["white"]:
        return {}
    sha = sha256_of(path)
    if not sha:
        return {}
    # 白名单优先：用户显式信任的文件应能覆盖旧的黑名单条目（误报修正就是这么来的）
    if sha in lists["white"]:
        return {"kind": "white", "sha": sha, "label": lists["white"][sha]}
    if sha in lists["black"]:
        return {"kind": "black", "sha": sha, "label": lists["black"][sha]}
    return {}


def ensure_hash_dirs(data_dir: str = "") -> dict:
    """建好 hashes/black.txt 与 white.txt（带说明头），已存在就不动。返回两个路径。"""
    d = hash_dir(data_dir)
    os.makedirs(d, exist_ok=True)
    paths = {}
    for kind, desc in (("black", "已知恶意样本 SHA256（每行一个，可跟 # 备注）"),
                       ("white", "可信文件 SHA256（命中直接跳过扫描，降低误报与耗时）")):
        fn = os.path.join(d, f"{kind}.txt")
        if not os.path.isfile(fn):
            with open(fn, "w", encoding="utf-8") as f:
                f.write(f"# {desc}\n")
        paths[kind] = fn
    return paths


def eicar_selftest(data_dir: str = "", rules: list = None) -> dict:
    """分两层自证检测能力：

    1. 规则层（纯内存）：内置 AV-EICAR 规则必须认出标准串——不落盘，不受系统拦截影响。
    2. 端到端：真写一个 EICAR 文件再扫。
       - 能读到 → 必须命中，`source="self"`；
       - 读不到（Windows Defender 实时防护直接把内容锁住，open 报 Errno 22）
         → `blocked="system"`，这同样是"检测已生效"的证明，只是生效的是系统引擎。
    3. 对照组：写一个无害脚本，必须零命中（证明不是见谁咬谁）。
    """
    t0 = time.perf_counter()
    rules = rules if rules is not None else load_rules(data_dir)
    rule = next((r for r in rules if r.get("id") == "AV-EICAR"), None)
    rule_match = bool(rule and _match(rule, EICAR_TEXT))
    d = tempfile.mkdtemp(prefix="whale_guard_selftest_")
    bad = os.path.join(d, "eicar.txt")
    good = os.path.join(d, "hello.txt")
    hits, blocked, clean = [], "", []
    try:
        with open(bad, "w", encoding="utf-8") as f:
            f.write(EICAR_TEXT + "\n")
        with open(good, "w", encoding="utf-8") as f:
            f.write("print('hello')\n")
        try:
            with open(bad, "rb") as f:
                f.read()
            hits = scan_file(bad, rules, data_dir=data_dir)
        except OSError as e:
            blocked = "system" if getattr(e, "errno", 0) in (13, 22) else f"err{getattr(e, 'errno', '')}"
        clean = scan_file(good, rules, data_dir=data_dir)
    finally:
        for p in (bad, good):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass
    ms = (time.perf_counter() - t0) * 1000
    detected = bool(hits) or blocked == "system"
    return {"ok": rule_match and detected and not clean,
            "rule_match": rule_match, "eicar_hits": len(hits),
            "eicar_score": score_of(hits), "eicar_rules": [h.get("rule") for h in hits],
            "blocked": blocked, "clean_hits": len(clean),
            "ms": round(ms, 1), "rules": len(rules)}


def scan_file(path: str, rules: list, deep: bool = True, data_dir: str = "") -> list:
    """扫单个文件：规则命中 + PE 结构异常。返回 findings 列表。"""
    findings = []
    try:
        size = os.path.getsize(path)
    except OSError as e:
        return [{"level": "info", "score": 0, "kind": "file", "target": path,
                 "title": "读不到文件", "why": str(e)[:100]}]
    if size == 0:
        return []
    # 0) 哈希名单先行：黑名单直接判高危、白名单直接放过（名单为空时零开销）
    hv = hash_verdict(path, data_dir)
    if hv:
        if hv["kind"] == "white":
            return []
        return [{"level": "high", "score": 45, "kind": "hash", "target": path,
                 "rule": "HASH-BLACK", "title": "命中哈希黑名单",
                 "why": f"SHA256 {hv['sha'][:16]}…" + (f"｜{hv['label']}" if hv["label"] else "")}]
    ext = os.path.splitext(path)[1].lower()
    is_pe = _read_head(path, 2) == b"MZ"
    # 1) 文本类：脚本/批处理，读前 2MB 匹配规则
    if ext in (".ps1", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".hta", ".txt", ""):
        try:
            with open(path, "rb") as f:
                raw = f.read(min(size, 2 * 1024 * 1024))
            text = raw.decode("utf-8", "ignore") + raw.decode("utf-16-le", "ignore")
        except OSError as e:
            text = ""
            if getattr(e, "errno", 0) in (13, 22):
                findings.append({"level": "info", "score": 0, "kind": "file", "target": path,
                                 "rule": "READ-BLOCK", "title": "内容读取被安全软件拦截",
                                 "why": "文件还在但读不开，常见于实时防护已锁定该文件——这条不是漏扫，是系统引擎已经动手了"})
        for r in rules:
            # cmdline 类规则同样扫脚本正文：脚本里通常就是嵌着这些命令行
            if r["scope"] not in ("file", "cmdline"):
                continue
            skip = r.get("exclude_ext") or []
            if skip and any(os.path.basename(path).lower().endswith(str(ext).lower())
                            for ext in skip):
                continue
            if _match(r, text) or _hex_hit(r, path):
                findings.append({"level": r["level"], "score": int(r["weight"]),
                                 "kind": "file", "target": path,
                                 "rule": r["id"], "title": r["name"],
                                 "why": r.get("why", "")})
    # 2) PE：结构异常
    if is_pe and deep:
        info = pe_info(path)
        if not info.get("is_pe"):
            findings.append({"level": "low", "score": 12, "kind": "pe", "target": path,
                             "rule": "PE-0", "title": "MZ 头但 PE 解析失败",
                             "why": info.get("error") or "结构异常"})
        else:
            if info.get("writable_exec_sections"):
                findings.append({"level": "high", "score": 30, "kind": "pe", "target": path,
                                 "rule": "PE-WX", "title": "存在可写且可执行的节",
                                 "why": "节区同时可写+可执行：" + ",".join(info["writable_exec_sections"][:4])})
            if info.get("entry_in_write_section"):
                findings.append({"level": "high", "score": 28, "kind": "pe", "target": path,
                                 "rule": "PE-EP", "title": "入口点落在可写节",
                                 "why": "正常编译器不会把入口放在可写数据段"})
            hi = info.get("high_entropy_sections") or []
            if len(hi) >= 1 and not info.get("signed_dir"):
                findings.append({"level": "medium", "score": 18, "kind": "pe", "target": path,
                                 "rule": "PE-ENT", "title": "高熵节且无签名目录",
                                 "why": "疑似加壳/加密：" + ",".join(hi[:3])})
            bad = [n for n in info.get("section_names", [])
                   if re.search(r"(?i)(upx|\.aspack|\.themida|\.vmp|pec|\.packed)", n or "")]
            if bad:
                findings.append({"level": "medium", "score": 16, "kind": "pe", "target": path,
                                 "rule": "PE-PACK", "title": "疑似加壳节名",
                                 "why": "节名：" + ",".join(bad[:3])})
            if not info.get("signed_dir"):
                findings.append({"level": "info", "score": 4, "kind": "pe", "target": path,
                                 "rule": "PE-NOSIGN", "title": "无数字签名目录",
                                 "why": "未带证书目录（不代表恶意，但降低可信度）"})
            if info.get("timestamp") and info["timestamp"] > int(time.time()) + 7 * 86400:
                findings.append({"level": "info", "score": 4, "kind": "pe", "target": path,
                                 "rule": "PE-TIME", "title": "编译时间在未来",
                                 "why": "时间戳比当前时间晚 7 天以上，可能是构建异常或造假"})
    return findings


def _path_rule_hits(target: str, rules: list) -> list:
    hits = []
    for r in rules:
        if r["scope"] != "path":
            continue
        if _match(r, target):
            hits.append({"level": r["level"], "score": int(r["weight"]), "kind": "path",
                         "target": target, "rule": r["id"], "title": r["name"],
                         "why": r.get("why", "")})
    return hits


def _cmd_rule_hits(cmd: str, rules: list) -> list:
    hits = []
    for r in rules:
        if r["scope"] != "cmdline":
            continue
        if _match(r, cmd):
            hits.append({"level": r["level"], "score": int(r["weight"]), "kind": "cmdline",
                         "target": cmd[:200], "rule": r["id"], "title": r["name"],
                         "why": r.get("why", "")})
    return hits


# ---------------- 持久化审计 ----------------
def _ps(script: str, timeout: int = 45) -> str:
    """跑一段 PowerShell 并取输出。

    注意：中文系统的 PowerShell 默认按 GBK 输出，直接 text=True 会 UnicodeDecodeError
    （实测报 0xbe/0xb2 解码失败，整段结果全丢）。这里强制控制台 UTF-8 + 解码容错。
    """
    try:
        exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                           "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        if not os.path.exists(exe):
            exe = "powershell.exe"
        prefix = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
                  "$OutputEncoding=[System.Text.Encoding]::UTF8;")
        cp = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", prefix + script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (cp.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _json_list(text: str) -> list:
    if not text:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return []
    return data if isinstance(data, list) else [data]


def audit_run_keys() -> list:
    out = _ps(
        "$r=@();"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',"
        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce',"
        "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run' | "
        "ForEach-Object { $p=$_; if(Test-Path $p){ (Get-Item $p).Property | ForEach-Object { "
        "$v=(Get-ItemProperty -Path $p -Name $_).$_; if($v){ $r += [ordered]@{loc=$p;name=$_;cmd=[string]$v} } } } };"
        "$r | ConvertTo-Json -Compress -Depth 3")
    items = []
    for it in _json_list(out):
        items.append({"kind": "run", "loc": str(it.get("loc", "")),
                      "name": str(it.get("name", "")), "cmd": str(it.get("cmd", ""))})
    return items


def audit_startup_folders() -> list:
    out = _ps(
        "$r=@(); $dirs=@(\"$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\","
        "\"$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\");"
        "$dirs | ForEach-Object { $d=$_; if(Test-Path $d){ Get-ChildItem -LiteralPath $d -File "
        "-ErrorAction SilentlyContinue | ForEach-Object { $r += [ordered]@{dir=$d;file=$_.FullName} } } };"
        "$r | ConvertTo-Json -Compress")
    items = []
    for it in _json_list(out):
        items.append({"kind": "startup", "loc": str(it.get("dir", "")),
                      "name": os.path.basename(str(it.get("file", ""))),
                      "cmd": str(it.get("file", ""))})
    return items


def audit_tasks() -> list:
    out = _ps(
        "Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object { "
        "$a=$_.Actions | Select-Object -First 1; [ordered]@{name=$_.TaskName; path=$_.TaskPath;"
        "state=[string]$_.State; exec=[string]$a.Execute; args=[string]$a.Arguments} } | "
        "ConvertTo-Json -Compress -Depth 3")
    items = []
    for it in _json_list(out):
        exe = str(it.get("exec", ""))
        items.append({"kind": "task", "loc": str(it.get("path", "")) + str(it.get("name", "")),
                      "name": str(it.get("name", "")),
                      "cmd": (exe + " " + str(it.get("args", ""))).strip()})
    return items


def audit_services() -> list:
    out = _ps(
        "Get-CimInstance Win32_Service -ErrorAction SilentlyContinue | ForEach-Object { "
        "[ordered]@{name=$_.Name; disp=$_.DisplayName; path=[string]$_.PathName; start=[string]$_.StartMode} } | "
        "ConvertTo-Json -Compress -Depth 3")
    items = []
    for it in _json_list(out):
        items.append({"kind": "service", "loc": str(it.get("name", "")),
                      "name": str(it.get("disp", "")), "cmd": str(it.get("path", "")),
                      "start": str(it.get("start", ""))})
    return items


def audit_ifeo() -> list:
    out = _ps(
        "$base='HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Image File Execution Options';"
        "$r=@(); if(Test-Path $base){ Get-ChildItem $base | ForEach-Object { "
        "$d=(Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue).Debugger; "
        "if($d){ $r += [ordered]@{name=$_.PSChildName; cmd=[string]$d} } } };"
        "$r | ConvertTo-Json -Compress -Depth 3")
    items = []
    for it in _json_list(out):
        items.append({"kind": "ifeo", "loc": "IFEO", "name": str(it.get("name", "")),
                      "cmd": str(it.get("cmd", ""))})
    return items


def audit_persistence() -> list:
    """四类持久化点合并；单点失败不影响其余（每类单独 try）。"""
    items = []
    for fn in (audit_run_keys, audit_startup_folders, audit_tasks, audit_services, audit_ifeo):
        try:
            items.extend(fn() or [])
        except Exception as e:  # noqa: BLE001
            _log(f"{fn.__name__} 失败：{e}")
    return items


def _exe_from_cmd(cmd: str) -> str:
    """从命令行里抠出可执行路径（支持带引号、带参数、带 svchost 形式）。"""
    c = (cmd or "").strip()
    if not c:
        return ""
    if c.startswith('"'):
        end = c.find('"', 1)
        return c[1:end] if end > 0 else c.strip('"')
    # 整串本身就是一个存在的文件（启动文件夹里的 .lnk 属于这种，不能再按空格切）
    if os.path.exists(c):
        return c
    m = re.match(r"(?i)^([a-z]:\\[^\s\"]+(?:\s[^\s\"]+)*?\.(?:exe|dll|bat|cmd|ps1|vbs|js|scr|com))",
                 c)
    if m:
        return m.group(1)
    m = re.match(r"(?i)^(%[a-z0-9_%]+%\\[^\s\"]+)", c)
    if m:
        return os.path.expandvars(m.group(1))
    return c.split(" ")[0].strip('"')


def audit_processes() -> list:
    """运行中进程的命令行（无文件攻击只在内存里跑，光查文件会漏）。

    只读：Get-CimInstance Win32_Process。取不到 CommandLine 的进程跳过。
    """
    out = _ps(
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | ForEach-Object { "
        "[ordered]@{name=$_.Name; pid=$_.ProcessId; path=[string]$_.ExecutablePath; "
        "cmd=[string]$_.CommandLine} } | ConvertTo-Json -Compress -Depth 3", timeout=50)
    items = []
    for it in _json_list(out):
        cmd = str(it.get("cmd", "") or "")
        if not cmd:
            continue
        items.append({"kind": "process", "loc": str(it.get("pid", "")),
                      "name": str(it.get("name", "")), "cmd": cmd,
                      "path": str(it.get("path", ""))})
    return items


def judge_persistence(items: list, rules: list) -> list:
    """给每条持久化项打风险：路径可疑 + LOLBin + 文件不存在 + 规则命中。

    系统/程序目录里的项目先豁免"目录可疑"加分，否则 Defender 自己的计划任务会被误报。
    """
    out = []
    for it in items:
        score, why = 0, []
        cmd = it.get("cmd", "") or ""
        is_proc = it.get("kind") == "process"
        # 进程只认主程序路径；命令行里出现 temp 字样很常见（缓存目录参数），不能据此判可疑
        target = it.get("path", "") if is_proc else _exe_from_cmd(cmd)
        low = (target if is_proc else cmd).lower()
        trusted = (not low) or any(low.startswith(p) or p in low for p in TRUSTED_PREFIXES)
        # 「开始菜单 → 程序 → 启动」是所有正常开机启动项的法定位置，不该因为落在 Roaming 里就加分
        if "\\start menu\\programs\\startup\\" in low:
            trusted = True
        if not trusted and any(h in low for h in SUSPICIOUS_DIR_HINTS):
            score += 22
            why.append("位于临时/下载/漫游/公共目录")
        # LOLBin 加分只算常驻项：一次性进程用 pwsh/curl 太正常了
        if not trusted and not is_proc:
            for lb in LOLBINS:
                if lb in cmd.lower():
                    score += 14
                    why.append(f"用了系统自带工具 {lb}")
                    break
        if target and ("\\" in target) and not os.path.exists(os.path.expandvars(target)):
            score += 12
            why.append("目标文件不存在（已卸载残留或指向失效路径）")
        long_limit = 420 if is_proc else 260
        if len(cmd) > long_limit:
            score += 8
            why.append("命令行超长（疑似编码/拼接）")
        if it.get("kind") in ("run", "startup") and re.search(
                r"(?i)[a-f0-9]{6,}\.(exe|dll|scr)$", target or ""):
            score += 12
            why.append("文件名是无意义十六进制串")
        hits = _cmd_rule_hits(cmd, rules) if cmd else []
        for h in hits:
            score += int(h["score"] * 0.6)
            why.append(f"{h['rule']} {h['title']}")
        if it.get("kind") == "ifeo":
            score += 26
            why.append("IFEO 调试器劫持：指定程序被替换启动")
        level = "high" if score >= 45 else "medium" if score >= 22 else "low" if score >= 10 else "info"
        out.append({**it, "target": target, "score": min(score, 100), "level": level,
                    "why": "；".join(why) or "无明显可疑点"})
    return out


# ---------------- 目标文件扫描 ----------------
def scan_roots() -> list:
    """常见投毒落地目录（只读遍历，限制文件数与大小）。"""
    env = os.environ
    roots = [
        os.path.join(env.get("TEMP", tempfile.gettempdir()), ""),
        os.path.join(env.get("LOCALAPPDATA", ""), "Temp"),
        os.path.join(env.get("USERPROFILE", ""), "Downloads"),
        os.path.join(env.get("USERPROFILE", ""), "Desktop"),
        os.path.join(env.get("PUBLIC", r"C:\Users\Public"), ""),
        os.path.join(env.get("APPDATA", ""), ""),
    ]
    seen, out = set(), []
    for r in roots:
        if r and os.path.isdir(r):
            key = os.path.normcase(os.path.abspath(r))
            if key not in seen:
                seen.add(key)
                out.append(r)
    return out


def collect_targets(roots: list = None, limit: int = MAX_FILES,
                    max_mb: int = MAX_FILE_MB) -> list:
    """收集候选文件。

    排除开发依赖与缓存目录（node_modules/site-packages/.git/缓存/WinSxS）——
    实测不排除时，Firefox 与 npm 的正常 JS 会连带把风险分推到「高」，纯噪音。
    """
    roots = roots or scan_roots()
    skip_names = {"node_modules", "site-packages", "__pycache__", ".git", ".cache",
                  "cache", "cache2", "winsxs", "vendor", "dist-info", "tempcache"}
    got = []
    for root in roots:
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames
                               if not d.startswith("$") and d.lower() not in skip_names][:40]
                skip_here = any(s in os.path.normcase(dirpath) + "\\" for s in
                                ("\\node_modules\\", "\\site-packages\\", "\\.git\\"))
                if skip_here:
                    continue
                for fn in filenames:
                    if len(got) >= limit * 3:
                        break
                    if not fn.lower().endswith(SCAN_EXTS):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size == 0 or st.st_size > max_mb * 1024 * 1024:
                        continue
                    got.append((st.st_mtime, p))
                if len(got) >= limit * 3:
                    break
        except OSError:
            continue
    got.sort(key=lambda x: -x[0])          # 最近落地的优先
    return [p for _, p in got[:limit]]


# ---------------- 汇总 ----------------
def score_of(findings: list) -> int:
    """风险分：多个独立证据相加，最高 100（单一高权重不封顶到 100）。"""
    total = 0
    for f in findings:
        total += int(f.get("score", 0))
    return min(total, 100)


def level_of(score: int) -> str:
    if score >= 60:
        return "高"
    if score >= 35:
        return "中"
    if score >= 15:
        return "低"
    return "提示"


def deep_scan(roots: list = None, deep: bool = True,
              progress=None) -> dict:
    """完整扫描：持久化审计 + 目标文件规则/PE 扫描 + 汇总。"""
    t0 = time.time()
    rules = load_rules()
    errors = []

    def _p(step, msg):
        if progress:
            try:
                progress(step, msg)
            except Exception:  # noqa: BLE001
                pass

    _p(5, "读持久化点（Run/启动文件夹/计划任务/服务/IFEO）…")
    persist = []
    try:
        persist = judge_persistence(audit_persistence(), rules)
    except Exception as e:  # noqa: BLE001
        errors.append(f"持久化审计失败：{e}")

    _p(20, "看正在运行的进程命令行…")
    procs = []
    proc_total = 0
    try:
        procs_all = judge_persistence(audit_processes(), rules)
        proc_total = len(procs_all)
        procs = [p for p in procs_all if p["score"] >= 10]
    except Exception as e:  # noqa: BLE001
        errors.append(f"进程审计失败：{e}")

    _p(25, "找可疑落点目录里的可执行文件…")
    targets = collect_targets(roots)
    _p(30, f"待查文件 {len(targets)} 个，开始逐个解析…")
    file_findings = []
    for i, p in enumerate(targets):
        try:
            file_findings.extend(scan_file(p, rules, deep=deep))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{os.path.basename(p)}：{e}")
        if i % 20 == 0:
            _p(30 + int(60 * i / max(1, len(targets))), f"已解析 {i}/{len(targets)}")

    persist_findings = []
    for it in persist:
        if it["score"] >= 10:
            persist_findings.append({
                "level": it["level"], "score": it["score"], "kind": it["kind"],
                "target": it["target"], "title": f"{it['kind']}：{it['name'] or it['loc']}",
                "why": it["why"], "rule": "PERSIST"})
    proc_findings = []
    for it in procs:
        proc_findings.append({
            "level": it["level"], "score": it["score"], "kind": "process",
            "target": it["target"], "title": f"进程 {it['name']}（PID {it['loc']}）",
            "why": it["why"], "rule": "PROC"})

    pscore = max([f.get("score", 0) for f in persist_findings + proc_findings] or [0])
    fscore = max([f.get("score", 0) for f in file_findings] or [0])
    # 总分口径：单条最高分 + 其他线索数量的轻加成（10/条高危、4/条中危），上限 30。
    # 不用简单相加，否则 6 个低权重样本也能把分数堆到 100，看着吓人但不准。
    all_f = persist_findings + proc_findings + file_findings
    high_n = sum(1 for f in all_f if f.get("level") == "high")
    med_n = sum(1 for f in all_f if f.get("level") == "medium")
    bonus = min(30, high_n * 10 + med_n * 4)
    total = min(100, max(pscore, fscore) + bonus)
    findings = sorted(all_f,
                      key=lambda f: (-int(f.get("score", 0)), f.get("target", "")))
    report = {
        "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": total, "level": level_of(total),
        "counts": {"high": sum(1 for f in findings if f["level"] == "high"),
                   "medium": sum(1 for f in findings if f["level"] == "medium"),
                   "low": sum(1 for f in findings if f["level"] == "low"),
                   "info": sum(1 for f in findings if f["level"] == "info")},
        "findings": findings,
        "persistence": persist,
        "processes_checked": proc_total,
        "files_scanned": len(targets),
        "rules": len(rules),
        "errors": errors[:8],
        "elapsed_s": round(time.time() - t0, 1),
        "mode": "只读研判，未删除/未隔离任何文件",
    }
    _p(100, f"完成：{len(findings)} 条线索，{report['elapsed_s']}s")
    return report


def report_markdown(rep: dict) -> str:
    lines = [
        "# 鲸鱼娘安全管家 · 扫描报告",
        "",
        f"- 扫描时间：{rep.get('checked_at', '')}",
        f"- 风险分：**{rep.get('score', 0)} / 100**（{rep.get('level', '')}）",
        f"- 线索：高危 {rep['counts']['high']} · 中危 {rep['counts']['medium']} · "
        f"低危 {rep['counts']['low']} · 提示 {rep['counts']['info']}",
        f"- 已解析文件：{rep.get('files_scanned', 0)} 个 · 规则 {rep.get('rules', 0)} 条 · "
        f"耗时 {rep.get('elapsed_s', 0)}s",
        f"- 处置方式：{rep.get('mode', '')}",
        "",
        "## 线索明细",
        "",
        "| 等级 | 权重 | 类型 | 对象 | 原因 | 规则 |",
        "|---|---|---|---|---|---|",
    ]
    for f in rep.get("findings", [])[:120]:
        obj = str(f.get("target", "")).replace("|", "\\|")[:90]
        why = str(f.get("why", "")).replace("|", "\\|")[:110]
        lines.append(f"| {f.get('level', '')} | {f.get('score', 0)} | {f.get('kind', '')} | "
                     f"{obj} | {why} | {f.get('rule', '')} |")
    if rep.get("errors"):
        lines += ["", "## 未能完成的子项", ""] + [f"- {e}" for e in rep["errors"]]
    lines += ["", "> 本报告只做只读研判，没有删除或隔离任何文件。"
                   "需要处置时请用「交给 Defender 深扫」，由官方引擎判定与清理。"]
    return "\n".join(lines)


def save_report(rep: dict, out_dir: str = "") -> dict:
    """落盘 md + json，返回路径。"""
    d = out_dir or os.path.join(_data_root(), "reports")
    os.makedirs(d, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    md = os.path.join(d, f"guard_{stamp}.md")
    js = os.path.join(d, f"guard_{stamp}.json")
    try:
        with open(md, "w", encoding="utf-8") as f:
            f.write(report_markdown(rep))
        with open(js, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        return {"md": md, "json": js}
    except OSError as e:
        return {"error": str(e)}


# ---------------- Defender 交接 ----------------
def mpcmdrun_path() -> str:
    cands = [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                          "Windows Defender", "MpCmdRun.exe")]
    plat = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                        "Microsoft", "Windows Defender", "Platform")
    if os.path.isdir(plat):
        try:
            vers = sorted(os.listdir(plat), reverse=True)
            for v in vers[:6]:
                cands.append(os.path.join(plat, v, "MpCmdRun.exe"))
        except OSError:
            pass
    for c in cands:
        if os.path.exists(c):
            return c
    return ""


def defender_scan(paths: list = None, quick: bool = False, timeout: int = 900) -> dict:
    """把可疑文件（或整机快扫）交给 Defender。只扫描，处置交给它自己。"""
    exe = mpcmdrun_path()
    if not exe:
        return {"ok": False, "msg": "找不到 MpCmdRun.exe（Defender 可能被第三方杀软接管）"}
    args = [exe, "-Scan"]
    if quick or not paths:
        args += ["-ScanType", "1"]
    else:
        args += ["-ScanType", "3", "-File", paths[0]]
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = ((cp.stdout or "") + (cp.stderr or ""))[-1500:]
        return {"ok": cp.returncode == 0, "code": cp.returncode, "msg": out.strip()[:400]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "msg": f"扫描超时（>{timeout}s）"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": str(e)[:200]}


# ---------------- 线程封装 ----------------
def _qt():
    from PySide6.QtCore import QThread, Signal
    return QThread, Signal


try:
    QThread, Signal = _qt()

    class GuardWorker(QThread):
        """后台跑完整扫描，进度用 (百分比, 描述) 回主线程。"""
        progress = Signal(int, str)
        done = Signal(dict)
        failed = Signal(str)

        def __init__(self, roots: list = None, deep: bool = True):
            super().__init__()
            self.roots = roots
            self.deep = deep
            self._stop = False

        def stop(self):
            self._stop = True

        def run(self):
            try:
                rep = deep_scan(self.roots, self.deep,
                                progress=lambda p, m: self.progress.emit(int(p), m))
            except Exception as e:  # noqa: BLE001
                self.failed.emit(str(e)[:200])
                return
            if self._stop:
                return
            self.done.emit(rep)

    class DefenderWorker(QThread):
        """交接给 Defender 扫描（单文件优先，没有可疑文件就快扫）。"""
        done = Signal(dict)

        def __init__(self, paths: list = None, quick: bool = False):
            super().__init__()
            self.paths = paths or []
            self.quick = quick

        def run(self):
            self.done.emit(defender_scan(self.paths, self.quick))
except Exception:  # noqa: BLE001
    # 非 GUI 环境（脚本/单测）也允许 import 本模块
    GuardWorker = None
    DefenderWorker = None
