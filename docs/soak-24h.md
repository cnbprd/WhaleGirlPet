# 24 小时 3D 浸泡

状态：**旧轮提前结束；当前有效轮是任务计划程序轮，仍在进行中。** 2026-11-27 12:44:05 左右旧 3D 进程 PID 15080 退出，实际约 8 小时 26 分；最后一个检查点仍是 `status=running`，没有 `done` / 最终报告。当前有效轮见“任务计划程序轮”。

- 启动：2026-11-27 04:18:14 +0800（Asia/Shanghai）
- 预计结束：2026-11-28 04:18:14 +0800
- 3D 进程 PID：15080；Python 启动器 PID：10492
- 模式：离屏（窗口移到屏幕外，仍以约 28–29 fps 渲染，不占桌面）
- 时长：86,400 s；采样间隔 30 s；输出标签 `24h`
- 检查点：`3d/longrun_24h.json`；运行日志：`3d/longrun_24h.log`
- 截图：离屏模式不截图；可见窗口的 10 分钟证据仍是 `docs/_3d_longrun_10m_mid.png`、`_3d_longrun_final.png`

## 启动时实测

| 项 | 值 |
|---|---|
| 3D 进程 | 存活，PID 15080 |
| FPS | 28.9–29.1 |
| 三角形 | 2,076 |
| 动画 | `ozz`、`clip=idle`、自动眨眼 |
| 离屏 CPU | 启动约 36 s 累计 CPU 2.53 s（约 7% 单核，远低于可见窗口的 35%） |
| 首条 JSON 检查点 | 04:22:47 写入；`status=running`，`samples=10`，`elapsed_s=270`；最后一条 RSS 70,651,904 B（约 67.4 MB），3D 进程存活 |

## 51 分钟中间检查点

- `status=running`，`samples=100`，`elapsed_s=2970.1`（约 49.5 分钟），`updated_at=2026-11-27T05:07:47+0800`。
- RSS 起 **67.5 MB**、当前 **68.6 MB**，差 **+1.1 MB**；最近 10 条样本稳定在 **71,929,856 B**，没有继续爬。
- 早段线性斜率约 **+1.62 MB/h**，不能外推成 24 小时泄漏结论；需要看后段是否平台化。
- CPU 平均 **7.2%** / 峰值 **8.8%**；FPS 平均 **28.34** / 最低 **5.8**（启动段）/ 最后 **28.0**。
- 由 `3d/tools/soak_report.py --tag 24h` 生成；`stale=False`。

## 8 小时中间检查点

- `status=running`，`samples=1000`，`elapsed_s=29970.1`（约 8 小时 19 分），`updated_at=2026-11-27T12:37:47+0800`。
- RSS 起 **67.5 MB**、当前 **68.0 MB**，差 **+0.5 MB**；线性回归斜率 **-0.077 MB/h**，说明早段上涨后已经平台化/轻微回落，不是持续泄漏。
- CPU 平均 **7.5%** / 峰值 **10.0%**；FPS 平均 **27.94** / 最低 **4.8**（启动段）/ 最高 **29.2** / 最后 **28.8**。
- 3D 进程仍存活，`stale=False`，`error=None`。距离 24 小时结束还剩约 **15.7 小时**。

## 提前结束（2026-11-27 12:44）

- 3D PID 15080 已不存在（`tasklist /FI "PID eq 15080"` 无结果）；Python 启动器 PID 10492 也不在进程列表。
- `3d/longrun_24h.json` 最后更新 12:42:47，`status=running`、`elapsed_s=30270.0`、1010 样本；没有 `done`、没有 `alive_after_soak`、没有错误字段。
- `3d/longrun_24h.log` 最后写入 12:44:05，尾部是正常的 `EmotionTrace`，没有异常堆栈；`3d/longrun_24h.err.log` 为空。
- Windows Application 日志在 12:44 前后没有 `whale3d.exe` 的崩溃事件；原因无法仅凭现有日志确定，可能是窗口被关闭/进程被终止/环境清理，不能归因于某一条代码路径。
- 因此这轮**不能**当 24 小时通过；8 小时 26 分的数据可保留作中段趋势证据，但 24 小时结论要重新跑一轮。

## 新一轮：带 sprite 的生产 exe（已被任务计划程序轮取代）

2026-11-27 13:41:47 +0800 用重建的 `3d/whale3d.exe`（1,377,792 B，含 sprite 接线）启动过一轮 24 小时离屏浸泡：

