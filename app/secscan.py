# -*- coding: utf-8 -*-
"""安全体检：只读检查系统安全状态并生成报告，不写杀毒引擎、不删除任何文件。

检查项：
1. Microsoft Defender 实时防护 / 病毒库时间 / 上次扫描
2. 开机自启动项（注册表 Run 键 + 启动文件夹）
3. 高危端口监听（常见远控端口）
4. 可疑进程名（少量已知挖矿/远控命名特征）

所有信息仅在本机读取与展示，不上传。
"""
import json
import os
import subprocess

from PySide6.QtCore import QThread, Signal

PS_TIMEOUT = 25

# PowerShell 7 无法导入 Defender 的 Windows 模块，必须用 Windows PowerShell 5.1。
# 某些环境 PATH 被改写后找不到 powershell.exe，因此优先用绝对路径。
_PS_CANDIDATES = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe",
]


def _ps_exe() -> str:
    for p in _PS_CANDIDATES:
        if os.path.exists(p):
            return p
    return "powershell"

# 只在名字层面命中的粗筛清单，命中不代表恶意，仅提示人工确认
SUSPECT_TOKENS = [
    "xmrig", "miner", "coinminer", "cpuminer", "nbminer",
    "njrat", "remcos", "asyncrat", "quasar", "dcrat", "gh0st",
    "teamviewer_host", "anydesk_host", "mimikatz", "lazagne",
]

REMOTE_PORTS = {3389: "远程桌面 RDP", 5900: "VNC", 4444: "常见反弹端口",
                1337: "常见后门端口", 31337: "常见后门端口", 6667: "IRC 僵尸网络",
                1080: "SOCKS 代理", 9050: "TOR"}


