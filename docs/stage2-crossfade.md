# 阶段 2：idle ↔ walk 真采样 crossfade

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：run `46135131492` success（build + 20 条动画 + 35 条卡队列 + headless 60）。  
构建：`3d/whale3d-stage2-crossfade.exe`，1,417,216 B，
SHA256 `F16D41AE2A141D27C6B8F5156D4133393FC492BC0F4E7A42D179F045958D8F65`。  
性质：测试构建，不替换生产 `3d/whale3d.exe`。

## 1. 实现了什么

- `Model` 增加 `previousClip`、`clipFadeElapsedMs`、`clipFadeDurationMs`；`setClip` 在 idle↔walk 真正切换时启动 fade，`nextClip` 改为复用 `setClip`。
- `updateOzz` 同时采样目标 clip 和上一个 clip，使用第二个 `SamplingJob::Context` 与 `ozzLocalsPrev` 缓冲。
- 在局部骨骼空间混合：translation/scale 用 `Lerp`，rotation 用 `NLerp`，再统一做 `LocalToModel`、pose offsets 和 spring bones。
- 默认 fade 180ms；`WHALE3D_CLIP_FADE_MS=0` 可关闭，负值按 0 处理。日志：
  - 开始：`clip fade: idle -> walk 180ms`
  - 结束：`clip fade end: walk`
- 不再只是状态机计算 `fadeInMs/fadeOutMs`，而是实际输出混合后的骨骼局部变换。

## 2. 验证

| 项 | 结果 |
|---|---|
| 构建 | `build.ps1` 成功，`-Wall -Wextra -Werror` 无错误 |
| 真实 W 切换 | `3d/tools/check_clip_crossfade.py` 通过；日志有 `idle -> walk`、`walk -> idle`，结果 `build/stage2-crossfade/crossfade-result.json` |
| fade 结束 | 日志 `clip fade end: walk`；说明 180ms 后走完混合路径 |
| headless 60 render | PASS，p50 1.81ms / p99 8.47ms / work 2.21ms |
| headless 600 no-render | PASS，exit 0 |
| 17 卡截图 | `build/stage2-crossfade-cards/` 捕获 17/17；状态 `needs_visual_review`，未把截图生成当成视觉通过 |
| 队列回归 | `build/stage2-crossfade-queue/queue-test.json` 6/6 通过 |
| 真实点击穿透 | `build/stage2-crossfade-click.json`：`ok:true`，卡面 `-1`、模型 `1`、目标 `clicks 0→1` |
| 真实拖拽 | `build/stage2-crossfade/drag-test.json`：`ok:true`，窗口 (1420,430)→(1510,475)，delta (90,45) |
| 90 秒快速 W | `build/stage2-crossfade-soak/crossfade-soak.json`：147 次 fade、无退出，CPU 单核 avg 31.93% / max 35.91% |
| 10 分钟 W 浸泡 | 进行中；完成后单独记录，不与 90 秒结论混写 |
| 进程 | 测试后无残留 |

## 3. 边界

- 只覆盖 `idle`/`walk` 两个真实 clip；`action_*`、`expression_*` 没有独立动画 clip，因此不会切 3D clip，只走卡面/状态机。
- 卡面 overlay 仍是硬切 + sprite 0.12s alpha；本轮没有做 overlay crossfade。
- `ShellUi` 设置里的 `setFace` 仍直接调用，face 不归 controller。
- 没有做逐帧视觉差异度量；本轮证明的是采样/混合路径和真实切换不崩，不是主观手感满分。
- 生产 exe、Release 资产、阶段 0/1 waiver 均未改。

## 4. 下一步

1. 等 action/expression 有真正动画资产后，把 `AnimationController` 的 fade 参数接到 clip crossfade。
2. 若要覆盖卡面，再做 overlay 双层纹理 crossfade，不要把它混进 clip 采样结论。
