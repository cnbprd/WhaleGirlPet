# 阶段 2：卡面队列与 EmotionBus 多帧

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：run `46130542797` success（20 条动画 + 35 条卡队列断言 + headless 60 no-render）。  
构建：`3d/whale3d-stage2-queue.exe`，1,416,192 B，
SHA256 `2C9AE17318840B7468F75D90901990DAC18B309E2C5B1B2D846BE7AC10AEB2CE`。  
性质：**测试构建，不替换生产 `3d/whale3d.exe`。**

## 1. 本轮改动

- 新增 `3d/card_queue.h`：纯队列，不依赖 SDL/GL；按 priority、seq 选下一条；低优先级在动作期间等待，动作结束再显示。
- 队列的 `displayTtlMs` 与 `maxWaitMs` 分开：表情卡可以等 3 秒动作结束后再显示完整 1.2 秒，不会因为动作比 TTL 长就永久丢掉。
- `3d/emotion_bus.h/.cpp` 新增 `pollAll(std::vector<Frame>&)`：一次 drain 本次 socket 队列里的全部有效帧；旧 `poll()` 保留，内部改为取最后一条。
- `main.cpp` 改为 `pollAll`，同批多帧都应用；卡面走 `handleEmotionCard`：
  - 当前 base 或请求优先级不低于当前状态：立即 request + show；
  - 低优先级：进 `CardQueue`，日志 `anim card queued`；
  - 每帧 `cardQueue.tick`，动作/表情结束后 `popReady`，再 request + show，日志 `Sprite card queued`。
- 同状态重复卡在队列内合并，刷新等待时间，不无限堆积。
- 状态表仍是 `3d/anim_state_table.h` 内置 19 态。

## 2. 测试

| 项 | 结果 |
|---|---|
| AnimationController 单测 | 20/20 PASS |
| CardQueue 单测 | 35/35 PASS；CI run `46130542797` success |
| 同批多帧 | 日志 `Emotion batch: 2 frames`，两张卡都显示 |
| 动作期间表情 | `anim card queued: card=expression/happy ... active=action_wave active_priority=40 queued=1` |
| 动作结束补显 | `Sprite card queued: expression/happy state=expression_happy ttl=1200ms active=expression_happy queued_left=0` |
| 补显后过期 | 约 1.2s 后回 `idle`；独立 `build/check_expiry.py` 复核 |
| 多张 FIFO | `action/dance` 期间连发 curious、pat：queued=1/2，动作结束先 curious、1.2s 后 pat；`build/stage2-queue-multi/queue-test.json` 6/6 |
| 17 卡可见 | 17/17 captured，`build/stage2-queue-cards/2d-card-visible-qa.json` |
| headless 60 render | exit 0；p50 1.14ms / p99 4.16ms / work 1.18ms |
| headless 600 render | exit 0；p50 0.90ms / p99 1.97ms / work 0.96ms |
| headless 60/600 no-render | exit 0 |

真实窗口 QA 脚本：`3d/tools/check_card_queue.py`；结果 `build/stage2-queue/queue-test.json`，截图 `queue_after_action.png`。  
日志：`build/stage2-queue/queue-test.log`。  
headless 证据：`build/headless-smoke/headless-*-queue-summary.json`。

## 3. 队列版 10 分钟压力浸泡

命令：`build/stage2-queue-soak.ps1`，正常窗口，`WHALE3D_KEEP_AWAKE=1`，600 秒；每 10 秒发一组 `action/wave`（2500ms）+ `expression/happy`（1200ms），共 60 组。日志 `build/stage2-queue-soak.log`，CSV `build/stage2-queue-soak.csv`。

| 指标 | 本轮 | 对照 |
|---|---:|---:|
| 队列产生 / 补显 / 丢弃 | 60 / 60 / 0 | 目标 60/60 |
| FPS avg | 21.58 | 阶段 1 Run B（keep-awake）21.40 |
| interval p50 avg | 46.04ms | Run B 45.96ms |
| p95 avg | 51.55ms | Run B 52.79ms |
| p99 avg | 54.40ms | Run B 61.35ms |
| hitch 总数 | 1691 | 阶段 1 Run A 190（条件不同） |
| CPU 单核 avg | 26.35%（24.32–29.53%） | 阶段 1 Run B 26.30% |
| RSS | 70.50–71.60MB | Run B 69.75–70.58MB |
| private | 113.0–114.3MB | Run B 112.7–114.1MB |

