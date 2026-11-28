# 3D 引擎分阶段计划（2026-11-28）

状态：**执行中；阶段 0 已按 waiver 关闭，阶段 1 已按 GPU CI runner waiver 条件退出，阶段 2 已按 3D 引擎范围条件退出（聊天项不属 3D core，#70 仍独立待办），阶段 3 已按“资产校验/清单/打包/运行时校验”条件退出，阶段 4 已按“pass 边界 + inspector + golden”条件退出，阶段 5 已按“内容包安装/升级/卸载 + 签名 waiver + 后端 no-go”收口；#70 已覆盖点击/拖拽/动作，聊天待定；idle CPU A/B +1.75pp 已判定可接受。**
基线版本：`v3.2.0-sprite` 已公开发布，tag `v3.2.0-sprite` → `a2ef92c`。
原则：学 UE 的**工业化方法**，不学 UE 的**功能体量**；每阶段有独立分支、证据和退出条件，不并行重构。

## 0. 当前基线

- 引擎：手写 OpenGL 3.3 + SDL3 + ozz；单模型 2,076 三角形，窗口 420×620，28–29 FPS，private 约 98MB，单核 CPU 31–36%（来源：`3d/README.md` 本机测量表）。
- 结构：`Model` 同时管 GLB/VRM 解析、GL 资源、ozz 采样、表情、gaze/lean、spring；`main.cpp` 管窗口、overlay、托盘、输入；`EmotionBus::poll` 只返回本次 poll 的最后一帧。
- 发布：`v3.2.0-sprite` 已公开，4 个资产已上传并下载核对；安装器和 exe 仍为 `NotSigned`。
- 未闭环：2D PyInstaller 冻结包、SignPath 审核、普通桌面 z 序点击复核。

## 1. 阶段总览

| 阶段 | 主题 | 优先级 | 估算 | 核心产出 |
|---|---|---|---|---|
| 0 | 发布收尾与基线冻结 | P0 | 0.5–1 天 | `docs/engine-baseline-3.2.0-sprite.md`；遗留项 pass/waiver |
| 1 | 可观测性与无头回归 | P0 | 3–5 天 | `FrameStats`、JSONL trace、`--headless`、CI smoke |
| 2 | 动画状态机与手感 | P0 | 5–8 天 | `AnimationController`、固定 tick、卡面队列、17 卡回归 |
| 3 | 资产管线与烘焙 | P1 | 3–5 天 | `cook_assets`、`content.json`、坏资产夹具 |
| 4 | 渲染 pass 边界与 inspector | P1 | 5–8 天 | `IRenderer`、pass 计时、`--inspect`、golden 截图 |
| 5 | 内容包/签名/可选后端 | P2 | 按需 | `content` 包、签名决策、后端评估 |

估算为单人工作量，不承诺日期；每阶段结束必须过退出条件，才进入下一阶段。

## 2. 阶段详情

### 阶段 0：发布收尾与基线冻结

**目标**：把 `v3.2.0-sprite` 的遗留项变成明确的 pass 或 waiver，避免后续引擎改动背着未决问题跑。

工作项：

1. 记录已发布基线：tag、commit、4 个资产大小/SHA256、Release URL、CI run。
2. 2D PyInstaller 冻结包：构建一次，启动并确认能读到 `assets/2d_bridge` 的 17 卡；若本版不支持，写明确 waiver，不把“没验”留成隐形债。
3. SignPath：只查审核状态；批准则走签名流程，签名后重新构建/重新上传资产，不能只替换 exe；未批准则记录 `NotSigned` waiver，不买付费 OV。
4. 普通桌面 z 序：用 Notepad/Chrome/Explorer 等真实目标复核卡面点击转发；区分“受控 z 序通过”和“普通桌面通过”。
5. 写 `docs/engine-baseline-3.2.0-sprite.md`，冻结引擎基线指标和已知限制。

退出条件：

