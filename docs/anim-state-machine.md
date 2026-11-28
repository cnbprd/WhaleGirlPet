# 阶段 2 设计：动画状态机与手感

状态：**首刀与第一轮集成已落地；base clip、action/expression 卡门禁、17 卡验收通过；卡队列与 `EmotionBus` 有序队列尚未做。**

## 1. 当前问题

- `main.cpp` 直接调用 `model.setClip()`、`model.applyEmotion()`、`model.applyGazeLean()`、`sprite.showCard()`。
- 谁后调用谁赢：低优先级表情卡可以顶掉高优先级动作；`EmotionBus::poll()` 只取本次 poll 的最后一帧，同一批高优先级包会丢。
- 没有固定 tick：动画/spring 跟着墙钟帧走，长帧会一次性推进过大。
- 状态切换没有统一事件和可读 trace，只能从 `fps=` 日志猜。

## 2. 分层

| 层 | 内容 | 优先级 | 说明 |
|---|---|---:|---|
| base | idle、walk | 0 | 常驻底层，可循环；与 expression 同优先级，后到者胜 |
| face | expression/idle 等 10 张 | 0 | 第一轮集成按独占状态处理，避免挡住 base；后续再做真正的叠加 |
| action | wave、dance、type、balloon 等 7 张 | 40 | 高优先级、有限 TTL；同优先级的新动作可替换旧动作，低优先级表情不能抢占 |
| overlay | gaze、lean、spring | 0–50（权重） | 仍由 `applyGazeLean` 直接处理，不参与 clip 抢占 |
| card | 17 张 2D 卡面 | 独立队列 | **队列尚未实现**；当前低优先级卡直接丢弃，不排队 |

原则：`AnimationController` 只决定“当前应该是什么状态/权重”，`Model` 继续负责采样、GL、spring、表情帧。第一轮集成没有改 `Model` 内部。

## 3. 状态表 schema

```json
{
  "version": 1,
  "default": "idle",
  "states": [
    {
      "id": "idle",
      "layer": "base",
      "clip": "idle",
      "face": "open",
      "priority": 0,
      "loop": true,
      "interruptible": true,
      "fadeInMs": 0,
      "fadeOutMs": 0
    },
    {
      "id": "action_wave",
      "layer": "action",
      "clip": "idle",
      "face": "smile",
      "priority": 40,
      "loop": false,
      "interruptible": true,
      "ttlMs": 1800,
      "fadeInMs": 120,
      "fadeOutMs": 180
    }
  ]
}
```

必填：`id`、`layer`、`clip`、`priority`。  
`face` 可空；`ttlMs=0` 表示不自动过期；`loop` 默认 true；`interruptible` 默认 true。

## 4. 仲裁规则

1. 优先级高者胜。
2. 同优先级时，后到的请求胜（latest-wins），但必须记录 `seq`，不能依赖遍历顺序。
3. 当前状态 `interruptible=false` 时，低优先级请求被拒绝；同优先级也不抢占。
4. TTL 到期后回退到当前最高优先级的 base；没有 base 时回 `default`。
5. 切换有 `fadeInMs`/`fadeOutMs`；第一刀先只计算权重和目标状态，不实际采样混合。
6. `FixedStep` 用 accumulator 固定 1/60 推进逻辑；单帧最多 4 个 substep，避免长帧炸开。

## 5. 卡面队列（尚未实现）

- 目标：`CardRequest` 字段 `cardId`、`priority`、`ttlMs`、`source`；只显示最高优先级且未过期的一张。
- 当前第一轮集成：低优先级卡请求只更新控制器 pending，**不显示、也不在动作结束后补显示**；等于直接丢弃。17 卡验收靠动作状态可被同优先级新动作替换才通过。
- 下一步：实现真正的 `CardQueue`，动作结束后 pop 下一条，避免低优先级表情卡在动作期间永久丢失。

## 6. EmotionBus 顺序（尚未实现）

- 目标：`poll()` 改为一次取出本次 socket 队列中的全部有效帧，写入有序队列，不再只返回最后一帧。
- 当前仍是原 `poll()`：同一轮只返回最后一帧；控制器已能按状态优先级拦截卡面，但同批多帧仍在传输层丢失。
- 每帧带 `seq`；同一 `source` 的连续包按 latest-wins 合并，不同 source 按 priority + seq 仲裁。
- 保留现有 JSON 字段，不改 Python/LLM 侧协议。

