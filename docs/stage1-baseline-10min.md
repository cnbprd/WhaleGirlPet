# 阶段 1 基线：10 分钟统计浸泡

日期：2026-11-28  
构建：`3d/whale3d-headless.exe`，1,381,376 B，SHA256 `CC7FAAB4027C38C9DD482F74FCD447D93581978C74996FA577453D10DC5A38C1`。该轮是加入 `clip/face` context 字段前的构建；当前 exe `CEA673...` 的 10 分钟 CPU run 见 `docs/stage1-cpu-10min.md`。  
环境：GTX 1060 6GB / 582.78 / OpenGL 3.3.0；无卡面；`WHALE3D_STAT=1`、`WHALE3D_TRACE=<path>`、`WHALE3D_TRACE_HITCH_MS=45`、`WHALE3D_KEEP_AWAKE=1`。

## 1. 结果

| 指标 | 值 |
|---|---|
| 墙钟 | 610,044 ms（约 10 分 10 秒） |
| 1Hz 样本 | 600；5 秒后 596 |
| FPS | avg 27.86 / max 29.72 / min 4.94（单次异常窗口） |
| interval p50 | avg 34.78 ms（34.13–35.60） |
| p95 | avg 39.18 ms（37.62–42.51） |
| p99 | avg 45.18 ms（38.53–71.69） |
| work | 1.3–2.6 ms |
| readback | 约 1.8 ms |
| swap | 0.07 ms |
| RSS | 70.1–73.0 MB |
| private | 112.2–113.3 MB |
| 进程 | 结束时 alive，exit 0 |

RSS / private 在 10 分钟内基本平稳，没有看到持续增长。

## 2. Hitch 事件

`WHALE3D_TRACE_HITCH_MS=45` 下共写出 190 条 hitch 事件；去掉启动前 160 帧后 186 条。

- 48 条 hitch 的 `readback_ms > 5`；最大 readback 97.53 ms（frame 11892），对应 work 102.78 ms。
- 还有 4 条长 interval（275–885 ms），但 work 仅约 1 ms，更像桌面/窗口被系统挂起或切换，不是引擎工作导致的。
- 这些事件已经能定位到具体帧号和 pass；Stage 1 的“单帧 hitch 可定位”目标达到。

## 3. 与 `v3.2.0-sprite` 基线对比

- 基线 FPS 28.3–29.0；本机 10 分钟 avg 27.86，低约 0.5–1 FPS，属于统计构建/环境噪声范围，不是 P0。
- 基线 private 约 97.8–98.2 MB（PowerShell 计数）；本次 `PerfStats` 的 `PrivateUsage` 约 112–113 MB，口径不同，不能直接相减；关键是 10 分钟内平稳。
- 没有 crash、没有持续内存增长；60/600 帧 headless smoke 和 CI no-GL smoke 均通过。
- CPU 10 分钟两轮：无 keep-awake 29.61% 单核、keep-awake 26.30% 单核；见 `docs/stage1-cpu-10min.md`。

## 4. 环境备注

第一次 10 分钟测试没有开 `WHALE3D_KEEP_AWAKE`，后段出现 21–22 FPS、swap 10–11 ms、p50 45.6 ms；开启 `ES_DISPLAY_REQUIRED` 后同样的 10 分钟保持 27.8–28.8 FPS、swap 0.07 ms。前者是显示空闲/桌面合成干扰，不作为引擎基线。

补充（同日 CPU 采样轮）：同一构建再开 keep-awake 跑 10 分钟，仍有窗口被桌面合成压到 21–22 FPS、swap 约 10 ms。说明 keep-awake 只能挡住“显示空闲”这一条路径，不能消除所有桌面合成干扰；CPU 数据仍有效（见 `docs/stage1-cpu-10min.md`），但帧时间基线只在当时那轮清扫环境成立，不能跨环境无条件复现。

## 5. 证据

- `build/stats-10min-keepawake.log`
- `build/stats-10min-keepawake-trace.jsonl`（600 条 1Hz + 190 条 hitch）
- `build/headless-smoke/headless-60-*`、`headless-600-*`
