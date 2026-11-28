# 阶段 2 第一轮集成记录

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：run `46128539544` success（20 条动画夹具 + headless 60 no-render）。  
构建：`3d/whale3d-stage2-integration.exe`，1,410,048 B，
SHA256 `8CE361E495B341CD94C1B3C324EFF4ED03B8930E1692345D84EDF0BA9626BE29`。  
性质：**测试构建，不替换生产 `3d/whale3d.exe`。**

## 1. 接入范围

- `3d/anim_state_table.h`：内置 19 态 fallback（2 base + 10 expression + 7 action）。
- `main.cpp` 的 W 键改为 `AnimationController::request()`，不再直接 `model.nextClip()`。
- 每帧 `animation.advance(dt*1000,4)`，只把 `idle`/`walk` 的 base 决策落到 `model.setClip()`；动作态不切 clip。
- 情绪卡：`action/wave` 映射 `action_wave`，`expression/happy` 映射 `expression_happy`；动作 40、表情 0。
- 动作活跃时低优先级表情卡被拒绝显示，避免动作被表情顶掉。
- `WHALE3D_CLIP=walk` 启动时 `start=walk`；`ShellUi` 设置里的直接 `setClip` 会被主循环检测为 external 并同步回控制器。
- `PerfStats` 的 `card` 字段临时填 controller `activeId`，便于 `stat` 直接看状态。

## 2. 验收结果

| 项 | 结果 | 证据 |
|---|---|---|
| 单元夹具 | 20/20 PASS，CI run `46128539544` success | `build/test_animation_controller.exe`、`build/ci-46128539544.log` |
| W 键单击 | idle→walk，`anim request base=walk active=walk clip=walk` | `build/stage2-key.log` |
| W 键双击 | walk→idle，日志有两次 `anim request` / `anim base` | `build/stage2-keytoggle.log` |
| 启动 clip=walk | `default=walk active=walk`，4 秒保持 | `build/stage2-clipwalk.log` |
| 动作 TTL 到期 | `action_wave` 到期回 `walk`，日志 `anim state: walk clip=walk priority=0 source=default` | `build/stage2-actionexpiry2.log` |
| 动作 vs 表情 | wave 活跃时 `expression/happy` 被 `anim card deferred`；动作卡仍显示 | `build/stage2-priority-final.log` |
| 17 卡可见 | 17/17 captured | `build/stage2-cards/2d-card-visible-qa.json`、`_3d_visible_17_cards.png` |
| headless 60 render | exit 0；p50 1.01ms / p99 3.50ms / work 1.21ms | `build/headless-smoke/headless-60-render-summary.json` |
| headless 600 render | exit 0；p50 0.85ms / p99 2.31ms / work 0.96ms | `build/headless-smoke/headless-600-render-summary.json` |
| headless 60/600 no-render | exit 0 | `headless-60-norender-summary.json`、`headless-600-norender-summary.json` |

正常窗口 stats：FPS 28.8，p50 34.1ms，RSS 70.6–71.1 MB，private 113.3–113.7 MB；动作/overlay 段曾掉到 20.9 FPS，随后恢复 28.7。

## 3. 已知边界

- **卡队列未实现**：低优先级卡在动作期间只更新 pending，动作结束不会补显示；等于丢弃。
- **EmotionBus 未改多帧队列**：同一 poll 仍只取最后一帧。
- **动作状态 `interruptible=true`**：同优先级新动作可以替换旧动作，保证 17 卡 QA 和真实使用里 dance→wave 不被锁死；低优先级表情仍不能抢占。
- **没有真正 crossfade 采样**：只输出 `fadeInMs/fadeOutMs` 和状态决策，`Model` 采样仍硬切。
- **ShellUi 设置里的 `setFace` 仍是直接调用**；本轮只同步 `setClip`。
- 10 分钟集成浸泡正在跑，结果补在本文件末尾。

## 4. 下一步

1. 做 `CardQueue`：低优先级卡不丢，动作结束后 pop；17 卡 QA 保持通过。
2. 做 `EmotionBus` 多帧有序队列：同批不丢，source priority + seq。
3. 接真实窗口 #70：点击/拖拽/动作/聊天触发全部走一次。
4. 通过后再谈 `Model` 内部 crossfade，不先重写采样器。
