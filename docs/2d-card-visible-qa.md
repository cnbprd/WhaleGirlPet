# 17 张 2D 卡面可见验收

日期：2026-11-28  
状态：**17/17 通过**

## 结论

单实例可见验收已完成。17 张卡全部在 3D 窗口右下角显示，方向正确、无整张图集网格、无缺角；卡面外层为透明 sprite，截图背景会随桌面内容变化，这是预期行为，不是卡面自身背景。

## 证据

- 总览图：`docs/_3d_visible_17_cards.png`
- 机器结果：`docs/2d-card-visible-qa.json`（`status=pass`）
- 逐卡整窗截图：`docs/_3d_visible_card_<id>.png`
- 逐卡裁图：`docs/_3d_visible_card_<id>_crop.png`

## 17 张结果

| # | card id | 结果 |
|---|---|---|
| 1 | `expression/idle` | PASS |
| 2 | `expression/happy` | PASS |
| 3 | `expression/eat` | PASS |
| 4 | `expression/walk` | PASS |
| 5 | `expression/sleep` | PASS |
| 6 | `expression/sleepy` | PASS |
| 7 | `expression/shy` | PASS |
| 8 | `expression/angry` | PASS |
| 9 | `expression/curious` | PASS |
| 10 | `expression/pat` | PASS |
| 11 | `action/wave` | PASS |
| 12 | `action/dance` | PASS |
| 13 | `action/type` | PASS |
| 14 | `action/balloon` | PASS |
| 15 | `action/fireworks` | PASS |
| 16 | `action/lion` | PASS |
| 17 | `action/change` | PASS |

## 说明

- 验收实例使用 `3.2.0-sprite` 安装器静默安装到临时目录后的 `whale3d.exe`；安装退出码 0，安装后的 `assets/2d_bridge` 完整。
- 脚本按顺序发送 17 个 card id，并逐卡等待 `Sprite card: <id>` 日志后再截图。
- 这一步证明“看得见、方向对、裁切对”，不替代点击穿透和安装器回归。
