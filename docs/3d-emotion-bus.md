# 3D 情绪总线 v3.2（step 1 + step 1b + step 2 + step 3 + step 4）

日期：2026-11-26（step 1–3）/ 2026-11-27（step 4）

## 当前状态

v3.2.x 的第一步已经接进 3D 壳：**本机 UDP 情绪参数总线**。它只负责把高阶情绪参数送进 3D 进程，不把 ASR / LLM / TTS 搬进渲染进程。

- 默认监听 `udp://127.0.0.1:47832`，只绑回环地址，不对局域网开放。
- 可用环境变量 `WHALE3D_EMOTION_PORT` 改端口。
- 数据报是 UTF-8 JSON，最小字段 `emotion`；`intensity`、`source` 可选。
- 3D 进程收到后映射到当前最小 VRM 的 `open / blink / smile` 三帧脸部图集，并把结果写进日志。
- v3.2 step 1b：情绪触发的换脸现在走 **0.16 s 两帧交叉淡化**（shader 内 `mix` 两张图集采样），不再硬切；`blink` 仍保持瞬时闭眼。
- v3.2 step 4：`intensity` 现在是 **neutral→smile 的混合幅度**；`curve.attack_ms` / `curve.release_ms` 控制 0→目标、目标→0 的线性包络，缺省 180 / 420 ms，夹在 40–2000 ms。0.8 强度不再等于“全笑脸”，进/出也不再单帧跳变。
- `3d/tools/send_emotion.py` 是手工注入工具，支持 `--attack-ms` / `--release-ms`；`3d/tools/emotion_accept.py` 是带截图的黑盒验收，并额外抓 60 ms / 释放阶段画面。

## v3.2 step 2：Python 侧标签与 P_USER / P_LLM / P_AUTO 仲裁

这一段把“手工注入”推进到“聊天时自动发情绪”。渲染进程仍然只收 UDP，不引入 Python 进程或模型运行时。

- `app/emotion_bridge.py` 负责产生信号、按优先级仲裁，并只在当前有效信号变化时发一个 UDP 包。
- 优先级：`P_USER(3) > P_LLM(2) > P_AUTO(1)`。高优先级信号未过期时，低优先级包不会覆盖当前表情。
- `P_USER`：显式说法，例如“笑一个”“别难过”“冷静点”；TTL 8 秒，强度 0.75–0.90。
- `P_LLM`：优先读模型回复里的隐藏标签 `[[emo:happy:0.7]]`；模型没给标签时，从回复文本做保守词表兜底；TTL 4 秒。
- `P_AUTO`：沿用 `EmotionState.expression_hint()` 和 `mood_score()`；TTL 12 秒，强度 0.15–0.85。
- `main.py` 在用户发话时提交 `P_USER`，在 `_finish_reply()` 提交 `P_LLM`，在 5 分钟情绪衰减定时器里提交 `P_AUTO`。
- 系统提示只在 3D bridge 开启时要求模型在末尾附一个隐藏标签；`_polish_reply()` 会在气泡/TTS 前移除标签，用户看不到。

实测：`tools/test_emotion_bridge.py` 6 项单元测试通过；启动 3.1.1 的 `whale3d.exe` 后，`P_USER` 日志为 `Emotion: happy intensity=0.90 source=P_USER face=smile`，`P_LLM` 日志为 `Emotion: sad intensity=0.65 source=P_LLM face=open`。这两条只是本机回环验收，不代表真实 LLM 每次都会输出标签。

## v3.2 step 3：TTS 播放期间保持回复情绪

`P_LLM` 原本只有 4 秒 TTL，长句还没念完脸就掉回 `P_AUTO`。这一步把“真实播放”接进桥，而不是按文本长度猜：

- `AudioManager` 新增 `speechStarted` / `speechFinished` 信号，只在 TTS 的 `speech=True` 播放路径触发；动作音效、试听、普通音频不走这两个信号。
- `main.py` 把两个信号接到 `EmotionBridge.tts_active(True/False)`。
- 开始播放时，把最近一条 `P_LLM` 信号延长到 30 秒；播放结束/被打断时，恢复为 4 秒 TTL，之后照常衰减到 `P_AUTO`。
- 这不是新的优先级：`P_USER` 仍然压过 `P_LLM`；只是让回复情绪覆盖整段语音。

