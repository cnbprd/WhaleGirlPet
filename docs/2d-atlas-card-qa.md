# 2D 卡面图集逐卡 QA

日期：2026-11-27  
输入：`assets/2d_bridge/atlas.png` + `assets/2d_bridge/manifest.json`  
工具：`3d/tools/check_2d_atlas.py`（CPU-only，不启动 3D）  
配套结构检查：`docs/2d-manifest-qa.md`

- 图集尺寸：1024x512
- 卡面数：17；失败：0
- 最大 alpha MAE：0.0
- 最大 RGB MAE：0.005
- 最大 coverage delta：0.0

| 卡 id | rect (x,y,w,h) | 源图 | alpha MAE | RGB MAE | coverage delta | 结果 |
|---|---:|---|---:|---:|---:|---|
| `expression/angry` | 35,4,90,152 | `assets/expressions/angry.png` | 0.0 | 0.002 | 0.0 | PASS |
| `expression/curious` | 194,4,91,152 | `assets/expressions/curious.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/eat` | 358,4,84,152 | `assets/expressions/eat.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/happy` | 516,4,88,152 | `assets/expressions/happy.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/idle` | 677,4,86,152 | `assets/expressions/idle.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/pat` | 838,4,83,152 | `assets/expressions/pat.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/shy` | 37,164,86,152 | `assets/expressions/shy.png` | 0.0 | 0.002 | 0.0 | PASS |
| `expression/sleep` | 167,164,145,152 | `assets/expressions/sleep.png` | 0.0 | 0.002 | 0.0 | PASS |
| `expression/sleepy` | 356,164,87,152 | `assets/expressions/sleepy.png` | 0.0 | 0.003 | 0.0 | PASS |
| `expression/walk` | 516,164,88,152 | `assets/expressions/walk.png` | 0.0 | 0.003 | 0.0 | PASS |
| `action/balloon` | 679,164,81,152 | `assets/actions/balloon.png` | 0.0 | 0.003 | 0.0 | PASS |
| `action/change` | 833,164,94,152 | `assets/actions/change.png` | 0.0 | 0.002 | 0.0 | PASS |
| `action/dance` | 35,324,89,152 | `assets/actions/dance.png` | 0.0 | 0.003 | 0.0 | PASS |
| `action/fireworks` | 188,324,103,152 | `assets/actions/fireworks.png` | 0.0 | 0.005 | 0.0 | PASS |
| `action/lion` | 347,324,105,152 | `assets/actions/lion.png` | 0.0 | 0.003 | 0.0 | PASS |
| `action/type` | 503,324,114,152 | `assets/actions/type.png` | 0.0 | 0.002 | 0.0 | PASS |
| `action/wave` | 677,324,86,152 | `assets/actions/wave.png` | 0.0 | 0.004 | 0.0 | PASS |

## 结论

- 17/17 卡在图集内、非空，且与源图在记录的 trim/scale 后一致。
- 该报告验证的是“图集内容正确”，不等于“17 张卡都已在 3D 可见窗口逐张目检”。当前只对 `expression/happy` 和 `action/wave` 做了 3D 可见验收。
- 卡面区域仍按代码约定不进入 `hitTest`，实际点击穿透未单独采样；不要在 24h 浸泡期间用可见窗口补测。

图集预览：`docs/_2d_bridge_contact.png`
