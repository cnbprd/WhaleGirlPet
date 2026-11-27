# 2D 卡面 sprite 层：接线与验收

日期：2026-11-27
状态：**已接入 3D 主循环，并通过可见帧验收**。`3d/whale3d.exe` 已重建为带 sprite 的 1,377,792 B 版本；临时 exe 只用于调试时保留。24 小时离屏浸泡在 12:44 提前结束，未形成 24h 结论，见 `docs/soak-24h.md`。

## 目标

在 3D 渲染循环里加一个最小屏幕空间卡面层：读 `assets/2d_bridge/manifest.json`，启动时上传 `atlas.png` 一次，每帧最多画一个 textured quad。它只做装饰，不参与命中区，不替换 3D 脸/身体，也不碰 2D PySide6 面板。

## 文件

- `3d/sprite.h`：`SpriteLayer`、`PixelRect` 公开接口。
- `3d/sprite.cpp`：manifest 解析、图集解码、GL 资源、quad 绘制、`uUvRect` 子图采样。
- `3d/main.cpp`：初始化、UDP `card` 接线、每帧 `update/draw`、窗口 region 扩展。
- `3d/shell_ui.h/.cpp`：`updateWindowRegion` 的 4 个可选额外边界；卡面只扩展 Win32 region，不进入点击 mask。
- `3d/build.ps1` 已把 `sprite.cpp` 加入源码列表；`3d/tools/emotion_longrun.py` 支持 `WHALE3D_EXE`，并可发 `WHALE3D_LONGRUN_CARD` 做协议验收。

## 接口

```cpp
SpriteLayer sprite;
sprite.init(basePath);          // GL context current 之后
sprite.showCard("expression/happy", 1800.0f);
sprite.update(dt);
sprite.draw(pixelW, pixelH);    // 命中区 glReadPixels 之后
```

- `showCard` 只接受 manifest 里的 id；未知 id 返回 `false`，不会打开任何路径。
- `ttlMs` 钳制 `200..10000`；过期后 `visible()` 为 `false`。
- `draw` 画在右下角，高度 `min(220, 0.36 * 窗口高)`，宽高比按 manifest rect 计算；首尾 120 ms 淡入淡出。
- 图集用 `stb_image` 解码后上传为 GL 纹理；`uUvRect` 把 quad 的 `aUv` 映射到卡面子矩形。纹理坐标约定为：`v0 = y / sheetH`（图集顶部），`v1 = (y + h) / sheetH`（图集底部），绘制时以 `v1` 为底、`v0 - v1` 为负向步长，避免上下颠倒。
- 绘制前临时 `glDisable(GL_CULL_FACE)`，绘制后恢复原状态；这修复了模型遗留 culling 导致 quad 少一个三角形的问题。

## 接线顺序（已完成）

1. `main.cpp` 在 `ui.setHitTest` 之后初始化 `SpriteLayer`；先找 `base + assets/2d_bridge/manifest.json`，找不到再找 `base + ../assets/2d_bridge/manifest.json`，因此 `3d\whale3d.exe` 与打包目录都能读到图集。
2. `EmotionBus::poll` 返回的 `frame.card` 非空且 `cardTtlMs > 0` 时调用 `sprite.showCard(frame.card, frame.cardTtlMs)`；未知 id 只记 `Sprite card rejected`。
3. 主循环 `sprite.update(dt)`，`dt = clamp(t - lastT, 0, 0.1)`。
4. `sprite.draw(pw, ph)` 放在模型绘制和命中区 `glReadPixels` 采样之后、`SDL_GL_SwapWindow` 之前。
5. 把 `sprite.lastRect()` 作为额外矩形传给 `ui.updateWindowRegion`，让卡面不被 Win32 region 裁掉；该矩形不进 `hitTest`，卡面区域仍然点击穿透。
6. 结束顺序为 `sprite.shutdown()` → `ui.shutdown()` → `emotionBus.stop()` → `model.shutdown()` → 销毁 GL context。

## 实测结果

- 强制卡面：`WHALE3D_CARD=expression/happy`，3–4 秒可见运行，截图 `docs/_3d_longrun_sprite_clean_mid.png`，卡面完整、正向、位于右下角。
- 真实 UDP：`WHALE3D_LONGRUN_CARD=action/wave`，`action/wave` 被 `SpriteLayer` 接收并绘制；日志 `Sprite draw card=action/wave active=1`，截图 `docs/_3d_longrun_sprite_action_mid.png`。
- 真实 2D 端 `app.asset_bridge.AssetBridge`：读取 17 张卡，`bridge.action('wave', 2600)` 返回 True，3D 日志 `source=P_2D card=action/wave`、`Sprite card: action/wave ttl=2600ms`；截图 `docs/_3d_asset_bridge_action.png` 可见 wave 卡面。
- 独立打包目录：`build/package-sprite` 内带 `assets/2d_bridge`，启动日志 `Sprite layer: ready (...\assets/2d_bridge)`，FPS 27.9–29.7，截图 `docs/_3d_longrun_sprite_package_mid.png`。
- 从新 ZIP 解压到干净目录后再次启动：`Sprite layer: ready (...\assets/2d_bridge)`，强制 `expression/happy` 与 UDP `action/wave` 都可见；`action/wave` 的 TTL 2.6 s 到期后最终帧恢复无卡面，说明 TTL 和 window region 收缩正常。
- 未开卡面时窗口 region 仍只覆盖模型；开卡面时只额外扩出卡面矩形，点击 mask 不变。
- 调试开关 `WHALE3D_SPRITE_SOLID`、`WHALE3D_SPRITE_OPAQUE`、`WHALE3D_SPRITE_NO_REGION` 已从产品代码移除；只保留 `WHALE3D_SPRITE_TRACE` 做首帧 rect 日志，以及 `WHALE3D_CARD` / `WHALE3D_CARD_TTL` 作为开发期强制卡面。

## 边界

- 没有做卡面点击/拖拽；它画在命中区采样之后，天然不抢点击。
- 没有做多卡队列/动画；最新卡覆盖旧卡，过期隐藏，和 `CardArbiter` 的语义一致。
- 没有把卡面接到 3D 骨骼/材质；这是屏幕空间浮层，不是“2D 皮肤变 3D 服装”。
- 只支持 Windows + OpenGL 3.3 core；GL 入口点全部用 `SDL_GL_GetProcAddress` 加载，缺一个就 `init` 失败并返回错误。
- 发布包必须把 `assets/2d_bridge/` 放在 exe 同级；`3d/build.ps1` 只编译 exe，打包脚本负责复制图集。

## 下一步

- 24 小时真浸泡仍未完成；当前约 8h26m 的旧 session 已结束，重启前需要决定是否用新 exe。
- 2D PyInstaller 包需要把 `assets/2d_bridge` 加进 `WhaleGirlPet.spec`，否则冻结后的 2D 端可能拿不到 manifest。
- 多卡快速切换、TTL 过期后的 region 收缩、卡面与模型遮挡关系仍需再做一轮可见目检。
