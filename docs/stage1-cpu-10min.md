# 阶段 1 CPU 10 分钟采样

日期：2026-11-28  
构建：`3d/whale3d-headless.exe`，1,381,888 B，SHA256 `CEA67348C99905EC6EE9626ECA20FB99C4E32374431CE5C0F742AB152013D9CF`。  
环境：GTX 1060 6GB / NVIDIA 582.78 / OpenGL 3.3.0；窗口模式；`WHALE3D_STAT=1`、`WHALE3D_KEEP_AWAKE` 按 run 设置。

## 1. 采样方法

- PowerShell `Start-Process` 启动正常窗口（不是 headless）。
- 每 10 秒读一次 `Process.TotalProcessorTime`，用相邻差值除以墙钟秒数，得到 **单核百分比**（100% = 一个逻辑核心跑满，不等于整机 CPU）。
- 共 60 个样本，取 `t_s >= 30s` 的 58 个稳态样本；去掉前 20 秒的启动/shader 编译抖动。
- 第二个 run 设置 `WHALE3D_KEEP_AWAKE=1`，用来检查显示空闲是否影响 CPU；FPS 仍受当前桌面合成环境影响。

## 2. 结果

| Run | 样本 | CPU 单核 avg | p50 | p95 | min–max | FPS avg | p50 | p95 | p99 | work | swap | RSS | private |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A 无 keep-awake | 58 | 29.61% | 29.31% | 34.35% | 25.13–36.89% | 22.82 | 43.79 ms | 48.88 ms | 53.16 ms | 11.16 ms | 8.57 ms | 70.94–73.00 MB | 113.2–114.3 MB |
| B keep-awake | 58 | 26.30% | 26.37% | 28.06% | 22.48–29.03% | 21.40 | 45.96 ms | 52.79 ms | 61.35 ms | 13.39 ms | 10.37 ms | 69.75–70.58 MB | 112.7–114.1 MB |

两次 run 都跑满 60 个采样、无 crash、RSS/private 无持续增长。B 的 CPU 均值更低，说明 `ES_DISPLAY_REQUIRED` 确实减少了空闲路径的系统开销；但这轮窗口仍被桌面合成压到 21–22 FPS，不能用 B 的 FPS 替代阶段 1 的 27.86 FPS keep-awake 基线。

## 3. 判定

- **CPU 门禁通过**：10 分钟有实测，单核占用约四分之一到三分之一，没有接近单核跑满，也没有随时间的单调上涨。
- **帧时间门禁仍以 `docs/stage1-baseline-10min.md` 的 27.86 FPS / p50 34.78 ms 为准**；本文件只回答“CPU 占多少”，不重写帧时间基线。
- **未通过/未覆盖**：CI 仍没有 Windows GPU runner，`--headless` 的真实 render 路径只在本地验证。该项作为阶段 1 的条件 waiver，转入阶段 4/基础设施，不冒充已验证。

## 4. 证据

- `build/stage1-cpu-10min.csv`、`build/stage1-cpu-10min.log`、`build/stage1-cpu-10min-trace.jsonl`、`build/stage1-cpu-10min-summary.json`
- `build/stage1-cpu-keepawake.csv`、`build/stage1-cpu-keepawake.log`、`build/stage1-cpu-keepawake-trace.jsonl`、`build/stage1-cpu-keepawake-summary.json`
- 采样脚本：`build/stage1-cpu-keepawake.ps1`（临时验证脚本，未入 Git）
