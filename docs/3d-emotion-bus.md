# 3D 情绪总线 v3.2 第一步

日期：2026-11-26

## 当前状态

v3.2.x 的第一步已经接进 3D 壳：**本机 UDP 情绪参数总线**。它只负责把高阶情绪参数送进 3D 进程，不把 ASR / LLM / TTS 搬进渲染进程。

- 默认监听 `udp://127.0.0.1:47832`，只绑回环地址，不对局域网开放。
- 可用环境变量 `WHALE3D_EMOTION_PORT` 改端口。
- 数据报是 UTF-8 JSON，最小字段 `emotion`；`intensity`、`source` 可选。
- 3D 进程收到后映射到当前最小 VRM 的 `open / blink / smile` 三帧脸部图集，并把结果写进日志。
- v3.2 step 1b：情绪触发的换脸现在走 **0.16 s 两帧交叉淡化**（shader 内 `mix` 两张图集采样），不再硬切；`blink` 仍保持瞬时闭眼。
- `3d/tools/send_emotion.py` 是手工注入工具；`3d/tools/emotion_accept.py` 是带截图的黑盒验收，并额外抓 60 ms 中间帧。

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
- 帧率：step 1 约 27.8–28.8 fps，`update_us` 约 10 µs；step 1b 交叉淡化验收日志 `fps=27.2 update_us=7.23`，没有明显回退。
- 截图：`docs/_3d_emotion_neutral.png`、`docs/_3d_emotion_crossfade.png`、`docs/_3d_emotion_happy.png`、`docs/_3d_emotion_compare.png`（三栏依次为 neutral / 60 ms cross-fade / happy）。
- 交叉淡化实测：`neutral -> 60 ms` 全窗 RGB 平均差 **0.121**，`60 ms -> happy` **0.407**，`neutral -> happy` **0.516**（0–255 尺度）；中间帧明显处在两端之间，说明不是硬切。
- `open` 与 `happy` 最终态全窗口 RGB 平均差多次运行在 **0.626–0.674**（旧硬切版本）；差异集中在眼部/嘴部，属于图集帧切换，不是窗口位移。

## 交叉淡化实现

- `Model::Impl` 增加 `faceFrameB`、`faceMix`、`faceTransition`；`setFace("open"/"smile"/"auto")` 与 `toggleSmile()` 调 `startFaceTransition()`。
- `updateFace()` 在过渡期间按 `dt / 0.16 s` 递增 `faceMix`，完成后把 B 帧写回 A；自动眨眼仍走瞬时帧。
- shader 增加 `uFaceFrameB` 与 `uFaceMix`；脸部 UV 同时采 A/B 两帧后 `mix`，身体 UV 不变。
- GL 函数加载表新增 `glUniform1f`；`draw()` 在无过渡时让 B=A、mix=1，避免采样到旧目标帧。

## 还没做的

这一步只解决“参数进得来、脸能平滑切”。以下仍属于 v3.2.x 后续：

1. **强度缓动**：`intensity` 目前只决定选 `smile` 还是 `auto/open`，还没有把 0–1 映射成表情幅度或时间曲线。
2. **姿态/视线**：`body_lean`、`gaze_target` 还没有接进骨骼后处理；当前模型没有对应 BlendShape。
3. **LLM/ASR/TTS 闭环**：Python 侧还没有把对话情绪标签发到 UDP；这条总线目前只被手工工具和验收脚本使用。
4. **权限/仲裁**：`source` 只记录，还没有 `P_USER` / `P_LLM` / `P_AUTO` 优先级和打扰预算。

## 体积与安全

- 新增 `emotion_bus.cpp` 后，`whale3d.exe` 从 1,315,840 B 增至 **1,321,472 B**（+5,632 B；其中 1,024 B 是版本资源）。
- 交叉淡化（step 1b）后当前 dev exe 为 **1,322,496 B**，SHA256 `5139593C63050D63572B4663763290274422975176923204B26D285C0C1EF769`；相对 step 1 只增加 1,024 B，来自 shader uniform 与状态字段。
- 仅链接系统 `ws2_32.dll`，没有引入新运行时 DLL。
- 只绑 `127.0.0.1`，不监听 `0.0.0.0`；没有认证，本机任意进程都能注入，这也是当前开发阶段的预期边界。
- 当前改动是开发态，**没有重新打 v3.1.0 的 ZIP / 安装包**；Release 里的 3.1.0 仍是旧 exe。
