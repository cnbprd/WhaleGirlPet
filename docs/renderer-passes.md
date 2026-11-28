# 渲染 pass 边界与 inspector（阶段 4）

阶段 4 的目标是把现有 OpenGL 调用从 `model.cpp` / `main.cpp` 的隐式顺序，收成可命名的 pass、可观测的耗时和只读 inspector。它不是完整 RHI/RDG，也不引入第二个渲染后端。

## 1. 代码边界

新增：

- `3d/renderer.h`：`IRenderer`、`GLRenderer`、`NullRenderer`；`RenderPass` 与 pass 的输入/输出声明。
- `3d/inspect_overlay.h/.cpp`：`--inspect` 调试侧栏。
- `3d/tools/compare_render_goldens.py`：对阶段 2 golden 卡面/区域做回归比较。

改造：

- `3d/main.cpp`：主循环插入 `beginFrame/endFrame` 和 `beginPass/endPass`；加入 `--inspect`、`--duration`。
- `3d/build.ps1`：加入 `inspect_overlay.cpp`。

`GLRenderer` 只负责 pass 计时和文本描述，`Model::draw`、`SpriteLayer::draw`、窗口 region 仍按原路径执行。`NullRenderer` 用于 headless/未来的无渲染测试。

## 2. 实际 pass 顺序

实际顺序与路线图的文字顺序有偏差：

```text
model -> hit mask -> sprite overlay -> region/UI-window update
```

原因：主窗口的点击 mask 必须只包含 3D 模型，不能包含 2D 卡面；卡面在独立的透明 overlay 窗口上绘制，所以 hit mask 必须在 sprite 之前读回。这个顺序不是“抄 UE”，而是当前双窗口结构的正确依赖顺序。

| pass | 入口 | 输入 | 输出 | 计时字段 |
|---|---|---|---|---|
| `model` | `model.draw(viewProj.m)` | view-projection、蒙皮/骨骼姿态 | 主窗口 color/depth back buffer | `renderUs` + pass timer |
| `hitmask` | `glReadPixels` 到 `hitMask` | 主窗口 color back buffer | `pw*ph*4` RGBA hit mask | `readbackUs` + pass timer |
| `sprite` | `sprite.draw`（主窗 fallback 或 overlay 窗口） | atlas、card rect、当前卡 id | 卡面像素；overlay 窗口一次 swap | `overlayUs`（overlay 路径） + pass timer |
| `region` | `ui.updateWindowRegion` / `setOverlayCardRegion` | hit mask alpha、card rect | 主窗/overlay 的输入 region | `regionUs` + pass timer |

`ShellUi` 是原生 Win32 托盘/设置窗口，不产生 GL draw call；因此没有单独的 GL `UI` pass。`region` 是窗口输入区域更新，不是 UI 绘制 pass。这一条是阶段 4 当前的边界，不是“已经迁移了 ShellUi 绘制”。

## 3. inspector

`--inspect` 启动一个 topmost、`WS_EX_NOACTIVATE`、`WM_NCHITTEST=HTTRANSPARENT` 的调试侧栏，位置在主窗左侧，显示：

```text
whale3d inspect  fps=...
state=... clip=... face=...
card=... emotion=...@...
passes model=... hitmask=...
sprite=... region=... frame=...
rss=...MB private=...MB
asset=...
```

它每 500ms 更新一次，只在 `--inspect` 时创建；默认路径没有额外窗口。实际截图见 `build/stage4-inspect-screen.png`（左侧黑色面板）。发送 `expression/happy` 卡后，侧栏显示 `card=expression/happy`、`emotion=happy@0.80`、`sprite=0.23ms`，截图 `build/stage4-inspect-card2.png`。

实现选择：早期使用 `WS_EX_LAYERED` + color key 的 GDI 路径，实测窗口存在但文字不显示；改为不透明 topmost 侧栏，避免 layered GDI 的不可见问题。它仍然是调试控件，不是生产 UI。侧栏覆盖主窗左侧的桌面内容，但 `WM_NCHITTEST` 返回 `HTTRANSPARENT`，鼠标点击不会挡住下层窗口。

## 4. 构建

```text
F:\WhaleGirlPet\build\whale3d-stage4-passes.exe
1,463,296 B
SHA256 EBAEDA8E3DF02A543E2820031C5C32497F6A100D90FEE7B6B11B8EFAB7B59B2B
```

`3d\whale3d-stage4-passes.exe` 与 build 副本同 hash。

## 5. 实测

### 5.1 可见窗口 240 秒

命令：`whale3d-stage4-passes.exe --duration=240`，日志 `build\stage4-window.log`，汇总 `build\stage4-window-summary.json`。

