# 阶段 1 进展：FrameStats 与 trace

日期：2026-11-28  
分支：`feat/v3.3-observe`  
状态：**FrameStats、1Hz trace、`--headless` 60/600 帧 smoke、CI no-GL smoke 已完成；`initLog` 分 session 尚未完成。**

## 1. 已实现

- `3d/perf_stats.h`：头文件实现，不新增 `.cpp`，不改变 `build.ps1` 源文件列表。
- `WHALE3D_STAT=1`：每秒输出一行 `stat`，含：
  - FPS、interval p50/p95/p99、work、hitch；
  - update / render / readback / region / overlay / swap 的均值。
- `WHALE3D_TRACE=<path>`：追加 JSONL，每秒一条，字段与 `stat` 对齐。
- 启动后 5 秒清空一次统计窗口，避免把模型加载、shader 编译、窗口创建的启动抖动算进稳态 p50/p95。
- `3d/main.cpp` 已接入 pass 计时点：model update、model render、hit-mask readback、region 更新、overlay 绘制、swap。

## 2. 实测

构建：`3d/whale3d-stage1-stats.exe` 与 `3d/whale3d-headless.exe` 均为 1,379,840 B，SHA256 `FB484EF558A4786B2E3808710ED0BE5DCEF4B2D81D791DA6E92D6C5923E8B80F`。  
环境：GTX 1060 6GB，驱动 582.78，OpenGL 3.3.0。

### 2.1 无卡面、15 秒

| 指标 | 值 |
|---|---|
| FPS | 27.5–28.2 |
| interval p50 | 34.56–34.81 ms |
| p95 | 38.76–39.48 ms |
| p99 | 39.90–40.58 ms |
| work | 2.05–2.47 ms |
| update | 0.01 ms |
| render | 0.01 ms |
| readback | 1.20–1.66 ms |
| region | 0.47–0.77 ms |
| overlay | 0.00 ms |
| swap | 0.07–0.18 ms |
| hitch | 0–1 |

同 exe 关闭 `WHALE3D_STAT`、同样 15 秒：FPS 27.0–28.9。统计开销在当前样本内接近噪声。

### 2.2 有卡面

- `expression/happy`、TTL 2000ms：15 秒测试出现过 19–23 FPS、swap 10–14ms 的段；同一构建重复测试又回到 28.5–29.0 FPS。
- 不是每次复现，暂按“桌面合成/overlay z 序抖动”记录，不把它归因给 `PerfStats`。
- 该问题在 Stage 4 的 pass/overlay 收口时复核；Stage 1 不先改 overlay。

### 2.3 trace

`build/stats-nocard-trace.jsonl` 共 14 行，逐行 `ConvertFrom-Json` 0 错误。示例字段：

```json
{"t_ms":2089,"fps":28.68,"frames":29,"p50_ms":34.08,"p95_ms":38.60,"p99_ms":41.27,"hitch":0,"update_ms":0.01,"render_ms":0.01,"readback_ms":0.69,"region_ms":0.62,"overlay_ms":0.00,"swap_ms":0.07}
```

## 3. Headless 60/600 帧

新增参数：

```text
--headless
--no-render
--frames=N
--fixed-dt=1/60
--summary=<path>
```

`--headless` 使用隐藏窗口，跳过托盘、overlay、UDP 和单实例互斥；模型路径仍可用位置参数指定。固定 dt 下只按帧数退出，summary 写入指定 JSON，trace 同时保留一行 summary。

| 帧数 | exit | GL error | center_alpha | summary p50/p99 | work |
|---|---|---|---|---|---|
| 60 | 0 | 0 | 255 | 1.44 / 5.57 ms | 1.62 ms |
| 600 | 0 | 0 | 255 | 0.96 / 3.34 ms | 1.14 ms |

`fps` 是 headless 实际跑帧速度（60 帧约 104 FPS，600 帧约 575 FPS），不是目标刷新率；固定 dt 的模拟时间仍是 `frames × 1/60`。

### CI 限制

GitHub `windows-latest` 只有 `GDI Generic` / OpenGL 1.1，无法创建本引擎需要的 3.3 core context（`glGenVertexArrays` 缺失）。因此 CI 用 `--headless --no-render`：

- 只验证固定 dt 循环、summary/trace schema、exit 0，不验证像素；
- summary `mode=headless-cpu`，`fps=0`（循环太快，不足 1ms，不做虚假估算）；
- 真实 GPU 的 60/600 帧 render 验证仍由本机结果负责。

脚本：`3d/tools/test_headless_smoke.py`，本机已跑 60/600 帧 render 路径和 60 帧 no-render 路径，均 PASS。证据在 `build/headless-smoke/`。

## 4. 未完成

- 逐帧 trace/环形缓冲尚未落盘；当前是 1Hz 聚合 trace。
- `initLog()` 每次覆盖日志的问题尚未修。

## 5. 下一步

1. 处理 `initLog()` 覆盖问题：按启动时间分文件或追加 session 头。
2. 再把 `--headless` 的 render 路径接到一台有 GPU 的 Windows runner（或接受 CI 只做 no-GL smoke 的 waiver）。
3. 再评估是否需要逐帧 trace；没有明确定位需求前不先加。
