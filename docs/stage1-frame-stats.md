# 阶段 1 进展：FrameStats 与 trace

日期：2026-11-28  
分支：`feat/v3.3-observe`  
状态：**阶段 1 已按 1 项条件 waiver 退出：CPU 10 分钟已实测；CI 仍只有 no-GL smoke，GPU runner 转入阶段 4/基础设施。阶段 2 首刀已落地，待集成。**

## 1. 已实现

- `3d/perf_stats.h`：头文件实现，不新增 `.cpp`，不改变 `build.ps1` 源文件列表。
- `WHALE3D_STAT=1`：每秒输出一行 `stat`，含：
  - FPS、interval p50/p95/p99、work、hitch、RSS/private；
  - update / render / readback / region / overlay / swap 的均值；
  - 当前 `clip` / `face`。
- `WHALE3D_TRACE=<path>`：追加 JSONL，每秒一条，字段与 `stat` 对齐。
- `WHALE3D_TRACE_HITCH_MS=<ms>`：超过阈值的单帧写成 `{"event":"hitch",...}`，带帧号和 pass 耗时，用来定位单帧 hitch。
- 启动后 5 秒清空一次统计窗口，避免把模型加载、shader 编译、窗口创建的启动抖动算进稳态 p50/p95。
- `WHALE3D_KEEP_AWAKE=1`：统计浸泡时阻止显示空闲，避免把系统降频误判成引擎退步。
- `3d/main.cpp` 已接入 pass 计时点：model update、model render、hit-mask readback、region 更新、overlay 绘制、swap。
- 默认日志改为追加并写 session 头；`WHALE3D_LOG` 覆盖时仍按测试需要覆盖。

## 2. 实测

构建：`3d/whale3d-headless.exe` 为 1,381,888 B，SHA256 `CEA67348C99905EC6EE9626ECA20FB99C4E32374431CE5C0F742AB152013D9CF`。
环境：GTX 1060 6GB，驱动 582.78，OpenGL 3.3.0。

### 2.1 无卡面、15 秒

| 指标 | 值 |
|---|---|
| FPS | 28.6–28.8 |
| interval p50 | 34.19–34.25 ms |
| p95 | 37.99–38.38 ms |
| p99 | 46.52–47.57 ms |
| work | 1.31–1.47 ms |
| update | 0.01–0.02 ms |
| render | 0.01 ms |
| readback | 0.60–0.73 ms |
| region | 0.47–0.59 ms |
| overlay | 0.00 ms |
| swap | 0.07–0.10 ms |
| RSS / private | 70.9–71.1 MB / 112.7 MB |
| hitch | 0 |

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

当前构建的 1Hz trace 还带 `rss_mb`、`private_mb`、`clip`、`face`、`card`。设置 `WHALE3D_TRACE_HITCH_MS=45` 时，超阈值帧会额外写：

```json
{"event":"hitch","frame":11892,"interval_ms":49.70,"work_ms":102.78,"update_ms":0.01,"render_ms":0.02,"readback_ms":97.53,"region_ms":0.00,"overlay_ms":0.00,"swap_ms":0.63}
```

## 2.4 10 分钟基线

完整结果见 `docs/stage1-baseline-10min.md`。摘要：600 个 1Hz 样本，FPS avg 27.86 / max 29.72，p50 avg 34.78 ms，p95 avg 39.18 ms，p99 avg 45.18 ms，RSS 70.1–73.0 MB，private 112.2–113.3 MB；190 条 hitch 事件（去启动前 160 帧后 186 条），最大单帧 interval 885 ms、最大 readback 97.5 ms。没有 crash 或持续内存增长。

## 2.5 CPU 10 分钟

完整结果见 `docs/stage1-cpu-10min.md`。两次 10 分钟进程采样，取 30 秒后的 58 个稳态样本：

| Run | CPU 单核 avg | p50 | p95 | RSS | private |
|---|---:|---:|---:|---:|---:|
| 无 keep-awake | 29.61% | 29.31% | 34.35% | 70.94–73.00 MB | 113.2–114.3 MB |
| keep-awake | 26.30% | 26.37% | 28.06% | 69.75–70.58 MB | 112.7–114.1 MB |

CPU 没有接近单核跑满，也没有单调上涨。两次 run 的 FPS 被当前桌面合成压到 21–22，不作为帧时间基线；帧时间仍以 2.4 的 27.86 FPS / p50 34.78 ms 为准。

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

## 4. 未完成 / waiver

- **GPU CI waiver**：CI 仍只有 no-GL smoke；GPU 的 `--headless` render 路径没有 Windows GPU runner。本机已跑 60/600 帧 render 路径，作为替代证据；该项转入阶段 4/基础设施，不冒充已验证。
- 全量逐帧 trace 没做；当前是 1Hz 摘要 + hitch 事件，已足够定位单帧异常，不再为“逐帧”而逐帧。

## 5. 退出记录与下一步

1. **阶段 1 条件退出**：CPU 10 分钟实测完成；60/600 帧、本机 GPU render、CI no-GL smoke、10 分钟帧时间基线均通过。唯一未闭合项是 GPU CI runner，按 waiver 记录。
2. **阶段 2 两轮集成已落地**：`AnimationController` + 20 条夹具 + `CardQueue` 35 条夹具 + `main.cpp` base/action 门禁 + `EmotionBus::pollAll`；17 卡可见验收通过；真实点击穿透和拖拽已过。idle 10 分钟 FPS 27.95 / p50 34.62ms / p99 48.36ms，接近平均基线；历史 CPU 比 26.30% 高 6.97pp，但同机 A/B 后 stage1-stats 31.52% vs queue 33.27%，只 +1.75pp；队列 FPS/p99 更好但 swap 路径不同，不能直接比较。真实 crossfade 和 #70 聊天未验。详见 `docs/stage2-queue.md`。
3. **下一步**：先决定是否接受 idle p99/CPU 回归；#70 剩余聊天触发（3D shell 无聊天入口，待确认范围）；crossfade 暂缓。
4. 旧任务 #70 的真实窗口手感验收仍然保留，作为阶段 2 退出条件，不因状态机单测通过而提前关闭。
