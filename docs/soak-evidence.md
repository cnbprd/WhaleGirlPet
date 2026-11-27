# 浸泡失败取证

脚本：`3d\tools\collect_soak_evidence.ps1`  
模式：只读取证；不停止/启动任务，不重启 3D，不改生产 checkpoint。

## 什么时候用

- 24h 任务提前结束；
- `whale3d.exe` 消失但任务状态仍是 Running；
- `check_soak_status.ps1` 返回 stale / unhealthy；
- 24h 结束后需要保存现场。

## 命令

```powershell
Set-Location 'F:\WhaleGirlPet'

# 只看当前判定，不落盘
& '.\3d\tools\collect_soak_evidence.ps1' -DryRun

# 保存现场：docs\soak-evidence\<tag>-<timestamp>\
& '.\3d\tools\collect_soak_evidence.ps1' -OutDir 'docs\soak-evidence'

# 指定标签（例如排查旧轮）
& '.\3d\tools\collect_soak_evidence.ps1' -Tag '24h' -OutDir 'docs\soak-evidence'
```

## 采集内容

- 任务计划状态、LastTaskResult、LastRunTime、NextRunTime、missed runs；
- checkpoint 状态、样本数、elapsed、PID、父进程链、`whale3d.exe` 数量；
- `longrun_*.log` / `.err.log` 的尾部与文件大小；
- Application Error / Windows Error Reporting / System 41,6008 事件（从浸泡开始时间起）；
- 内存、开机时长、磁盘剩余空间；
- `summary.json`、`checkpoint.json`、`process-chain.json`、`events.json` 和日志尾部文件。

## verdict

| verdict | 含义 |
|---|---|
| `running_healthy` | 任务 Running、PID 存活、单实例、checkpoint 未 stale |
| `running_process_gone` | checkpoint 仍是 running，但 PID 已不存在 |
| `running_stale` | 进程还在，但 checkpoint 超过 stale 窗口 |
| `task_not_running_process_alive` | 任务已退出，但 3D 还活着 |
| `completed` | `status=done` 且进程仍存活 |
| `completed_process_dead` | `status=done` 但进程不在 |
| `checkpoint_missing` | checkpoint 不存在或无法解析 |

## 限制

- 事件查询只覆盖 Windows 事件日志中已有的记录；如果进程被静默 kill 或宿主直接清理，可能仍然没有 `whale3d.exe` 崩溃事件。
- 脚本不会自动定时运行；失败后需要手动执行，或由外层监控调用。