- 2D 冻结包：pass 或 waiver。
- 签名：signed 或 waiver。
- z 序：pass 或 waiver。
- 基线文档已提交；没有未记录的 P0 遗留。

**关闭记录（2026-11-28）**：2D UI 发包、第三方 z 序、SignPath 三项以条件 waiver 转入阶段 2/阶段 5；详见 `docs/engine-baseline-3.2.0-sprite.md` 第 6 节。阶段 0 关闭，阶段 1 开始。

不做：不在这阶段改引擎代码。

### 阶段 1：可观测性与无头回归

**目标**：先让引擎“看得见”，再谈优化。对应 UE 的 Insights / Automation 思路，不是做完整编辑器。

工作项：

1. 新增 `3d/perf_stats.h/.cpp`：帧时间环形缓冲、FPS、RSS、hitch 计数、资产加载耗时、当前 clip/card/emotion/state。
2. 新增 pass 计时：model、sprite overlay、UI、hit mask；CPU 计时必做，GL timer query 可选。
3. 新增 `WHALE3D_STAT=1` 周期摘要和 `WHALE3D_TRACE=<path>` JSONL 逐帧/逐事件 trace。
4. 新增 `--headless --fixed-dt=1/60 --frames=N`：隐藏窗口 + FBO 渲染，跑资产加载、17 卡解析、动画推进和退出。
5. 新增 `3d/tools/test_headless_smoke.py`：60 帧 smoke、trace schema 校验、exit 0。
6. 修掉 `initLog()` 每次覆盖日志的问题；日志按启动时间分文件或追加 session 头。

退出条件：

- 60 帧 headless smoke 通过；600 帧无崩溃。
- trace 覆盖所有 pass 和状态切换；能定位单帧 hitch。
- 基线 10 分钟跑完，p50/p95/p99、RSS、CPU 有记录；相对 `v3.2.0-sprite` 无 P0 退步。

**退出记录（2026-11-28）**：CPU 10 分钟两轮实测完成（单核 29.61% / 26.30%，见 `docs/stage1-cpu-10min.md`）；60/600 帧本机 GPU render、CI no-GL smoke、10 分钟帧时间基线均通过。唯一未闭合项是“CI 无 Windows GPU runner 跑真实 render”，按条件 waiver 转入阶段 4/基础设施。**阶段 1 条件退出，阶段 2 开始。**

### 阶段 2：动画状态机与手感

**目标**：把当前“谁后调用谁赢”的 `setClip` / `applyEmotion` / `applyGazeLean` / `showCard` 收成一个状态机。对应 UE 的 AnimBP / State Machine / Blend Space / Sync Marker，但不做节点编辑器。

工作项：

1. 新增 `AnimationController`：JSON 状态表，状态含 idle、walk、sleep、action、emotion overlay；支持优先级、打断、crossfade、进入/退出事件。
2. 固定 tick：动画/spring 用 accumulator，渲染帧做插值；spring 每帧最多 4 个 substep，避免长帧炸开。
3. 卡面队列：`CardRequest` 带 priority、TTL、来源；替代当前单卡覆盖，解决高优先级动作被低优先级卡顶掉。
4. `EmotionBus` 改为有序队列/序号 + latest-wins 语义；保留最后一帧的同时不丢同批高优先级包。
5. 分层合成：base clip、face、gaze/lean、spring、card 各自权重；冲突时按优先级和 mask 解决。
6. 旧计划 #70 的“真实窗口手感验收”并入本阶段：点击、拖拽、动作、聊天触发都走真实窗口，不只是测试 target。

退出条件：

- 17 卡全部可见；动作/表情/gaze/spring 无互相覆盖的回归。
- 10 分钟浸泡通过；帧时间不高于阶段 1 基线；无新增 crash。
- 状态切换 trace 可读；真实窗口手感验收记录完成。
- 产出 `docs/anim-state-machine.md`。