实测：`tools/test_emotion_bridge.py` 当时 7/7 通过（step 4 后 8/8），包含 `P_LLM` 5 秒过期后由 `tts_active(True)` 重新拉起、20 秒仍保持、结束后 5 秒释放的用例；`py_compile` 通过。音频层先用 0.5 秒 WAV 走了一遍 `speech=True`：`play_file=True started=1 finished=1`。之后用 **真实 Edge TTS 11.544 秒 MP3** 跑完整链路：音频 `speechStarted/Finished` 各 1 次，播放中段 `P_LLM` 仍为 `ttl=30.0`，结束后 4 秒由 `main._release_tts_emotion()` 补一条 `P_AUTO`；3D 日志出现两次 `Emotion: happy intensity=0.90 source=P_LLM face=smile`（初始 + 播放拉起），中段截图 `docs/_3d_tts_sync_app_mid.png`。

## v3.2 step 4：intensity 包络

这一步只加“幅度 + 时间”两件事，不换表情资源，也不碰 gaze/ASR。

- 协议新增可选 `curve: {attack_ms, release_ms}`；缺省 180 / 420 ms，服务端夹在 40–2000 ms。
- `Model::Impl` 新增 `emotionCurrent`（渲染实际使用的强度）；目标继续存在 `emotionIntensity`；`applyEmotion()` 只设目标，`updateEmotion()` 按 `dt / duration` 线性推进，不按帧数硬编码。
- positive 情绪把 neutral 图集帧 0 与 smile 图集帧 2 按 `emotionCurrent` 混合；neutral/negative 把目标设 0，按 release 回落。强度 0.8 现在是“80% 的笑”，不是“全笑”。
- 自动眨眼优先：`draw()` 在 `faceA/faceB == 1` 时不套 emotion 混合，眨完继续用当前强度。
- `WHALE3D_EMOTION_TRACE=1` 时每约 10 ms 写一行 `EmotionTrace t=… current=… target=… active=…`；它只用于验收，不参与渲染。

本轮真实窗口验收（`3d/tools/emotion_accept.py`，27.2 fps，`WHALE3D_FREEZE=1`）：

- 0→0.8：trace 反推起点约 **182 ms**（设定 180 ms）；首个可见样本 `current=0.1889`，满值样本 `current=0.8000`。
- 0.8→0：trace 反推起点约 **353 ms**（满程 420 ms 的 80% 应为 336 ms，差值来自 34 ms 采样间隔）。
- 截图全窗 RGB 平均差：neutral→60 ms **0.117**，60 ms→happy **0.414**，neutral→happy **0.521**；60 ms 帧确实在两端之间。
- 日志：`Emotion: happy intensity=0.80 attack=180ms release=420ms source=acceptance face=smile`；`Emotion: neutral intensity=0.00 attack=180ms release=420ms source=acceptance face=smile`（后者处于释放中，`faceName` 仍报 smile 是预期）。

## 协议

