# 阶段 1 进展：FrameStats 与 trace

日期：2026-11-28  
分支：`feat/v3.3-observe`  
状态：**部分完成；headless 60 帧回归尚未接入。**

## 1. 已实现

- `3d/perf_stats.h`：头文件实现，不新增 `.cpp`，不改变 `build.ps1` 源文件列表。
- `WHALE3D_STAT=1`：每秒输出一行 `stat`，含：
  - FPS、interval p50/p95/p99、work、hitch；
  - update / render / readback / region / overlay / swap 的均值。
- `WHALE3D_TRACE=<path>`：追加 JSONL，每秒一条，字段与 `stat` 对齐。
- 启动后 5 秒清空一次统计窗口，避免把模型加载、shader 编译、窗口创建的启动抖动算进稳态 p50/p95。
- `3d/main.cpp` 已接入 pass 计时点：model update、model render、hit-mask readback、region 更新、overlay 绘制、swap。

## 2. 实测

构建：`3d/whale3d-stage1-stats.exe`，1,374,208 B，SHA256 `E957BC3B7888A502A64B03D00C04685F9D1185DDE97220C605C35F1711B1BDEB`。  
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

## 3. 未完成

- `--headless --fixed-dt=1/60 --frames=N` 尚未接入。
- `test_headless_smoke.py` 尚未编写。
- 逐帧 trace/环形缓冲尚未落盘；当前是 1Hz 聚合 trace。
- `initLog()` 每次覆盖日志的问题尚未修。

## 4. 下一步

1. 给 `main` 增加 `--headless --fixed-dt=1/60 --frames=N`，隐藏窗口 + FBO 渲染，输出 summary JSON。
2. 写 `3d/tools/test_headless_smoke.py`，跑 60 帧 smoke，校验 trace schema 和 exit 0。
3. 处理 `initLog()` 覆盖问题：按启动时间分文件或追加 session 头。
