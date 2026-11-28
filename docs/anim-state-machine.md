# 阶段 2 设计：动画状态机与手感

状态：**首刀进行中；先做纯状态层 + 单元夹具，不重写 `Model`。**

## 1. 当前问题

- `main.cpp` 直接调用 `model.setClip()`、`model.applyEmotion()`、`model.applyGazeLean()`、`sprite.showCard()`。
- 谁后调用谁赢：低优先级表情卡可以顶掉高优先级动作；`EmotionBus::poll()` 只取本次 poll 的最后一帧，同一批高优先级包会丢。
- 没有固定 tick：动画/spring 跟着墙钟帧走，长帧会一次性推进过大。
- 状态切换没有统一事件和可读 trace，只能从 `fps=` 日志猜。

## 2. 分层

| 层 | 内容 | 优先级 | 说明 |
|---|---|---:|---|
| base | idle、walk、sleep | 0–10 | 常驻底层，可循环 |
| face | open、blink、smile | 15–25 | 增量覆盖，不抢占 base |
| action | wave、dance、type、balloon 等 | 30–50 | 高优先级、有限 TTL；默认不可被低优先级打断 |
| overlay | gaze、lean、spring | 0–50（权重） | 叠加层，不参与 clip 抢占 |
| card | 17 张 2D 卡面 | 独立队列 | UI 层，按 priority + TTL 排队 |

原则：`AnimationController` 只决定“当前应该是什么状态/权重”，`Model` 继续负责采样、GL、spring、表情帧。第一刀不改 `Model` 内部。

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
      "id": "wave",
      "layer": "action",
      "clip": "idle",
      "face": "smile",
      "priority": 40,
      "loop": false,
      "interruptible": false,
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

## 5. 卡面队列

- `CardRequest` 字段：`cardId`、`priority`、`ttlMs`、`source`。
- 只显示最高优先级且未过期的一张；低优先级不顶掉高优先级。
- 同优先级后到者胜，但旧卡保留到新卡 fade-out 完成（后续阶段再接 overlay 混合）。
- 当前 `sprite.showCard()` 的单卡覆盖在集成时替换为队列 pop。

## 6. EmotionBus 顺序

- `poll()` 改为一次取出本次 socket 队列中的全部有效帧，写入有序队列，不再只返回最后一帧。
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
- `3d/tests/test_animation_controller.cpp`：15 条断言组通过，覆盖优先级、同优先级 latest-wins、TTL 回退、不可打断、固定 tick、非法状态表。
- `.github/workflows/3d-build.yml`：新增 `Animation controller unit tests`，在 Windows CI 编译并运行同一份夹具。

本地验证命令：

```powershell
& 'F:\WhaleGirlPet\.toolchains\w64devkit\w64devkit\bin\g++.exe' -std=c++17 -O2 -Wall -Wextra -I'F:\WhaleGirlPet\3d' 'F:\WhaleGirlPet\3d\tests\test_animation_controller.cpp' -o 'F:\WhaleGirlPet\build\test_animation_controller.exe'
& 'F:\WhaleGirlPet\build\test_animation_controller.exe'
```

结果：15/15 PASS，exit 0。

首刀**没有**接入 `main.cpp`/`Model`/`SpriteLayer`，也没有实际淡入淡出采样；这是刻意的边界。下一步是把 `main.cpp` 的三处直接调用收编到控制器，并先接 `setClip`/`setFace`，再接 `showCard` 队列。

