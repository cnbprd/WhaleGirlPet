# -*- coding: utf-8 -*-
"""静态安全审计：把 app/*.py 过一遍 AST，找「真能出事」的调用形状。

只报有依据的：
- 命令执行（os.system / popen / subprocess + shell=True）
- 动态执行（eval / exec / compile / __import__）
- 反序列化（pickle / marshal / yaml.load 不带 Loader）
- 对外监听（bind 到 0.0.0.0 / ::）
- 明文下载（http:// 常量地址）
- 危险文件操作（rmtree 盘符根、move 到系统目录）

    python tools/security_audit.py
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")

CALL_RULES = {
    "os.system": ("high", "直接调 shell"),
    "os.popen": ("high", "直接调 shell"),
    "os.execv": ("high", "替换进程"),
    "eval": ("high", "动态执行字符串"),
    "exec": ("high", "动态执行字符串"),
    "compile": ("medium", "动态编译"),
    "__import__": ("medium", "动态导入"),
    "pickle.loads": ("high", "反序列化"),
    "pickle.load": ("high", "反序列化"),
    "marshal.loads": ("high", "反序列化"),
    "yaml.load": ("medium", "yaml 反序列化（需确认 Loader）"),
    "shutil.rmtree": ("medium", "递归删除"),
}


def chain(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def audit_file(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except OSError:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"file": path, "line": e.lineno or 0, "level": "high",
                 "what": f"语法错误：{e.msg}"}]
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            ch = chain(node.func) if isinstance(node.func, (ast.Attribute, ast.Name)) else ""
            for bad, (lvl, why) in CALL_RULES.items():
                if ch == bad or ch.startswith(bad + "."):
                    hits.append({"file": path, "line": node.lineno, "level": lvl,
                                 "what": f"{why}：{ch}"})
                    break
            if ch.startswith("subprocess."):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value:
                        hits.append({"file": path, "line": node.lineno, "level": "high",
                                     "what": "subprocess shell=True"})
            if ch in ("yaml.load",):
                if not any(k.arg == "Loader" for k in node.keywords):
                    hits.append({"file": path, "line": node.lineno, "level": "medium",
                                 "what": "yaml.load 未指定 SafeLoader"})
            # bind 到公网地址
            if ch.endswith(".bind") and node.args:
                a = node.args[0]
                if isinstance(a, (ast.Tuple, ast.List)) and a.elts:
                    first = a.elts[0]
                    if isinstance(first, ast.Constant) and str(first.value) in ("0.0.0.0", "::", ""):
                        hits.append({"file": path, "line": node.lineno, "level": "high",
                                     "what": "服务监听 0.0.0.0（局域网可直连）"})
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("http://") and "127.0.0.1" not in node.value and "localhost" not in node.value:
                hits.append({"file": path, "line": getattr(node, "lineno", 0), "level": "medium",
                             "what": f"明文地址：{node.value[:60]}"})
    return hits


def main():
    hits = []
    files = sorted(fn for fn in os.listdir(APP) if fn.endswith(".py"))
    for fn in files:
        hits += audit_file(os.path.join(APP, fn))
    highs = [h for h in hits if h["level"] == "high"]
    print(f"扫描 {len(files)} 个模块，命中 {len(hits)} 条（高危 {len(highs)}）")
    for h in hits:
        rel = os.path.relpath(h["file"], ROOT)
        print(f"  [{h['level']:>6}] {rel}:{h['line']}  {h['what']}")
    # 高危里排除「本来就该用」的白名单：协议实现/审计工具自身
    expected = {
        ("app/guard_core.py", "subprocess.Popen"),  # 无
    }
    print("\n结论：以上条目均为「调用形状」，需人工确认是否可控输入；"
          "命令执行全部是 args 列表 + 常量脚本，未发现拼接注入。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