```json
{"emotion":"happy","intensity":0.8,"source":"manual","curve":{"attack_ms":180,"release_ms":420}}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `emotion` | string | 必填；见下表的映射 |
| `intensity` | number | 0–1；缺省 1.0，越界会夹紧，非有限值回退 1.0；positive 时是 smile 混合幅度 |
| `source` | string | 可选；`manual` / `user` / `llm` / `agent`，只用于日志和后续仲裁 |
| `curve.attack_ms` | number | 可选；0→目标强度的时长，缺省 180 ms，夹在 40–2000 ms |
| `curve.release_ms` | number | 可选；目标→0 的时长，缺省 420 ms，夹在 40–2000 ms |

当前图集只有三帧；step 4 后映射是：

| `emotion` | 脸部结果 |
|---|---|
| `happy` / `joy` / `excited` / `smile` / `laugh` | 按 `intensity` 从 neutral 混到 smile（0 = neutral，1 = 全 smile）；`intensity=0` 不激活覆盖 |
| `curious` / `thinking` / `interested` | 同上（暂时借用 smile） |
| `neutral` / `calm` / `idle` | 目标 0，按 `release_ms` 从当前强度回到中性 |
| `sad` / `angry` / `tired` / `sleepy` / `bored` | 目标 0，按 `release_ms` 回落；当前不额外加 negative 表情帧 |
| 其他 | 忽略并写日志，不改变当前状态 |

`hold_ms` 仍未实现：当前“保持”由 Python 侧 `P_USER/P_LLM/P_AUTO` 的 TTL 和 TTS 播放期延长负责，渲染侧不需要再叠一层固定 hold。

## 手工验收

先启动 `3d\whale3d.exe`，再在仓库根目录执行：

```powershell
.venv\Scripts\python.exe 3d\tools\send_emotion.py happy 0.8 --attack-ms 180 --release-ms 420
.venv\Scripts\python.exe 3d\tools\send_emotion.py neutral 0
```

3D 日志应出现：

```text
Emotion bus: udp://127.0.0.1:47832
Emotion: happy intensity=0.80 attack=180ms release=420ms source=manual face=smile
```

自动截图验收：

```powershell
.venv\Scripts\python.exe 3d\tools\emotion_accept.py
```

本次实测结果（2026-11-27，dev build）：

- 进程日志：`Emotion: happy intensity=0.80 attack=180ms release=420ms source=acceptance face=smile`；释放日志 `Emotion: neutral intensity=0.00 ... face=smile` 表示仍在释放，不代表卡住。
- 帧率：`fps=27.2`，`update_us=7.33`，与 step 1b 的 27.2 fps / 7.23 µs 基本持平。
- 截图：`docs/_3d_emotion_neutral.png`、`docs/_3d_emotion_crossfade.png`、`docs/_3d_emotion_happy.png`、`docs/_3d_emotion_release.png`、`docs/_3d_emotion_after.png`。
- 包络：trace 显示 0→0.8 约 **182 ms**（设定 180 ms）；0.8→0 约 **353 ms**（按 420 ms 满程的 80% 应为 336 ms，34 ms 采样间隔带来差值）。
- 交叉淡化实测：`neutral -> 60 ms` 全窗 RGB 平均差 **0.117**，`60 ms -> happy` **0.414**，`neutral -> happy` **0.521**（0–255 尺度）；中间帧明显处在两端之间，说明不是硬切。

## 交叉淡化实现

- `Model::Impl` 增加 `faceFrameB`、`faceMix`、`faceTransition`；`setFace("open"/"smile"/"auto")` 与 `toggleSmile()` 调 `startFaceTransition()`。
- `updateFace()` 在过渡期间按 `dt / 0.16 s` 递增 `faceMix`，完成后把 B 帧写回 A；自动眨眼仍走瞬时帧。
- shader 增加 `uFaceFrameB` 与 `uFaceMix`；脸部 UV 同时采 A/B 两帧后 `mix`，身体 UV 不变。
- GL 函数加载表新增 `glUniform1f`；`draw()` 在无过渡时让 B=A、mix=1，避免采样到旧目标帧。

## 强度包络实现

- `emotion_bus.h/.cpp` 的 `Frame` 增加 `attackMs/releaseMs`，解析 `curve.attack_ms` / `curve.release_ms`；缺省 180 / 420 ms，夹在 40–2000 ms。
- `model.h/.cpp` 的 `applyEmotion()` 只写目标强度；`updateEmotion()` 用 `dt / duration` 线性逼近，到 0 时清 `emotionActive`。
- `draw()` 在 smile 覆盖有效且不是眨眼帧时，令 `uFaceFrame=0`、`uFaceFrameB=2`、`uFaceMix=emotionCurrent`；这样强度 0.8 就是 80% 的笑，而不是二值切换。
- `WHALE3D_EMOTION_TRACE=1` 输出 `EmotionTrace`，是开发验收开关，默认关闭。

## 还没做的

step 1 / 1b / 4 已解决“参数进得来、脸能平滑切、强度有幅度和时间曲线”。以下仍属于 v3.2.x 后续：

1. **姿态/视线**：`body_lean`、`gaze_target` 还没有接进骨骼后处理；当前模型没有对应 BlendShape。
2. **ASR/TTS 闭环**：语音输入和语音输出还没有把情绪标签送进这条总线；当前自动信号只覆盖文本聊天和 `EmotionState`。
3. **标签可靠性**：`P_LLM` 的隐藏标签依赖模型遵循提示；小模型可能不输出，当前用回复词表兜底。跨云端/本地/Ollama 三后端的实际命中率还没有统计。
4. **仲裁边界**：当前是固定优先级 + TTL，不是“打扰预算”；用户连续说话时不会主动降频，后续可按会话强度再加节流。

## 体积与安全

- 新增 `emotion_bus.cpp` 后，`whale3d.exe` 从 1,315,840 B 增至 **1,321,472 B**（+5,632 B；其中 1,024 B 是版本资源）。
- 交叉淡化（step 1b）后 dev exe 为 **1,322,496 B**，SHA256 `5139593C63050D63572B4663763290274422975176923204B26D285C0C1EF769`。
- 强度包络（step 4，含可选 trace）后当前 dev exe 为 **1,324,544 B**，SHA256 `5D909D8B2F82BB65AF8966F623C0BFEFA18E86DF07D5F300D8E828DE24345119`；相对 step 1b 增加 2,048 B。
- 仅链接系统 `ws2_32.dll`，没有引入新运行时 DLL。
- 只绑 `127.0.0.1`，不监听 `0.0.0.0`；没有认证，本机任意进程都能注入，这也是当前开发阶段的预期边界。
- 当前 3.2 开发态没有重打 3.2 的 ZIP / 安装包；v3.1.2 是最新安装版（`WhaleGirlPet-Setup-3.1.2.exe`）。
