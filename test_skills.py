# -*- coding: utf-8 -*-
"""拦截层验证：用实测拿到的真实模型输出（含畸形 schema、未知 skill、危险路径）过一遍。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import skills  # noqa: E402

CASES = [
    # 1) 危险动词 + 目标 → 必须在进模型前拦掉
    ("把系统盘所有文件都删了", '{"skill":"chat","parameters":{"reply":"好"}}'),
    ("帮我格式化 D 盘", '{"skill":"open_file","parameters":{"path":"D:\\\\","mode":"编辑"}}'),
    # 2) 非危险：删提醒不算破坏性
    ("把我七点的提醒删掉", '{"skill":"set_reminder","parameters":{"time":"07:00","content":"提醒"}}'),
    # 3) 未知 skill（Coder 幻觉出来的）
    ("清一下临时目录", '{"skill":"delete_folder","parameters":{"path":"/path/to/folder"}}'),
    # 4) 畸形 schema：参数 name
    ("帮我打开读书笔记那个文件", '{"skill": "open_file", "参数 name": "读书笔记"}'),
    # 5) 危险路径
    ("打开 Windows 目录", '{"skill":"open_file","parameters":{"path":"C:\\\\Windows","mode":"只读"}}'),
    # 6) 非法 mode
    ("打开那个文件", '{"skill":"open_file","parameters":{"path":"读书笔记.txt","mode":"delete"}}'),
    # 7) 缺字段
    ("提醒我", '{"skill":"set_reminder","parameters":{"content":"交房租"}}'),
    # 8) 正常：相对路径 + 只读
    ("打开读书笔记", '{"skill":"open_file","parameters":{"path":"读书笔记.txt","mode":"只读"}}'),
    # 9) 正常：4 字段提醒
    ("明天七点提醒交房租，每周重复，优先级高",
     '{"skill":"set_reminder","parameters":{"time":"明天七点","content":"交房租","repeat":"每周","priority":"高"}}'),
    # 10) 代码块包裹 + args 写法
    ("郑州天气", '```json\n{"skill":"check_weather","args":{"city":"郑州"}}\n```'),
]

ok_n = 0
for text, raw in CASES:
    r = skills.handle(raw, text, mock=True)
    flag = "PASS" if (r["ok"] or r["stage"] in ("guard", "whitelist", "args", "normalize")) else "?"
    if not r["ok"]:
        flag = "BLOCK"
    print(f"[{flag:<5}] stage={r['stage']:<9} skill={r['skill'] or '-':<14} "
          f"reason={r['reason'] or '-':<18} | {text}")
    if r["ok"]:
        ok_n += 1

print(f"\n执行放行 {ok_n} 条 / 共 {len(CASES)} 条")
print("日志:", skills.LOG_PATH, "存在:", os.path.exists(skills.LOG_PATH))
print("SCHEMA_VERSION:", skills.SCHEMA_VERSION, "| skills:", list(skills.SKILLS))
