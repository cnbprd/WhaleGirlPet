# v3.3.x Agentic 薄层（设计 + 当前实现）

日期：2026-11-27  
状态：**骨架已落代码并有回归测试；尚未接进聊天主流程。**

## 用户约束（原话落地）

- 工具按需加载，不打包全套。
- 权限门和循环编排是自研薄层。
- 不引入 LangChain / AutoGen / CrewAI 之类重型 Agent 框架。

## 模块

| 文件 | 职责 |
|---|---|
| `app/agentic_runtime.py` | 工具元数据、懒加载注册表、权限门、有限步循环 |
| `app/agentic_tools.py` | 把现有只读能力（安全体检/知识卡/学习路线）注册成工具，**不提前 import 业务模块** |
| `tools/test_agentic_runtime.py` | 懒加载计数、读/写/危险三态、循环停止条件 |
| `tools/test_agentic_tools.py` | `describe()` 不加载业务模块，`call()` 才加载 |

## 懒加载

`ToolRegistry` 只存 `ToolSpec(name, loader, permission, description)`；`describe()` 只返回元数据，`load()` 第一次被调用时才执行 loader，之后缓存 handler。

实测：

```text
agentic_runtime_ok loads {'read': 1, 'write': 1, 'danger': 0} steps 2 stop max_steps
agentic_tools_ok 14 cards lazy_ok
```

第二项验证的是：`agentic_tools.build_registry()` 之后 `security_cards` 和 `secscan` 都不在 `sys.modules`，调用 `security_cards` 后才出现。说明不是“注册即全套加载”。

## 权限门

| 权限 | 默认行为 | 说明 |
|---|---|---|
| `read` | 放行 | 只读查询、状态读取 |
| `write` | 拒绝，返回 `needs_approval` | 必须 `approved=True` 或预先 `grant(name)` |
| `dangerous` | 一律拒绝 | 不注册、不放行；避免把高风险动作藏进工具表 |

权限门是**进程内门**，不是操作系统权限；它不能替代 UAC、文件 ACL 或签名校验。现有 `app/skills.py` 的 mock 白名单仍独立，未做替换。

## 循环编排

`AgentLoop(next_call, max_steps=6)`：

1. 调 `next_call(trace)` 拿下一步 `ToolCall`；
2. 没下一步 → `no_more_tools`；
3. 权限门拒绝 → `permission_denied`，立即停；
4. 工具异常 → `tool_error`，立即停；
5. 步数用尽 → `max_steps`。

只做“取下一步 → 过门 → 调用 → 记录”，不接管模型、提示词、记忆和 UI；换模型不需要改这个类。

## 未接的部分

- 聊天主流程还没有把模型输出解析成 `ToolCall`，也没有权限弹窗；当前只有模块和测试。
- 没有异步/流式/取消；循环是同步的，适合短工具调用，不适合长任务。
- 没有持久化 trace；只在内存里返回。
- 没有把 `guard_core` 的写操作注册进来；写操作要等 UI 审批链路做好再接。
- 不引入重型框架，也不把全部工具一次性塞进 prompt；后续只把 `describe()` 的精简清单给模型。

## 验收

```powershell
.\.venv\Scripts\python.exe -m py_compile app\agentic_runtime.py app\agentic_tools.py
.\.venv\Scripts\python.exe tools\test_agentic_runtime.py
.\.venv\Scripts\python.exe tools\test_agentic_tools.py
```

预期：`agentic_runtime_ok`、`agentic_tools_ok`，exit 0。