def _run_ps(script: str, timeout: int = PS_TIMEOUT) -> str:
    try:
        proc = subprocess.run(
            [_ps_exe(), "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout,
            creationflags=0x08000000)  # v2.9.9：禁掉控制台窗口，别每点一次体检就闪黑框
        return (proc.stdout or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def av_health() -> dict:
    """病毒库/引擎健康度：版本、签名日期、签名年龄（天）、上次快扫。"""
    out = _run_ps(
        "$s=Get-MpComputerStatus -ErrorAction SilentlyContinue;"
        "if($s){[ordered]@{"
        "sig_ver=[string]$s.AntivirusSignatureVersion;"
        "sig_time=[string]$s.AntivirusSignatureLastUpdated;"
        "sig_age=[int]$s.AntivirusSignatureAge;"
        "engine=[string]$s.AMEngineVersion;"
        "platform=[string]$s.AMProductVersion;"
        "quick=[string]$s.QuickScanEndTime;"
        "}|ConvertTo-Json -Compress}else{'{}'}"
    )
    if not out:
        return {"ok": False, "reason": "读不到 Defender 病毒库状态"}
    try:
        data = json.loads(out)
    except ValueError:
        return {"ok": False, "reason": "病毒库状态解析失败"}
    if not data:
        return {"ok": False, "reason": "Defender 未启用，无病毒库信息"}
    return {
        "ok": True,
        "sig_ver": str(data.get("sig_ver") or ""),
        "sig_time": str(data.get("sig_time") or ""),
        "sig_age": int(data.get("sig_age") or 0),
        "engine": str(data.get("engine") or ""),
        "platform": str(data.get("platform") or ""),
        "quick": str(data.get("quick") or ""),
        "stale": int(data.get("sig_age") or 0) >= 3,
    }


def firewall_status() -> list:
    """三个防火墙配置档的开关与默认策略。"""
    out = _run_ps(
        "Get-NetFirewallProfile -ErrorAction SilentlyContinue | "
        "Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction | "
        "ConvertTo-Json -Compress -Depth 3"
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    rows = []
    for it in data or []:
        rows.append({
            "name": str(it.get("Name") or ""),
            "enabled": bool(it.get("Enabled")),
            "in": str(it.get("DefaultInboundAction") or ""),
            "out": str(it.get("DefaultOutboundAction") or ""),
        })
    return rows


def threat_history(days: int = 7) -> dict:
    """近 N 天 Defender 的拦截记录（时间/威胁名/是否已处置）。

    Get-MpThreatDetection 在部分机器上需要更高权限，读不到就返回空并标注。
    """
    out = _run_ps(
        "$t=@{};"
        "Get-MpThreat -ErrorAction SilentlyContinue | ForEach-Object { "
        "$t[[string]$_.ThreatID]=[string]$_.ThreatName };"
        f"$d=(Get-Date).AddDays(-{days});"
        "$r=@();"
        "Get-MpThreatDetection -ErrorAction SilentlyContinue | "
        "Where-Object { $_.InitialDetectionTime -ge $d } | ForEach-Object { "
        "$r += [ordered]@{time=[string]$_.InitialDetectionTime;"
        "id=[string]$_.ThreatID;"
        "name=$t[[string]$_.ThreatID];"
        "action=[string]$_.ActionSuccess } };"
        "$r | ConvertTo-Json -Compress -Depth 3"
    )
    if not out:
        return {"ok": True, "items": [], "note": "近 %d 天没有拦截记录（或需要管理员权限才能读）" % days}
    try:
        data = json.loads(out)
    except ValueError:
        return {"ok": False, "items": [], "note": "拦截记录解析失败"}
    if isinstance(data, dict):
        data = [data]
    items = []
    for it in data or []:
        items.append({
            "time": str(it.get("time") or ""),
            "name": str(it.get("name") or "未知威胁"),
            "action": str(it.get("action") or ""),
        })
    return {"ok": True, "items": items, "note": ""}


def update_signatures() -> dict:
    """触发一次 Defender 病毒库更新（官方 MpCmdRun），失败不影响程序。"""
    out = _run_ps(
        "$p=(Get-ChildItem \"$env:ProgramData\\Microsoft\\Windows Defender\\Platform\" "
        "-Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | "
        "Select-Object -First 1).FullName;"
        "if($p){ & \"$p\\MpCmdRun.exe\" -SignatureUpdate }else{ 'NO_MPCMDRUN' }",
        timeout=150
    )
    low = (out or "").lower()
    if "no_mpcmdrun" in low:
        return {"ok": False, "msg": "找不到 MpCmdRun.exe，可能被第三方杀软接管"}
    # 本机实测：MpCmdRun 正常结束只打印 "Signature update finished."，
    # 没有 "applied"；所以用 finished + 排除错误码来判定
    good = any(k in low for k in ("signature update applied", "update applied",
                                  "signature update finished", "成功"))
    bad = any(k in low for k in ("failed", "error", "0x800", "0x8024", "无法", "失败"))
    return {"ok": bool(good and not bad), "msg": (out or "")[-200:].strip() or "无输出"}


def defender_status() -> dict:
    out = _run_ps(
        "$s=Get-MpComputerStatus -ErrorAction SilentlyContinue;"
        "if($s){"
        "$o=[ordered]@{"
        "realtime=[bool]$s.RealTimeProtectionEnabled;"
        "enabled=[bool]$s.AntivirusEnabled;"
        "sig=[string]$s.AntivirusSignatureLastUpdated;"
        "scan=[string]$s.QuickScanEndTime;"
        "threats=[string]$s.ThreatIDDefaultActionIds;"
        "};$o|ConvertTo-Json -Compress}else{'{}'}"
    )
    if not out:
        return {"ok": False, "reason": "读取 Defender 状态失败（可能被第三方杀软接管）"}
    try:
        data = json.loads(out)
    except ValueError:
        return {"ok": False, "reason": "Defender 状态解析失败"}
    if not data:
        return {"ok": False, "reason": "未安装或被禁用"}
    return {
        "ok": True,
        "realtime": data.get("realtime"),
        "enabled": data.get("enabled"),
        "sig_time": data.get("sig", ""),
        "last_scan": data.get("scan", ""),
    }


def startup_items() -> list:
    out = _run_ps(
        "$r=@();"
        "'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
        "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run',"
        "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run' | "
        "ForEach-Object { $p=$_; if(Test-Path $p){ "
        "(Get-Item $p).Property | ForEach-Object { "
        "$v=(Get-ItemProperty -Path $p -Name $_).$_; "
        "if($v){ $r += [ordered]@{name=$_; cmd=[string]$v} } } } };"
        "$r | ConvertTo-Json -Compress -Depth 3"
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    items = []
    for it in data or []:
        name = str(it.get("name", "")).strip()
        cmd = str(it.get("cmd", "")).strip()
        if name:
            items.append({"name": name, "cmd": cmd[:160], "system": cmd.lower().startswith(("c:\\windows", "c:\\program files\\windows"))})
    return items


def listening_ports() -> list:
    out = _run_ps(
        "Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -Property LocalPort,OwningProcess | ConvertTo-Json -Compress"
    )
    if not out:
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return []
    if isinstance(data, dict):
        data = [data]
    hits = []
    for it in data or []:
        try:
            port = int(it.get("LocalPort"))
        except (TypeError, ValueError):
            continue
        if port in REMOTE_PORTS:
            hits.append({"port": port, "desc": REMOTE_PORTS[port],
                         "pid": it.get("OwningProcess")})
    # IPv4/IPv6 会各报一次同一端口，按 (端口, PID) 去重
    seen, uniq = set(), []
    for h in hits:
        key = (h["port"], h["pid"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return uniq


def suspect_processes() -> list:
    hits = []
    try:
        out = subprocess.run(
            [_ps_exe(), "-NoProfile", "-NonInteractive", "-Command",
             "Get-Process | Select-Object -ExpandProperty ProcessName | Sort-Object -Unique"],
            capture_output=True, text=True, encoding="utf-8", timeout=PS_TIMEOUT,
            creationflags=0x08000000)
        names = [n.strip().lower() for n in (out.stdout or "").splitlines() if n.strip()]
    except Exception:  # noqa: BLE001
        names = []
    for n in names:
        for tok in SUSPECT_TOKENS:
            if tok in n:
                hits.append(n)
                break
    return sorted(set(hits))


def build_report() -> dict:
    dv = defender_status()
    av = av_health()
    fw = firewall_status()
    th = threat_history(7)
    starts = startup_items()
    ports = listening_ports()
    procs = suspect_processes()

    issues = []
    if not dv.get("ok"):
        issues.append({"level": "warn", "text": dv.get("reason", "无法确认 Defender 状态")})
    else:
        if not dv.get("realtime"):
            issues.append({"level": "high", "text": "Defender 实时防护已关闭"})
        if not dv.get("enabled"):
            issues.append({"level": "high", "text": "Defender 杀毒功能已关闭"})
        if not dv.get("sig_time"):
            issues.append({"level": "warn", "text": "未读到病毒库更新时间"})
        if not dv.get("last_scan"):
            issues.append({"level": "warn", "text": "未读到上次快速扫描时间"})

    if av.get("ok") and av.get("stale"):
        issues.append({"level": "high",
                       "text": f"病毒库已 {av['sig_age']} 天未更新（版本 {av['sig_ver']}）"})
    off_fw = [f["name"] for f in fw if not f["enabled"]]
    if off_fw:
        issues.append({"level": "high", "text": "防火墙已关闭：" + "、".join(off_fw)})
    n_th = len(th.get("items") or [])
    if n_th:
        issues.append({"level": "info",
                       "text": f"近 7 天 Defender 拦截 {n_th} 次，最近一次：{th['items'][0]['name']}"})

    user_starts = [s for s in starts if not s.get("system")]
    if user_starts:
        issues.append({"level": "info", "text": f"发现 {len(user_starts)} 个用户级开机自启动项，建议逐条确认来源"})
    for p in ports:
        issues.append({"level": "warn", "text": f"端口 {p['port']}（{p['desc']}）处于监听，进程 PID {p['pid']}"})
    for n in procs:
        issues.append({"level": "warn", "text": f"进程名命中可疑特征：{n}（需人工确认，可能是误报）"})

    score = 100
    for it in issues:
        if it["level"] == "high":
            score -= 30
        elif it["level"] == "warn":
            score -= 8
        elif it["level"] == "info":
            score -= 2
    score = max(0, score)

    return {
        "defender": dv,
        "av": av,
        "firewall": fw,
        "threats": th,
        "startup": starts,
        "ports": ports,
        "suspect": procs,
        "issues": issues,
        "score": score,
        "checked_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
    }


def defense_summary() -> str:
    """给开机早报用的一句话安全播报（只读，耗时约 3-6 秒）。"""
    av = av_health()
    fw = firewall_status()
    th = threat_history(7)
    parts = []
    if av.get("ok"):
        age = av.get("sig_age", 0)
        state = "需更新" if av.get("stale") else "已是最新"
        parts.append(f"病毒库 {av.get('sig_ver') or '未知版'}（{age} 天，{state}）")
    else:
        parts.append("病毒库状态读不到")
    off = [f["name"] for f in fw if not f["enabled"]]
    if not fw:
        parts.append("防火墙状态读不到")
    elif off:
        parts.append("防火墙已关闭：" + "、".join(off))
    else:
        parts.append("防火墙 3 档全部开启")
    n = len(th.get("items") or [])
    if n:
        recent = th["items"][0]
        parts.append(f"近 7 天拦截 {n} 次（最近 {recent['name']}）")
    else:
        parts.append("近 7 天无拦截记录")
    return "；".join(parts)


def openscan_hint() -> str:
    return "建议操作：Windows 安全中心 → 病毒和威胁防护 → 快速扫描"


class ScanWorker(QThread):
    done = Signal(dict)

    def run(self):
        self.done.emit(build_report())


class SummaryWorker(QThread):
    """只取一句安全摘要，开机早报用（比全量体检快）。"""
    done = Signal(str)

    def run(self):
        try:
            self.done.emit(defense_summary())
        except Exception:  # noqa: BLE001
            self.done.emit("")


class FirewallWorker(QThread):
    """每周体检用：只读三档开关。"""
    done = Signal(list)

    def run(self):
        try:
            self.done.emit(firewall_status())
        except Exception:  # noqa: BLE001
            self.done.emit([])


class UpdateWorker(QThread):
    """后台更新病毒库，不阻塞界面。"""
    done = Signal(bool, str)

    def run(self):
        try:
            r = update_signatures()
            self.done.emit(bool(r.get("ok")), str(r.get("msg", "")))
        except Exception as e:  # noqa: BLE001
            self.done.emit(False, str(e)[:100])