**第一轮集成（2026-11-28）**：`3d/animation_controller.h` + `3d/anim_state_table.h` + 20 条夹具 + `main.cpp` base/action 门禁已落地；集成 CI run `46128539544` success，17 卡可见验收通过（`build/stage2-cards/2d-card-visible-qa.json`）；10 分钟浸泡 FPS avg 27.78 / p50 34.92ms / p99 47.02ms，无 crash、RSS 无增长。

**第二轮队列（2026-11-28）**：`3d/card_queue.h` 35 条夹具 + `EmotionBus::pollAll` 接入；同批 2 帧、动作期间 queued、动作结束补显、多张 FIFO（curious→pat）均通过；17 卡 17/17；队列压力浸泡 60/60 补显、0 丢弃、CPU 26.35%、无 crash；真实点击穿透 + 拖拽通过。idle 10 分钟 FPS 27.95 / p50 34.62ms / p99 48.36ms；同机 A/B stage1-stats 31.52% vs queue 33.27%，CPU +1.75pp，swap 7.05 vs 0.11ms，帧时间不直接比优劣。idle↔walk 真采样 crossfade 已落地（180ms，双采样 Lerp/NLerp）；同构建 17 卡、队列 6/6、点击、拖拽、90 秒 147 次 fade、10 分钟 298 次 fade 均无退出；action/expression 仍无独立 clip。

**收口记录（2026-11-28）**：阶段 2 按 3D 引擎范围条件退出，详见 `docs/stage2-closeout.md`。已过：状态机 20/20、队列 35/35、17 卡、真实点击/拖拽、crossfade、10 分钟浸泡、A/B CPU +1.75pp。未过：3D 壳无聊天入口，#70 聊天项保留为独立待办；卡面 overlay 仍硬切；p99 不能宣称正式等同阶段 1。阶段 3 只做资产校验/清单/打包，不动渲染层。

### 阶段 3：资产管线与烘焙

**目标**：借 UE 的 cooked assets / DDC / Asset Registry 思路，先做“验证 + 清单 + 可重复打包”，不急着自定义二进制格式。

工作项：

1. 新增 `3d/tools/cook_assets.py`：校验 GLB/VRM 的 19 根骨骼、4 条 spring 链、mesh/accessor、材质、动画；校验 atlas 1024×512、slot 160、17 卡 rect 和 UV 方向。
2. 输出 `content.json`：schema 版本、源文件 hash、cooked hash、资产列表、17 卡清单；运行时启动时校验。
3. 生成 `build/content` 验证副本；ZIP/安装器 payload 携带同一份 `content.json`，运行时启动校验；`verify_release_assets.py` 可选校验。
4. 增加坏资产夹具：坏 bone 索引、坏 accessor、坏 atlas 尺寸、坏 manifest、重复卡 id，全部在 cook 阶段拒绝。
5. 只有实测加载时间/内存明显受益时，才做自定义 `content.bin`；否则保留 GLB/VRM 运行时解析。

退出条件：

- cook 对同一输入输出稳定 hash；坏资产夹具全部失败。
- 发布包与安装器使用 content 清单；现有 17 卡和模型加载无回归。
- 产出 `docs/asset-cook.md`、`docs/asset-cook-report.json`。

**收口记录（2026-11-28）**：阶段 3 按“资产校验 + 清单 + 可重复打包 + 运行时校验”条件退出。cook 正向 hash 稳定、8 类坏输入拒绝、`verify_content.py` 通过；`package_content.py`/`verify_package_content.py` 接进 CI ZIP，`46139915847` 包内 3 文件 hash/17 卡通过；`content_manifest.cpp` 在启动时校验 package content，篡改 model 或错误 hash 退出 1，缺失 manifest 走 legacy；从该 ZIP 编译安装器，静默安装、安装目录 content 校验、`verified package hashes`、17/17 卡、卸载均通过。边界：安装器自身不预检 content，运行时只校验 package 的 3 个文件；已发布资产未替换。详见 `docs/stage3-closeout.md`。