## 7. 首刀范围

- 新增 `3d/animation_controller.h`：纯 header、无 SDL/GL 依赖，可单测。
- 新增 `3d/tests/test_animation_controller.cpp`：优先级、同优先级 latest-wins、TTL、不可打断、fixed tick 五类夹具。
- **不在首刀改 `main.cpp`、`model.cpp`、`sprite.cpp` 的现有调用**；先让状态层可测试，再集成。

## 8. 退出条件

- 单元夹具全过。
- 17 卡全部可见，动作/表情/gaze/spring 无互相覆盖回归。
- 10 分钟浸泡帧时间不高于阶段 1 基线；无新增 crash。
- 真实窗口手感验收（旧任务 #70）完成。
- 产出本文件 + `docs/anim-state-machine.md` 的集成记录。

## 9. 首刀落地记录（2026-11-28）

已落地：

- `3d/animation_controller.h`：纯 header，状态表加载、priority/seq 仲裁、TTL、不可打断、`advance()` 固定 1/60 tick（单次最多 4 substep）。
- `3d/tests/test_animation_controller.cpp`：20 条断言组通过，覆盖 base 切换、优先级、同优先级 latest-wins、TTL 回退、不可打断、固定 tick、启动状态保持、非法状态表。
- `.github/workflows/3d-build.yml`：新增 `Animation controller unit tests`，在 Windows CI 编译并运行同一份夹具。

本地验证命令：

```powershell
& 'F:\WhaleGirlPet\.toolchains\w64devkit\w64devkit\bin\g++.exe' -std=c++17 -O2 -Wall -Wextra -I'F:\WhaleGirlPet\3d' 'F:\WhaleGirlPet\3d\tests\test_animation_controller.cpp' -o 'F:\WhaleGirlPet\build\test_animation_controller.exe'
& 'F:\WhaleGirlPet\build\test_animation_controller.exe'
```

结果：20/20 PASS，exit 0。

## 10. 第一轮集成记录（2026-11-28）

已接入：

- `3d/anim_state_table.h`：内置 19 态 fallback 表（2 base + 10 expression + 7 action）；阶段 3 的资产 cook 再替换成 content 表。
- `main.cpp`：W 键不再直接 `nextClip()`，改为 `animation.request()`；每帧 `advance(dt*1000,4)`，只把 base 决策落到 `model.setClip()`。
- 动作/表情卡：`action/wave` → `action_wave`，`expression/happy` → `expression_happy`；动作 40、表情 0。低优先级表情卡在动作期间被拒绝显示，动作结束回 base。
- `WHALE3D_CLIP=walk` 启动时控制器同步为 walk；`ShellUi` 设置里的直接 `setClip` 被主循环检测为 external 并同步，避免动作结束把用户设置打回 idle。
- `PerfStats` 的 `card` 字段暂填当前 controller activeId，方便从 `stat` 直接看状态。

实测：

| 项 | 结果 |
|---|---|
| 单元夹具 | 20/20 PASS |
| W 键注入 WM_KEYDOWN | idle→walk→idle，日志 `anim request` / `anim base` 正确 |
| `WHALE3D_CLIP=walk` | `AnimationController ready default=walk active=walk`，4 秒保持 walk |
| action TTL 到期 | `action_wave` 到期后 `anim state: walk clip=walk priority=0 source=default` |
| 动作/表情优先级 | wave 活跃时 `expression/happy` 被 `anim card deferred` 拒绝显示 |
| 17 卡可见 | `check_cards_visible.py` 17/17 captured；QA `build/stage2-cards/2d-card-visible-qa.json` |
| headless 60 render | exit 0，p50 1.01ms / p99 3.50ms / work 1.21ms |
| headless 600 render | exit 0，p50 0.85ms / p99 2.31ms / work 0.96ms |
| normal stats | FPS 28.8，RSS 70.6–71.1MB，private 113.3–113.7MB；动作晚段曾掉到 20.9 FPS，随后恢复 28.7 |

仍未完成：卡队列、`EmotionBus` 多帧有序队列、真正 crossfade 采样、真实窗口手感 #70。10 分钟集成浸泡已完成：FPS avg 27.78（基线 27.86）、p50 34.92ms（34.78）、p99 47.02ms（45.18）、hitch 134（190）、RSS 70.2–72.9MB，无 crash；详见 `docs/stage2-integration.md`。

