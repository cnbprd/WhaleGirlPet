# -*- coding: utf-8 -*-
"""「大肥鱼做小软件」：把一句需求变成可运行的 Python 小工具。

流程：需求 → 本地/云端模型写代码 → 抽代码块 → 静态风险检查 → 存到 数据目录/scripts
→ 用户点「运行」才真的执行（从不自动运行）。

安全边界（硬性的，不靠模型自觉）：
- 禁止 elevate / 改注册表 / 关机重启 / 格式化 / 删系统目录 / 反弹 shell 之类模式；
- 带风险模式的脚本直接判为不可运行，只留源码给用户自己看；
- 执行超时 20 秒，输出截断，跑完把结果贴回聊天。
"""
import os
import re
import shutil
import subprocess
import sys
import time

import paths

_CODE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)

DANGER_PATTERNS = [
    (r"\bshutil\.rmtree\s*\(\s*['\"]?[A-Za-z]:[\\/]", "删除整个盘符目录"),
    (r"\bos\.system\s*\(", "直接调 shell"),
    (r"\bsubprocess\.\w+\([^)]*shell\s*=\s*True", "shell=True 执行命令"),
    (r"rm\s+-rf\s+/", "递归删除根目录"),
    (r"format\s+[a-zA-Z]:", "格式化磁盘"),
    (r"reg\s+delete", "删注册表"),
    (r"shutdown\s+/", "关机/重启"),
    (r"winreg\.(DeleteKey|SetValue)", "改注册表"),
    (r"socket\.\w+\([^)]*\).*\bconnect\b", "主动联网连接"),
    (r"ctypes\.windll.*(ExitWindows|TerminateProcess)", "强制关系统/进程"),
]

PROMPT = (
    "你是一个给 Windows 写小工具的工程师。用户需求：{ask}\n"
    "要求：\n"
    "1) 只输出一个 Python 3 脚本，用 ```python 包住；不要解释、不要多余文字；\n"
    "2) 只用标准库，不要 pip 安装；不要联网、不要改注册表、不要删系统文件、不要关机；\n"
    "3) 有命令行参数时用 argparse，默认参数要能直接跑；\n"
    "4) 运行结束要打印清楚的结果（中文）；\n"
    "5) 代码里不要写死用户路径，用 os.path.expanduser。"
)


def extract_code(text: str) -> str:
    m = _CODE_RE.search(text or "")
    if m:
        return m.group(1).strip()
    # 没有围栏时，从第一个 import/def 开始兜底
    lines = (text or "").splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(("import ", "from ", "def ", "#!")):
            return "\n".join(lines[i:]).strip()
    return ""


def check_code(code: str) -> list:
    """返回命中的风险说明列表；空列表 = 可以运行。"""
    hits = []
    for pat, why in DANGER_PATTERNS:
        if re.search(pat, code, re.I):
            hits.append(why)
    if len(code) > 20000:
        hits.append("脚本过长（>20000 字符）")
    return hits


def scripts_dir() -> str:
    d = os.path.join(paths.data_dir(), "scripts")
    os.makedirs(d, exist_ok=True)
    return d


def save_script(code: str, ask: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5]+", "_", (ask or "tool"))[:24].strip("_") or "tool"
    path = os.path.join(scripts_dir(), f"{slug}_{stamp}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.rstrip() + "\n")
    return path


def _python_exe() -> str:
    """找一个能跑的 python：开发期用 .venv，装机后找系统 python。"""
    cand = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        ".venv", "Scripts", "python.exe")
    if os.path.exists(cand):
        return cand
    return shutil.which("python") or shutil.which("python3") or ""


def can_run() -> bool:
    return bool(_python_exe())


def run_script(path: str, args: str = "", timeout: int = 20) -> tuple:
    """执行脚本，返回 (ok, 输出)。只在用户点「运行」时调用。"""
    py = _python_exe()
    if not py:
        return False, "本机没找到 python 解释器，脚本已保存，你可以自己用 Python 跑。"
    cmd = [py, path] + (args.split() if args else [])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=os.path.dirname(path), creationflags=0x08000000)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        ok = p.returncode == 0
        return ok, (out.strip() or ("运行完成，没有输出。" if ok else f"退出码 {p.returncode}"))
    except subprocess.TimeoutExpired:
        return False, f"超过 {timeout} 秒还没跑完，已经掐掉了。"
    except Exception as e:  # noqa: BLE001
        return False, f"运行失败：{str(e)[:200]}"