### 阶段 4：渲染 pass 边界与 inspector

**目标**：把 GL 调用从 `model.cpp` / `main.cpp` 的隐式顺序，收成显式 pass 和资源生命周期。对应 UE 的 RHI / RDG 缩小版，不做多后端。

工作项：

1. 新增 `IRenderer` 接口 + `GLRenderer`；先保留 `NullRenderer` 供 headless/CI。
2. 显式 pass：model → sprite overlay → UI → hit mask；每 pass 有 begin/end、输入输出和计时。
3. 逐步迁移 `Model::draw`、`SpriteLayer::draw`、`ShellUi` 绘制；不一次性重写 `model.cpp`。
4. 新增 `--inspect` 调试浮层：当前 state/clip/card/emotion、pass ms、FPS、RSS、资产路径。
5. 增加 golden 截图/区域对比，覆盖主窗、卡面、透明角、点击区。

退出条件：

- 每 pass 时间可见；headless 仍通过。
- 主窗/卡面/点击区截图无回归；FPS 不低于阶段 1 基线。
- 产出 `docs/renderer-passes.md`。

**收口记录（2026-11-28）**：阶段 4 按“pass 边界 + inspector + golden”条件退出。`renderer.h` 提供 `IRenderer/GLRenderer/NullRenderer`，主循环显式包围 `model -> hitmask -> sprite -> region`，fps 日志输出各 pass 平均耗时；`--inspect` 侧栏显示 state/clip/card/emotion/pass/FPS/RSS/资产路径；`--duration=N` 支持有界可见测试。240 秒可见运行 231 个采样、平均 FPS 27.98（阶段 1 基线 21.79），17/17 卡 rect 与阶段 2 完全一致、golden 检查 `ok=true`，真实点击 `card=-1/model=1/received=true`，拖拽 `ok=true`，headless 60 帧与 package content 校验退出 0。边界：`GLRenderer` 不管理 GL 资源生命周期；实际顺序为 `model -> hitmask -> sprite -> region`，hit mask 必须在 sprite 之前；`ShellUi` 仍是原生 Win32，没有 GL UI pass；inspector 是不透明调试侧栏；240 秒不是 10 分钟；生产 exe/Release 未替换。详见 `docs/renderer-passes.md`。

### 阶段 5：内容包、签名与可选后端

**目标**：只在有明确收益时继续，不为了“像 UE”而膨胀。

工作项：

1. 内容包：把验证后的 assets 打成带 hash 的 `content` 包，安装器/ZIP 只认清单；需要增量更新时再做 patch。
2. 签名：SignPath 批准后重新构建/签名/上传；未批准保持 waiver。
3. 后端：只有出现跨平台或 D3D12/Vulkan 明确需求时，才评估第二个 `IRenderer` 后端。
4. 旧计划 #71 开机动画：作为表现层 backlog，不阻塞引擎主线；若要接，放在阶段 2 之后单独做。

退出条件：

- 内容包安装/卸载/升级通过；资产 hash 与 Release 一致。
- 签名状态明确；后端决策有书面理由。

