# 阶段 2：卡面队列与 EmotionBus 多帧

日期：2026-11-28  
分支：`feat/v3.3-observe`  
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
| CardQueue 单测 | 27/27 PASS |
| 同批多帧 | 日志 `Emotion batch: 2 frames`，两张卡都显示 |
| 动作期间表情 | `anim card queued: card=expression/happy ... active=action_wave active_priority=40 queued=1` |
| 动作结束补显 | `Sprite card queued: expression/happy state=expression_happy ttl=1200ms active=expression_happy queued_left=0` |
| 补显后过期 | 约 1.2s 后回 `idle` |
| 17 卡可见 | 17/17 captured，`build/stage2-queue-cards/2d-card-visible-qa.json` |
| headless 60 render | exit 0；p50 1.14ms / p99 4.16ms / work 1.18ms |
| headless 600 render | exit 0；p50 0.90ms / p99 1.97ms / work 0.96ms |
| headless 60/600 no-render | exit 0 |

真实窗口 QA 脚本：`3d/tools/check_card_queue.py`；结果 `build/stage2-queue/queue-test.json`，截图 `queue_after_action.png`。  
日志：`build/stage2-queue/queue-test.log`。  
headless 证据：`build/headless-smoke/headless-*-queue-summary.json`。

## 3. 已知边界

- `maxWaitMs` 固定 5000ms；超过 5 秒还没轮到的卡会丢，日志 `anim card dropped`。
- 队列 FIFO 只保证同优先级；高优先级动作仍可插队。
- 没有真正 crossfade；卡面仍是硬切 + sprite 自身 0.12s alpha。
- 没有 10 分钟队列版浸泡；旧 10 分钟浸泡属于上一构建。
- 生产 `3d/whale3d.exe`、Release 资产、阶段 0/1 waiver 均未改。
- 真实鼠标点击/拖拽/聊天 #70 仍未做。

## 4. 下一步

1. 队列构建跑 10 分钟浸泡，确认 tick/queue 无泄漏。
2. 补多张低优先级卡连续排队（happy→shy）实测。
3. 再进 #70 真实窗口点击/拖拽/聊天验收。
