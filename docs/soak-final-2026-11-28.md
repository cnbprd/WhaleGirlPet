# 24 小时浸泡最终结果（2026-11-28）

## 结论

`soak_24h_sprite_task` 已结束，最终 gate `exit 0`、`valid=True`、`issues=[]`。  
本轮判定为 **24h 通过**，不是中途退出；墙钟超过 24 小时标记。

## 关键数据

- tag：`soak_24h_sprite_task`
- 启动：`2026-11-27T13:51:03+0800`
- 结束：`2026-11-28T13:53:36+0800`
- 任务状态：`done`，任务结果 `0`
- gate：`exit 0`，`finished=True`，`valid=True`，`issues=[]`
- 目标时长：`86400.0s`
- 墙钟：`86553.0s`（24h 2m 33s）
- 最后采样：`elapsed_s=86370.2`
- `alive_after_soak=True`
- 样本：`2880`，期望 `2881`；只差最后一条采样，gate 未判失败
- RSS：`69.5 MB` → `11.4 MB`，delta `-58.1 MB`
- FPS：min `0.0`、max `29.3`、avg `27.25`、last `9.6`

`healthy=false` 是进程正常退出后的状态，不是浸泡失败。任务计划程序历史里的 `0x800710E0` 是 13:52:40 重复触发被拒绝，不是本轮 PID 7816 的失败。

## 证据文件

- `docs/soak-final-2026-11-28/gate.txt`
- `docs/soak-final-2026-11-28/longrun_soak_24h_sprite_task.json`
- `docs/soak-final-2026-11-28/longrun_soak_24h_sprite_task.log`（约 158 MB，留在本机；因体积未入 Git）
- `docs/soak-final-2026-11-28/longrun_soak_24h_sprite_task.err.log`（0 字节）
- `docs/soak-final-2026-11-28/soak-midrun-2026-11-27.md`

## 判定说明

- 按 `docs/post-soak-runbook.md`，`check_soak_final.py` 必须 `exit 0`、`valid=True`、`status=done`、`alive_after_soak=True`；本轮四项均满足。
- 样本数比期望少 1，属于最后采样边界，不影响 gate 的 `valid` 判定。
- 24h 之后已继续完成 P1 17/17、17 卡可见 17/17、真实点击穿透和安装器安装/卸载回归；证据见 `docs/2d-card-visible-qa.md`、`docs/click-through-qa.md`、`docs/release-asset-verify.md`。