**收口记录（2026-11-28）**：阶段 5 按“内容包安装/升级/卸载 + 签名 waiver + 后端 no-go”收口。用阶段 3 安装器 `WhaleGirlPet-Setup-3.2.0-ci.exe`（4,812,568 B，`2950B884...`）安装旧候选后，再安装阶段 4 候选安装器 `WhaleGirlPet-Setup-3.3.0-stage4.exe`（4,814,785 B，`BA734D2E...`）；升级 exit 0，`whale3d.exe` 从 1,457,664 B 替换为 1,463,296 B / `E792667E...`，`verify_package_content.py` 返回 `ok=True errors=0 files=3`，headless 60 帧输出 `Content manifest: verified package hashes` 且 exit 0；卸载 exit 0；同一新安装器另做一次全新安装、headless 和卸载也 exit 0。阶段 4 包内 model/manifest/atlas 三个资产 hash 与公开 `v3.2.0-sprite` Release ZIP 内同路径文件完全一致。签名仍为 `NotSigned`：本机 0 张代码签名证书、无 `signtool.exe`，SignPath 外部审核状态未知，维持阶段 0 waiver。后端决策：当前无跨平台/D3D12/Vulkan 明确需求，保留 `IRenderer + NullRenderer`，不引入第二后端；#71 开机动画仍在 backlog。边界：安装器版本 `3.3.0` 而 exe 版本资源仍是 `3.2.0.0`，这是内部候选；未发公开 Release，安装器仍不预检 content，升级只测同 AppId 覆盖，不测降级；测试安装器已加 `AppId` 隔离，避免与真实安装共用卸载键。详见 `docs/stage5-closeout.md`。

## 3. 与之前计划的合并

| 旧计划项 | 并入阶段 | 处理方式 |
|---|---|---|
| `v3.2.0-sprite` 发布收尾 | 阶段 0 | 2D 冻结包、SignPath、普通 z 序逐项 pass/waiver |
| 旧任务 #70 真实手感验收 | 阶段 2 | 与状态机一起验，不单独做“手感补丁” |
| 旧任务 #71 开机动画 | 阶段 5 backlog | 不阻塞引擎主线；需要时单独开分支 |
| 旧任务 #72 素材管线/绑骨 | 阶段 3 | 只并资产验证/打包；美术分层和绑骨不混进引擎重构 |
| `EmotionBus` 只保留最后一包 | 阶段 2 | 有序队列 + latest-wins |
| `initLog()` 每次覆盖 | 阶段 1 | 分 session 日志 |
| 每帧 `glReadPixels` / 每 6 帧 region | 阶段 1 测量、阶段 4 优化 | 先量化，再决定是否改读回/region 策略 |
| 高 DPI `WM_NCHITTEST` 坐标 | 阶段 0 复核、阶段 4 修 | 真实桌面测试复现后再改 |
| `agentic-v3.3` 薄层 | 不并入 | 与 3D 引擎独立；只共享 trace 字段时再对接 |

## 4. 版本与发布策略

- 阶段 0、1 只出内部候选，不公开发 Release。
- 阶段 2 通过后，视稳定性决定 `v3.3.0-anim` 公开候选。
- 阶段 3 通过后，视资产收益决定 `v3.3.1-cook`。
- 阶段 4、5 不强制发版；每阶段只保留内部证据和回滚点。
- 每个阶段一个分支，例如 `feat/v3.3-observe`、`feat/v3.3-anim`、`feat/v3.3-cook`、`feat/v3.3-render`；合并前跑阶段门禁。

## 5. 风险与不做

- **不抄 UE 源码**：UE 源码受 EULA 约束；只做概念学习和 clean-room 实现，必要处先确认许可。
- **不做完整 RHI/RDG**：一个 OpenGL 后端 + NullRenderer 足够；多后端等真实需求。
- **不做节点图编辑器**：JSON 状态表优先；可视化 inspector 只读，不编辑。
- **不做 Nanite/Lumen/World Partition/完整 ECS/UObject/GC**：2,076 三角形、单角色、420×620，负收益。
- **不并行重构**：阶段 1 没完成前不做状态机；阶段 2 没稳定前不动渲染层。
- **体积/内存红线**：每阶段记录 exe 字节增量和 private bytes 增量；无感知回涨就停。

## 6. 下一步

阶段 0–5 已按各自条件/waiver 收口；主线不再扩大阶段。后续只在有明确发布需求时做发布候选：统一 bump exe 版本资源、替换生产 `3d/whale3d.exe`、重打签名/安装器/Release，并重跑阶段 4 golden 与安装升级。未拍板前保持内部候选，不替换生产 exe。
