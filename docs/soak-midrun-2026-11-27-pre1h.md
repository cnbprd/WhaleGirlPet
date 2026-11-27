# 24h 浸泡检查点：约 34.5 分钟（1 小时前）

采集时间：2026-11-27 14:25:35 +0800  
任务：`WhaleGirlSoak24hSprite`（`soak_24h_sprite_task`）  
结论：**运行正常；这不是 1 小时检查点，也不能当 24 小时结论。**

## 当前数据

- 任务状态：`Running`；检查点 `status=running`
- 3D PID 7816 存活；进程链 `whale3d(7816) -> python(11864) -> python(22720) -> cmd(32232) -> svchost(2784)`
- `whale3d_count=1`
- 样本数：70；`elapsed_s=2070.1`（约 34 分 30 秒）；剩余约 84,330 秒
- RSS：起始 69.48 MB → 当前 24.21 MB；区间最低 24.18 MB，最高 69.72 MB
- CPU 平均：5.80%
- 日志 FPS：最低 11.10，最高 29.30，平均 28.42，最后 28.0
- `stale=false`；`healthy=true`
- 任务 `LastTaskResult` 仍为 `0x800710E0`，是 13:52:40 重复触发被拒绝的历史记录，不是当前 PID 7816 的失败

## 解读边界

RSS 从 69 MB 降到 24 MB，更像 Windows 工作集回收，不是“已确认修复泄漏”。当前只能说明进程存活、CPU/FPS 没有明显失稳；真正的结论要等 24 小时结束后的 `check_soak_final.py`。

## 下一个检查点：1 小时（约 14:51）

到点只做只读检查，不启动第二个 3D、不构建、不安装：

```powershell
Set-Location 'F:\WhaleGirlPet'
& '.\3d\tools\check_soak_status.ps1'
& '.\3d\tools\check_soak_status.ps1' -Json
```

落盘内容：

- 任务状态、PID 7816、`whale3d_count=1`、`stale`、`healthy`；
- RSS 起止、CPU 平均、日志 FPS 最低/平均/最后；
- 若出现 `healthy=false` 或 PID 变化，先记录原始 JSON，不重启、不结束本轮。

后续检查点：6 小时（约 19:51）、12 小时（约次日 01:51）、24 小时（次日 13:51，跑 `check_soak_final.py`）。
