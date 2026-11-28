# 2D 卡面 sprite 层：接线与验收

日期：2026-11-28  
状态：**已接入 3D，24h 浸泡通过，17/17 可见，卡面点击穿透通过**

## 目标

在 3D 渲染循环外挂一层屏幕空间卡面：读 `assets/2d_bridge/manifest.json`，启动时上传 `atlas.png` 一次，每帧最多画一个 textured quad。卡面不替换 3D 脸/身体，也不参与主窗口的点击 mask。

## 当前架构

- **主 3D 窗口**：只绘制模型；`ShellUi::updateWindowRegion` 只按模型 alpha 生成 region，不再把卡面矩形并进主窗口 region。
- **卡面 overlay 窗口**：单独一个透明、无边框、置顶、不可聚焦的 SDL/OpenGL 临时窗口，尺寸与主窗口一致；它只负责卡面 quad。
- overlay 的 Win32 region 被裁成卡面矩形，因此它只覆盖卡面，不会挡住模型区域的鼠标。
- overlay 收到卡面点击后，用 `GetWindow(GW_HWNDNEXT)` 向下找第一个真正可点的窗口，把 `WM_LBUTTONDOWN/UP`、右键/中键事件转发过去；这样主窗口不需要把卡面放回 region，也不会用 `HTTRANSPARENT` 去赌跨进程投递。
- 如果第二窗口/第二 GL context 创建失败，代码回退到旧路径：卡面画在主窗口，主窗口 region 额外扩卡面矩形。

## 文件

- `3d/sprite.h`：`SpriteLayer`、`PixelRect` 公开接口。
- `3d/sprite.cpp`：P1 `sprite_manifest` 解析、图集解码、GL 资源、quad 绘制、`uUvRect` 子图采样。
- `3d/main.cpp`：overlay 窗口/context、卡面 region、点击转发、显示/隐藏/跟随主窗口。
- `3d/shell_ui.h/.cpp`：`updateWindowRegion` 仍保留 4 个额外边界参数；overlay 可用时传 0，回退路径才传卡面矩形。
- `3d/build.ps1` 已把 `sprite.cpp`、`sprite_manifest.cpp` 加入源码列表。

## 接口

```cpp
SpriteLayer sprite;
sprite.init(basePath);          // overlay GL context current 之后
sprite.showCard("expression/happy", 1800.0f);
sprite.update(dt);
sprite.draw(pixelW, pixelH);    // overlay context current 时
```

- `showCard` 只接受 manifest 里的 id；未知 id 返回 `false`。
- `ttlMs` 钳制 `200..10000`；过期后 `visible()` 为 `false`，overlay 隐藏。
- `draw` 画在右下角，高度 `min(220, 0.36 * 窗口高)`，宽高比按 manifest rect 计算。
- 图集用 `stb_image` 解码后上传为 GL 纹理；`uUvRect` 把 quad 的 `aUv` 映射到卡面子矩形。

## 接线顺序

1. 主窗口 GL context 创建后，初始化模型和 `ShellUi`。
2. 解析 `spriteBase`：先找 `base + assets/2d_bridge/manifest.json`，找不到再找 `base + ../assets/2d_bridge/manifest.json`。
3. 创建隐藏的 overlay 窗口；设置置顶、不可聚焦、tool window；获取 HWND，设置 Win32 region 和输入转发 WndProc。
4. 在 overlay GL context 上 `sprite.init`；成功后切回主 context。
5. `WHALE3D_CARD` / UDP `card` 只调用 `sprite.showCard`；overlay 根据 `sprite.visible()` 显示/隐藏。
6. 每帧把主窗口位置同步给 overlay；overlay 绘制前设置卡面 region，绘制后 swap。
7. 结束时先切到 overlay context 执行 `sprite.shutdown()`，再销毁 overlay context/window。

## 实测结果

- **24h 浸泡**：`soak_24h_sprite_task` gate `exit 0`、`valid=True`、`alive_after_soak=True`；证据见 `docs/soak-final-2026-11-28.md`。
- **17 卡可见**：17/17 通过，总览 `docs/_3d_visible_17_cards.png`，逐卡证据 `docs/2d-card-visible-qa.json`、`docs/2d-card-visible-qa.md`。
- **点击穿透**：`docs/click-through-result.json` 中 `card_hit_test=-1`、`model_hit_test=1`、`target.received=true`；脚本返回 `exit 0`。
- **overlay 可见性**：`Sprite draw card=expression/happy` 日志确认 overlay context 绘制；17 卡截图确认卡面不再被主窗口 region 裁掉。

## 边界

- overlay 的输入转发主要覆盖左键/右键/中键按下和抬起；鼠标 hover 不保证逐像素转发到下层应用。
- 点击测试为了保证目标窗口在 3D 下方，测试目标临时置顶，再把 3D 主窗口和卡面 overlay 重新提到目标上方；这是为了排除截图工具/浏览器等第三方窗口抢点击，不改变产品点击路径。
- 回退路径仍保留旧行为：卡面画在主窗口，主窗口 region 包含卡面；这条路径没有 overlay 的点击转发能力。
- 只支持 Windows + OpenGL 3.3 core；overlay 需要第二个 GL context，创建失败会回退。
- 发布包必须把 `assets/2d_bridge/` 放在 exe 同级。
