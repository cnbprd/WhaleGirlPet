# -*- coding: utf-8 -*-
"""P3：网络安全资料的学习路线索引。

只扫描文件名/目录名和大小，不读取 PDF/视频正文，也不把资料打包进安装包。
对外展示时按“基础 → 攻击面认知 → 防御专题”分组；攻击面课程只作为目录索引，
不提供任何操作步骤。
"""
import os

LIBRARY_ROOT = r"F:\数据"
COURSE_ROOT = os.path.join(LIBRARY_ROOT, "网络安全-攻防实战课")
TEXT_ROOT = os.path.join(LIBRARY_ROOT, "网络安全-文字资料（PDF版）")
NOTES_ROOT = os.path.join(LIBRARY_ROOT, "一些网络安全笔记")

COURSE_01 = os.path.join(COURSE_ROOT, "01.网络安全攻防实战课")
COURSE_02 = os.path.join(COURSE_ROOT, "02.Kali Linux渗透测试")
COURSE_03 = os.path.join(COURSE_ROOT, "03.Web安全渗透测试与安全防御")

TEXT_DIRS = [
    "操作系统安全策略", "防火墙", "日志清除", "恶意代码", "Rootkit",
    "WEB安全", "漏洞攻击", "拒绝服务攻击", "网络欺骗", "网络扫描",
    "网络嗅探", "网络抓包", "无线安全", "网络设备攻击与安全配置",
    "Windows内核", "逆向工程", "汇编语言", "Linux",
]

ROUTES = [
    {
        "stage": "01 基础",
        "title": "网络与安全入门",
        "why": "先建立协议、边界和账号模型，再看攻击面。",
        "paths": [COURSE_01],
        "prefixes": ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "15."),
    },
    {
        "stage": "02 攻击面认知",
        "title": "Kali / 渗透课程（只看目录）",
        "why": "知道攻击者会看哪些面，才能收窄暴露；这里只索引标题，不提取步骤。",
        "paths": [COURSE_02],
        "prefixes": (),
    },
    {
        "stage": "03 Web 防御",
        "title": "Web 安全与防御",
        "why": "围绕输入边界、文件上传、权限和日志做防守。",
        "paths": [COURSE_03],
        "prefixes": (),
    },
    {
        "stage": "04 系统面",
        "title": "Windows 策略 / 账号 / 日志 / 防火墙",
        "why": "把 UAC、远程面、Guest、自动播放、日志大小这些检查项对应回资料。",
        "paths": [os.path.join(TEXT_ROOT, d) for d in
                 ("操作系统安全策略", "防火墙", "日志清除", "网络欺骗", "网络扫描")],
        "prefixes": (),
    },
    {
        "stage": "05 恶意代码",
        "title": "木马 / Rootkit / 逆向",
        "why": "只取“落地信号、持久化、驱动异常”的防守视角。",
        "paths": [os.path.join(TEXT_ROOT, d) for d in
                 ("恶意代码", "Rootkit", "逆向工程", "Windows内核")],
        "prefixes": (),
    },
    {
        "stage": "06 流量与拒绝服务",
        "title": "DDoS / 嗅探 / 无线",
        "why": "从流量洪峰、抓包和无线暴露面理解监控与限流。",
        "paths": [os.path.join(TEXT_ROOT, d) for d in
                 ("拒绝服务攻击", "网络嗅探", "网络抓包", "无线安全", "漏洞攻击")],
        "prefixes": (),
    },
    {
        "stage": "07 笔记",
        "title": "学习笔记与命令速查",
        "why": "作为查阅索引，不替代实际操作手册。",
        "paths": [NOTES_ROOT],
        "prefixes": (),
    },
]


def _files_under(root: str) -> list:
    if not os.path.isdir(root):
        return []
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            out.append({
                "name": name,
                "path": path,
                "size_mb": round(size / 1024 / 1024, 1),
                "dir": os.path.basename(dirpath),
            })
    return out


def _route_files(route: dict) -> list:
    files = []
    seen = set()
    for root in route.get("paths") or []:
        for f in _files_under(root):
            if f["path"] in seen:
                continue
            seen.add(f["path"])
            if route.get("prefixes"):
                if not any(f["name"].startswith(p) for p in route["prefixes"]):
                    continue
            files.append(f)
    return sorted(files, key=lambda x: x["name"])


def scan_library() -> dict:
    """返回按路线分组的索引；目录不存在时也返回结构，不抛异常。"""
    sections = []
    for route in ROUTES:
        files = _route_files(route)
        if not files:
            continue
        sections.append({
            "stage": route["stage"],
            "title": route["title"],
            "why": route["why"],
            "count": len(files),
            "size_mb": round(sum(f["size_mb"] for f in files), 1),
            "files": files,
        })
    total_files = sum(s["count"] for s in sections)
    total_mb = round(sum(s["size_mb"] for s in sections), 1)
    return {
        "ok": bool(sections),
        "root": LIBRARY_ROOT,
        "sections": sections,
        "total_files": total_files,
        "total_mb": total_mb,
        "note": "只索引文件名/路径，不读取正文，不打包进安装包。",
    }


def summary_lines(max_titles: int = 4) -> list:
    """给安全页/文档用的短摘要，默认每个阶段只列几条标题。"""
    data = scan_library()
    if not data["ok"]:
        return [f"资料目录不在：{LIBRARY_ROOT}"]
    lines = [f"资料根目录：{data['root']}（{data['total_files']} 个文件 / {data['total_mb']} MB）"]
    for s in data["sections"]:
        lines.append(f"{s['stage']}｜{s['title']}：{s['count']} 个文件 / {s['size_mb']} MB")
        for f in s["files"][:max_titles]:
            lines.append(f"  · {f['name']}")
        if s["count"] > max_titles:
            lines.append(f"  · …另有 {s['count'] - max_titles} 个")
    lines.append("只索引标题和本地路径，不读取正文，不提供操作步骤。")
    return lines


def route_text() -> str:
    """完整目录索引（只列名字/路径/大小），用于“学习路线”弹窗。"""
    data = scan_library()
    if not data["ok"]:
        return f"资料目录不在：{LIBRARY_ROOT}"
    out = [f"网络安全资料索引：{data['root']}", f"合计 {data['total_files']} 个文件 / {data['total_mb']} MB",
           "说明：只索引文件名与路径，不读取正文，不提供攻击步骤。", ""]
    for s in data["sections"]:
        out.append(f"== {s['stage']}｜{s['title']}（{s['count']} 个 / {s['size_mb']} MB）")
        out.append(s["why"])
        for f in s["files"]:
            out.append(f"  {f['name']}  [{f['size_mb']} MB]  {f['path']}")
        out.append("")
    return "\n".join(out)