- 231 个 1 秒采样（跳过前 5 秒预热）：平均 FPS 27.98，最高 29.0，最低 21.4。
- 阶段 1 基线平均 FPS 21.79；平均不低于基线，满足阶段 4 的“FPS 不低于阶段 1 基线”。
- 最低 21.4 是桌面调度/遮挡造成的瞬时掉帧，接近基线但低于基线；本轮结论按平均值成立，不把它写成“全程稳定 28 FPS”。
- pass 平均：model 0.01ms、hitmask 1.06ms、sprite 0.00ms（无卡面时）、region 0.55ms；frame_last 平均 2.20ms（不含 swap 和桌面合成）。
- 没有用 `perf.writeSummary` 的 p50/p99 作为本轮结论；阶段 4 只对 FPS 平均与 pass 耗时下结论。

### 5.2 17 卡与 golden

`python 3d\tools\check_cards_visible.py --exe 3d\whale3d-stage4-passes.exe --out-dir build\stage4-cards`：

- 17/17 卡抓到，`build\stage4-cards\2d-card-visible-qa.json`，状态仍是 `needs_visual_review`。
- contact sheet：`build\stage4-cards\_3d_visible_17_cards.png`。
- 对照阶段 2 `build\stage2-crossfade-cards`：17 张卡的 `client_rect` **全部完全相同**，卡面 crop 尺寸也全部相同；逐卡 `mean_abs_diff` 最大 8.589（sleep 卡因背景文字不同），其余 1.8–6.8。
- 自动检查报告 `docs\render-golden.json`：`ok=true`，7 项 check 全过（client 420×620、17 卡、rects exact、crop sizes exact、crop diff bounded、透明角非纯黑、点击穿透）。

### 5.3 点击区与拖拽

`check_click_through.py --exe 3d\whale3d-stage4-passes.exe --card action/wave --click`：

- `ok=true`
- `card_hit_test=-1`（HTTRANSPARENT）
- `model_hit_test=1`（HTCLIENT）
- 目标窗口 `received=true`
- 结果 `build\stage4-click.json`

`check_drag.py --exe 3d\whale3d-stage4-passes.exe`：`ok=true`，start `(1420,430)`、end `(1508,473)`、delta `(88,43)`，目标 `(100,50)`、tolerance 20；结果 `build\stage4-drag.json`。

### 5.4 headless 与 content

- `--headless --frames=60 --no-render` 退出 0，`build\stage4-headless.log`。
- 把同一 exe 放进 `build\package-content-test`（带 `whale3d-content-package-v1` 的 `content.json`），`--headless --frames=60 --no-render` 退出 0，日志 `Content manifest: verified package hashes`（`build\stage4-package.log`）。

## 6. 未完成/边界

- `GLRenderer` 不是资源生命周期管理器：没有 texture/buffer/shader 的创建/销毁所有权，也没有 GPU query；只是 pass 计时和接口壳。
- sprite pass 在 overlay 模式下含一次 overlay swap；它和主窗 swap、桌面合成不能直接相加成帧时间。
- 没有 GL UI pass；`ShellUi` 仍是原生 Win32。
- inspector 是不透明侧栏，不是覆盖在宠物身上的透明浮层；只在 `--inspect` 下存在。
- golden 比较不覆盖“主窗整图逐像素”：窗口透明，桌面背景属于截图内容，逐像素比较不稳定；已固定的是 client 尺寸、17 卡 id/rect、crop 尺寸、crop 差异上界、透明角 sanity、点击穿透。
- 240 秒不是阶段 1 的 10 分钟；没有把 240 秒结果写成 10 分钟结论。
- 生产 `3d\whale3d.exe` 与已发布 v3.2.0-sprite 资产未替换；阶段 4 产物是内部候选，不发 Release。

## 7. 复现命令

```powershell
powershell -ExecutionPolicy Bypass -File 3d\build.ps1 -OutFile build\whale3d-stage4-passes.exe
.\3d\whale3d-stage4-passes.exe --inspect
.\3d\whale3d-stage4-passes.exe --duration=240
python 3d\tools\check_cards_visible.py --exe 3d\whale3d-stage4-passes.exe --out-dir build\stage4-cards
python 3d\tools\compare_render_goldens.py --current build\stage4-cards --golden build\stage2-crossfade-cards --out docs\render-golden.json
C:\Users\yangmengke\AppData\Local\Programs\Python\Python314\python.exe 3d\tools\check_click_through.py --exe 3d\whale3d-stage4-passes.exe --card action/wave --click --out build\stage4-click.json
python 3d\tools\check_drag.py --exe 3d\whale3d-stage4-passes.exe --out build\stage4-drag.json
```

