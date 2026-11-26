# 3D 情绪总线 v3.2 第一步

日期：2026-11-26

## 当前状态

v3.2.x 的第一步已经接进 3D 壳：**本机 UDP 情绪参数总线**。它只负责把高阶情绪参数送进 3D 进程，不把 ASR / LLM / TTS 搬进渲染进程。

- 默认监听 `udp://127.0.0.1:47832`，只绑回环地址，不对局域网开放。
- 可用环境变量 `WHALE3D_EMOTION_PORT` 改端口。
- 数据报是 UTF-8 JSON，最小字段 `emotion`；`intensity`、`source` 可选。
- 3D 进程收到后映射到当前最小 VRM 的 `open / blink / smile` 三帧脸部图集，并把结果写进日志。
- `3d/tools/send_emotion.py` 是手工注入工具；`3d/tools/emotion_accept.py` 是带截图的黑盒验收。

## 协议

```json
{"emotion":"happy","intensity":0.8,"source":"manual"}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `emotion` | string | 必填；见下表的映射 |
| `intensity` | number | 0–1；缺省 1.0，越界会夹紧，非有限值回退 1.0 |
| `source` | string | 可选；`manual` / `user` / `llm` / `agent`，只用于日志和后续仲裁 |

当前图集只有三帧，映射是保守的过渡方案：

| `emotion` | 脸部结果 |
|---|---|
| `happy` / `joy` / `excited` / `smile` / `laugh` | `intensity >= 0.35` 时 `smile`，否则恢复自动眨眼 |
| `curious` / `thinking` / `interested` | 同上（暂时借用 `smile`） |
| `neutral` / `calm` / `idle` | `auto`，恢复自动眨眼 |
| `sad` / `angry` / `tired` / `sleepy` / `bored` | `open` |
| 其他 | 忽略并写日志，不改变当前状态 |

## 手工验收

先启动 `3d\whale3d.exe`，再在仓库根目录执行：

```powershell
.venv\Scripts\python.exe 3d\tools\send_emotion.py happy 0.8
.venv\Scripts\python.exe 3d\tools\send_emotion.py neutral 0
```

3D 日志应出现：

```text
Emotion bus: udp://127.0.0.1:47832
Emotion: happy intensity=0.80 source=manual face=smile
```

自动截图验收：

```powershell
.venv\Scripts\python.exe 3d\tools\emotion_accept.py
```

本次实测结果：

- 进程日志：`Emotion: happy intensity=0.80 source=acceptance face=smile`
- 帧率：约 27.8–28.8 fps，`update_us` 约 10 µs；和 v3.1.0 同量级。
- 截图：`docs/_3d_emotion_neutral.png`、`docs/_3d_emotion_happy.png`、`docs/_3d_emotion_compare.png`
- `open` 与 `happy` 全窗口 RGB 平均差 **0.674**（0–255 尺度）；差异集中在眼部/嘴部，属于图集帧切换，不是窗口位移。

## 还没做的

这一步只解决“参数进得来、脸能切”。以下仍属于 v3.2.x 后续：

1. **平滑过渡**：当前是三帧图集硬切，还没有两帧交叉淡化；下一版在 shader 里混两帧，再给 `intensity` 做时间缓动。
2. **姿态/视线**：`body_lean`、`gaze_target` 还没有接进骨骼后处理；当前模型没有对应 BlendShape。
3. **LLM/ASR/TTS 闭环**：Python 侧还没有把对话情绪标签发到 UDP；这条总线目前只被手工工具和验收脚本使用。
4. **权限/仲裁**：`source` 只记录，还没有 `P_USER` / `P_LLM` / `P_AUTO` 优先级和打扰预算。

## 体积与安全

- 新增 `emotion_bus.cpp` 后，`whale3d.exe` 从 1,315,840 B 增至 **1,320,448 B**（+4,608 B）。
- 仅链接系统 `ws2_32.dll`，没有引入新运行时 DLL。
- 只绑 `127.0.0.1`，不监听 `0.0.0.0`；没有认证，本机任意进程都能注入，这也是当前开发阶段的预期边界。
- 当前改动是开发态，**没有重新打 v3.1.0 的 ZIP / 安装包**；Release 里的 3.1.0 仍是旧 exe。