结论：60 次动作+排队表情全部补显，0 丢弃，无 crash，RSS/private 无持续增长；CPU 与阶段 1 keep-awake 基本持平。FPS 21.58 和 hitch 1691 是桌面合成/overlay 的 swap 限制（swap ≈ 11ms）在 50ms hitch 阈值下的结果，不能当作 GPU 帧时间回归；本轮没有做 idle 队列版基线，不能替代阶段 1 的 27.86 FPS 基线。

### 3.1 Idle 10 分钟基线

`build/stage2-queue-idle.ps1`，队列构建正常窗口，`WHALE3D_KEEP_AWAKE=1`，60 个 10 秒 CPU 采样，trace 1Hz。摘要 `build/stage2-queue-idle-summary.json`。

| 指标 | 队列 idle | 阶段 1 基线 | 差 |
|---|---:|---:|---:|
| FPS avg | 27.95 | 27.86 | +0.09 |
| interval p50 avg | 34.62ms | 34.78ms | -0.16ms |
| p95 avg | 39.33ms | 39.18ms | +0.15ms |
| p99 avg | 48.36ms | 45.18ms | +3.18ms |
| hitch 总数 | 153 | 190 | -37 |
| CPU 单核 avg（稳态 58） | 33.27% | 26.30% | +6.97pp |
| RSS 稳态 | 71.02–73.44MB | 69.75–70.58MB | +1.3–2.9MB |
| private | 112.7–113.6MB | 112.7–114.1MB | 持平 |

结论：平均 FPS、p50、hitch 与阶段 1 基线基本一致；**p99 高 3.18ms（+7%），CPU 高 6.97 个百分点**。但压力浸泡的 CPU 26.35% 反而低于本轮 idle 33.27%，FPS 也 21.58 vs 27.95，说明窗口/桌面合成状态对 CPU 和帧时间影响很大。本轮 idle 与阶段 1 不是同一会话，不能把 6.97pp 全归因于状态机；要严格门禁，需要同一桌面状态下的 A/B 复测。

### 3.2 真实窗口点击与拖拽

- 点击穿透：`check_click_through.py --click`，卡片命中 `HTTRANSPARENT (-1)`，模型区 `HTCLIENT (1)`，Tk 目标实际收到 1 次点击。结果 `build/stage2-queue/click-through-result.json`。
- 拖拽：真实鼠标 down → 10 步移动 → up，窗口从 (1420,430) 移到 (1510,475)，位移 (90,45)；目标 (100,50)，误差来自起点/系统缩放取整。结果 `build/stage2-queue/drag-test.json`。
- 聊天：3D shell 没有聊天入口，本轮未验；#70 只能算部分覆盖。

## 4. 已知边界

- `maxWaitMs` 固定 5000ms；超过 5 秒还没轮到的卡会丢，日志 `anim card dropped`。
- 队列 FIFO 只保证同优先级；高优先级动作仍可插队。
- 没有真正 crossfade；卡面仍是硬切 + sprite 自身 0.12s alpha。
- 队列版 10 分钟已跑：idle 基线平均/p50 接近阶段 1，但 p99 +3.18ms、CPU +6.97pp；压力场景 swap 限制使 FPS 约 21.6。
- 生产 `3d/whale3d.exe`、Release 资产、阶段 0/1 waiver 均未改。
- #70 已覆盖真实点击穿透和拖拽；3D shell 无聊天入口，聊天未验，所以 #70 仍不能关闭。
- 没有真正 crossfade，`ShellUi::setFace` 仍直接调用。

## 5. 下一步

1. 决定是否接受 idle p99 48.36ms / CPU 33.27% 的回归；不接受就先做 idle 路径优化，再复跑 10 分钟。
2. #70 剩余聊天触发；3D shell 当前无聊天入口，需要确认验收范围或接回 2D/聊天面板。
3. 真实 crossfade 暂不先做；先等 action/expression 的真正动画资产。
