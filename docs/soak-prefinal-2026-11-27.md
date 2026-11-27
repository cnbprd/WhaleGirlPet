# 24h 浸泡最终 gate 预检（运行中）

时间：2026-11-27 15:40 左右  
命令：`python 3d\tools\check_soak_final.py --tag soak_24h_sprite_task --json`

## 结果

`EXIT_CODE=3`，符合“仍在运行 / 未完成”的预期。

```json
{
  "status": "running",
  "finished": false,
  "valid": false,
  "samples": 220,
  "expected_samples": 2881,
  "duration_s": 86400.0,
  "elapsed_s": 6570.1,
  "issues": [
    "status is 'running', not 'done'",
    "sample count 220 < expected 2881 - 2",
    "last elapsed 6570.1s is short of 86400s"
  ]
}
```

结论：gate 没有把 `running` 误判为完成，退出码 3 正确。

## 顺带发现：单帧低 FPS

日志中只有 1 行 `fps=3.7`（第 195939 行），同一行 `update_us=237118.46`，随后立即回到 `fps=27.8`、`update_us≈47.7`。

- 出现次数：1 次；
- 持续情况：不是连续降速，前后都是 27–28 fps；
- 当前 checkpoint：220 样本、`status=running`、`updated_at=15:40:35`。

判断：这是一次约 237 ms 的单帧长帧，可能是系统调度/窗口管理/外部扫描造成的瞬时停顿；不足以证明泄漏或持续卡顿，但应作为 24h 结束前的观察项。若后续低 FPS 行增多或连续出现，再按失败取证处理。

## 限制

- 本次只是运行中预检，不是 24h 结论；
- 单帧异常无法从现有日志定位外部原因；
- 不杀进程、不重启、不启动第二个 3D。
