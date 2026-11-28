# 阶段 2 第一轮集成记录

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：run `46128539544` success（20 条动画夹具 + headless 60 no-render）。  
构建：`3d/whale3d-stage2-integration.exe`，1,410,048 B，
SHA256 `8CE361E495B341CD94C1B3C324EFF4ED03B8930E1692345D84EDF0BA9626BE29`。  
性质：**测试构建，不替换生产 `3d/whale3d.exe`。**  
后续：卡队列与 `EmotionBus::pollAll` 已在本文件之后接入，见 `docs/stage2-queue.md`；本文保留第一轮证据。

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

### 10 分钟浸泡

命令：`build/stage2-soak.ps1`，正常窗口，`WHALE3D_KEEP_AWAKE=1`，600 秒；日志 `build/stage2-soak.log`，trace `build/stage2-soak-trace.jsonl`，CPU/RSS `build/stage2-soak.csv`。

| 指标 | 本轮 | 阶段 1 基线 |
|---|---:|---:|
| FPS avg | 27.78 | 27.86 |
| interval p50 avg | 34.92ms | 34.78ms |
| p95 avg | 39.73ms | 39.18ms |
| p99 avg | 47.02ms | 45.18ms |
| hitch 总数 | 134 | 190 |
| RSS | 70.2–72.9MB | 70.1–73.0MB |
| private | 112.0–113.1MB | 112.2–113.3MB |
| CPU（单核） | avg 33.13%，30.11–37.32% | A 29.61%，B 26.30% |

结论：600 秒无 crash，RSS/private 无持续增长；平均 FPS 和 p50 与阶段 1 基本持平，p99 比基线高 1.84ms（4.1%），hitch 更少。CPU 比阶段 1 高约 3.5 个百分点（33.13% vs 29.61%），属于控制器每帧 `advance` 和状态日志的增量，暂记为阶段 2 观察项，不作为通过门槛。FPS min 14.7 是启动段单样本，未持续。

## 3. 已知边界

- **第一轮卡队列未实现**：低优先级卡在动作期间只更新 pending，动作结束不会补显示；第二轮已改为 `CardQueue` 补显。
- **第一轮 EmotionBus 未改多帧队列**：同一 poll 仍只取最后一帧；第二轮已改为 `pollAll`。
- **动作状态 `interruptible=true`**：同优先级新动作可以替换旧动作，保证 17 卡 QA 和真实使用里 dance→wave 不被锁死；低优先级表情仍不能抢占。
- **clip crossfade 已落地但只覆盖 idle/walk**：`Model::updateOzz` 现在双采样并混合局部骨骼；action/expression 没有独立 clip，仍不切 3D clip。详见 `docs/stage2-crossfade.md`。
- **ShellUi 设置里的 `setFace` 仍是直接调用**；本轮只同步 `setClip`。
- 10 分钟集成浸泡已完成，见上表；p99 略高于阶段 1 基线，CPU 高约 3.5 个百分点。

## 4. 下一步

1. 第二轮 `CardQueue` 已完成，见 `docs/stage2-queue.md`；队列版 idle 10 分钟和同机 A/B 已完成。
2. 做真实窗口 #70：点击/拖拽已过；聊天入口在 3D shell 不存在，待确认范围。
3. idle↔walk clip crossfade 已完成，见 `docs/stage2-crossfade.md`；同构建 17 卡截图、队列 6/6、真实点击/拖拽、90 秒与 10 分钟 W 浸泡均已完成；卡面 overlay crossfade 暂不做。
4. 生产包和 Release 资产暂不替换。
