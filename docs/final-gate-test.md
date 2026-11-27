# `check_soak_final.py` 合成测试记录

测试时间：2026-11-27（24h 浸泡运行期间，仅读临时 fixture，不碰 PID 7816）  
脚本：`3d/tools/check_soak_final.py`  
目的：确认最终 gate 在“有效完成”和“进程已死”两种结果上返回正确退出码，避免 24h 结束后把无效轮误判为通过。

## 测试方法

在 `docs/_gate_fixture` 下生成临时 checkpoint JSON，字段按脚本要求构造：

- `tag=soak_24h_sprite_task`
- `status=done`
- `finished_at` 存在
- `alive_after_soak=true`
- 无 `error`
- 60 秒、3 个样本
- 最后一个样本的 elapsed 接近 60 秒

先跑成功路径，再把 `alive_after_soak` 改成 `false` 跑失败路径。测试完成后删除临时 fixture，生产 checkpoint 未改动。

## 结果

| 场景 | 期望 | 实际 |
|---|---|---|
| 有效完成：`status=done`、`alive_after_soak=true` | exit 0 | exit 0 |
| 进程已死：`status=done`、`alive_after_soak=false` | 非 0 | exit 1，列出 `alive_after_soak is not true` |
| checkpoint 缺失（`--tag __missing_gate_fixture__`） | exit 2 | exit 2，打印 `missing checkpoint` |
| 当前仍在运行（真实 tag） | exit 3 | exit 3，打印 `NOT FINISHED` |

## 未覆盖

- 真实 24h 完成后的 `finish` 记录（要等 2026-11-28 13:51 后）；
- 样本数不足、`error` 非空等组合；
- Windows 任务计划程序返回码与实际进程状态的交叉验证。

## 结论

成功/失败/缺失/运行中四条路径符合脚本声明；该脚本可以作为 24h 结束后的第一道 gate，但不能替代真实 24h 运行。