- 启动：2026-11-27 13:41:47 +0800；3D PID 31812；Python 启动器 PID 27352
- 标签：`soak_24h_sprite`；检查点 `3d/longrun_soak_24h_sprite.json`；日志 `3d/longrun_soak_24h_sprite.log`
- 启动日志：`Sprite layer: ready (F:\WhaleGirlPet\3d\../assets/2d_bridge)`、`Hit mask ready: 420x620 center_alpha=255`、FPS 约 29
- 该轮仍挂在 agent 会话进程树 `pwsh -> python 27352 -> python 10312 -> whale3d 31812` 下，存在被宿主/任务切换截断的风险。2026-11-27 13:51 左右已主动结束，检查点状态标记为 `aborted_by_agent_session_restart`，不计入 24 小时结论。

## 任务计划程序轮（当前有效）

为避免再次被 agent 会话清理截断，改用 Windows 任务计划程序启动，进程树不再以当前 `pwsh` 为祖先：

- 计划任务：`WhaleGirlSoak24hSprite`
- 启动包装脚本：`3d/tools/soak_24h_sprite_task.cmd`（`build/soak_24h_sprite_task.cmd` 是同一份临时副本）
- 启动：2026-11-27 13:51:03 +0800；3D PID 7816；Python 启动器 PID 22720
- 标签：`soak_24h_sprite_task`；检查点 `3d/longrun_soak_24h_sprite_task.json`；日志 `3d/longrun_soak_24h_sprite_task.log`
- 预计结束：2026-11-28 13:51:03 +0800；时长 86,400 s；采样间隔 30 s；离屏模式
- 进程树：`svchost.exe (2784) -> cmd.exe (32232) -> python.exe (22720) -> python.exe (11864) -> whale3d.exe (7816)`；任务服务不是 agent 子进程
- 启动日志：`Sprite layer: ready (F:\WhaleGirlPet\3d\../assets/2d_bridge)`、`Hit mask ready: 420x620 center_alpha=255`、FPS 约 29
- 13:52:40 的一次性触发到达后仍只有 1 个 `whale3d.exe`，`MultipleInstances=IgnoreNew` 阻止了重复实例；该次触发记录为 `0x800710E0`（操作员或系统管理员拒绝了请求），当前 13:51:01 启动的实例继续运行
- 13:55:35 首个 10 样本检查点：`elapsed_s=270.1`，RSS `72,736,768 B`（约 69.4 MB），3D PID 7816 存活
- 任务状态：`Running`；这只是中段证据，结束前不能当 24 小时通过

检查命令：

```powershell
Get-ScheduledTaskInfo -TaskName 'WhaleGirlSoak24hSprite'
Get-Content 'F:\WhaleGirlPet\3d\longrun_soak_24h_sprite_task.log' -Tail 20
```

任务计划程序的限制：机器休眠/关机、用户注销或任务计划程序服务被停，仍会中断；这种方式只消除了 agent 会话进程树清理这一条风险，不等于绝对不中断。

## 终止原因线索（2026-11-27 补充）

- 时间线不支持“sprite GPU 测试截断”：旧轮最后日志 `12:44:05`，第一轮 sprite 可见测试日志 `13:11:54`，相差约 27 分钟。
- 旧 3D PID 15080 与 Python 启动器 PID 10492 同时消失；`longrun_24h.err.log` 为空，Windows Application 日志没有 `whale3d.exe` 崩溃事件，也没有 `status=done`。这更像外部终止（窗口关闭、进程树清理或宿主重启），不是 3D 自己崩溃。
- Windows `stability` 事件在 `12:41:11` 和 `12:51:11` 有 `Doubao.exe` 的 restart/restore 记录；当前 Doubao 进程命令行也带 `--restart --restart-for-update`。宿主重启/任务进程树清理是高度可疑的外部因素，但现有日志不能证明是哪一次操作直接杀了 PID 15080。
- 新一轮 `soak_24h_sprite` 的进程树是 `pwsh -> python 27352 -> python 10312 -> whale3d 31812`，仍挂在当前 agent 会话下；如果宿主再次重启或任务被切走，仍可能被同样方式终止。要得到可信的 24 小时结论，应该从 Windows 任务计划程序或独立于 agent 的进程启动。

## 判定规则

- 只有 `status=done` 且 `alive_after_soak=true`、RSS/CPU/FPS 样本完整，才算跑完。
- 进程被杀、机器休眠/关机、窗口被手动关闭，都会让本轮无效。
- 24 小时通过也只代表这一轮 24h 边界；仍不等于“永不泄漏”。

## 后续检查

1. 启动后 1 小时看一次 `longrun_24h.json` 的样本数与 RSS 趋势。
2. 12 小时看一次中段。
3. 结束后核对 `status=done`、样本数约 2,880、RSS/CPU/FPS 的起止与极值，再更新本文件和 CHANGELOG。
