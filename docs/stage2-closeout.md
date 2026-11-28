# 阶段 2 收口：3D 引擎范围条件退出

日期：2026-11-28  
分支：`feat/v3.3-observe`  
结论：**3D 动画/卡面/手感部分通过；聊天项不在 3D core 范围，不写成 pass。阶段 2 按 3D 引擎范围条件退出，阶段 3 开始。**

## 1. 已通过

| 项 | 证据 |
|---|---|
| 动画状态机 | 20/20 夹具；CI `46135131492` success |
| 卡队列 | 35/35 夹具；真实窗口 6/6 |
| 17 卡 | `build/stage2-crossfade-cards/` 捕获 17/17，contact sheet 目检 17 张都在 |
| 真实点击穿透 | `build/stage2-crossfade-click.json`：`ok:true`，卡面 `-1`、模型 `1`、目标 1 次点击 |
| 真实拖拽 | `build/stage2-crossfade/drag-test.json`：`ok:true`，delta (90,45) |
| idle↔walk crossfade | 双采样 Lerp/NLerp，180ms；W 切换、headless 60/600、90 秒 147 次 fade、10 分钟 298 次 fade，无退出 |
| 10 分钟队列浸泡 | 60/60 补显、0 丢弃、无 crash；CPU 26.35% |
| 同机 A/B | stage1-stats 31.52% vs queue 33.27%，CPU +1.75pp；队列帧时间更好但 swap 路径不同 |
| 生产资产 | 未替换 `3d/whale3d.exe`、未改 Release 资产 |

## 2. 明确未闭合

- **S2-CHAT-SCOPE**：`3d/README.md` 第 7 条写明这套 3D core 不含 AI/cloud/PySide6；3D 壳没有聊天入口。因此 #70 的“聊天”无法在 3D 壳验收。本项不是 pass，只是从“3D 动画/手感”范围排除；聊天保留为 2D/后续独立任务。
- **S2-FRAME**：队列版 idle 相对历史阶段 1 基线 p99 +3.18ms；同机 A/B 中队列 p99 反而低于 stage1-stats（48.36 vs 111.50ms），但两轮 swap 7.05 vs 0.11ms，不能把帧时间差直接归因代码。CPU +1.75pp 接受，帧时间不宣称“正式不高于阶段 1”。
- **S2-OVERLAY**：卡面 overlay 仍是硬切 + 0.12s alpha；没有做双层 crossfade。
- **S2-FACE**：`ShellUi::setFace` 仍直接调用，face 未归 controller。

## 3. 退出判定

按当前计划的**3D 引擎范围**，阶段 2 条件退出：

1. 动画、队列、卡面、点击、拖拽、crossfade 都有可复现证据。
2. 聊天不属于 3D core，不阻塞引擎主线；#70 继续作为独立待办，不关闭。
3. 阶段 3 只做资产校验/清单/打包，不动渲染层，不做完整 chat/UI。

若后续要求“3D 壳必须自带聊天”，应另开任务，不把本收口回写成已完成。
