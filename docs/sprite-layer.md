# 2D 卡面 sprite 层：骨架与接线契约

日期：2026-11-27
状态：**代码骨架 + 临时链接检查完成，未接入运行中的 3D**。24 小时离屏浸泡的 `whale3d.exe` 未重建、未启动新窗口；原浸泡进程在 12:44 已提前结束，见 `docs/soak-24h.md` 的说明。

## 目标

在 3D 渲染循环里加一个最小屏幕空间卡面层：读 `assets/2d_bridge/manifest.json`，启动时上传 `atlas.png` 一次，每帧最多画一个 textured quad。它只做装饰，不参与命中区，不替换 3D 脸/身体，也不碰 2D PySide6 面板。

## 文件

- `3d/sprite.h`：`SpriteLayer` 公开接口。
- `3d/sprite.cpp`：manifest 解析、图集解码、GL 资源、quad 绘制。
- 依赖 `3d/third_party/json.hpp` 与 `stb_image.h`；`stb_image` 的实现仍在 `model.cpp`，所以最终链接必须带 `model.cpp`。
- `3d/sprite.cpp` 已加入 `3d/build.ps1` 的源码列表；因为没有 `main.cpp` 调用，临时链接产物不会改变现有 3D 行为。

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
- 纹理 UV 使用 `v = 1 - y/h` 手工翻转，避免 `stb_image` 行序与 GL 原点导致上下颠倒；未改全局 `stbi_set_flip_vertically_on_load`，不会影响模型贴图。

## 接线顺序（浸泡结束后）

1. `main.cpp` 在 `ui.init` / 模型加载之后调用 `sprite.init(base)`；失败只记日志，不阻塞 3D。
2. `EmotionBus::poll` 返回的 `frame.card` 非空时调用 `sprite.showCard(frame.card, frame.cardTtlMs)`；`cardTtlMs=0` 时不画，避免旧包残留。
3. 主循环 `sprite.update(dt)`；`draw` 放在现有的命中区 `glReadPixels` 采样之后、`SDL_GL_SwapWindow` 之前。
4. 需要单独测试 exe：`build.ps1 -OutFile build\whale3d_sprite_test.exe`，不要覆盖正在跑的 `3d\whale3d.exe`。
5. 首测用 `WHALE3D_CARD=expression/happy` 或本地 UDP 发 `action/wave`；先看卡面位置/朝向/透明度，再测 FPS 与私有字节。

## 边界

- 没有做卡面点击/拖拽；它画在命中区采样之后，天然不抢点击。
- 没有做多卡队列/动画；最新卡覆盖旧卡，过期隐藏，和 `CardArbiter` 的语义一致。
- 没有把卡面接到 3D 骨骼/材质；这是屏幕空间浮层，不是“2D 皮肤变 3D 服装”。
- 骨架只在 Windows + OpenGL 3.3 core 下设计；GL 入口点全部用 `SDL_GL_GetProcAddress` 加载，缺一个就 `init` 失败并返回错误，不会空指针调用。
- 当前编译检查产物 `build\sprite_proto.o` 被 `build/` 忽略，不是交付物。

## 编译检查

```powershell
$gxx = 'F:\WhaleGirlPet\.toolchains\w64devkit\w64devkit\bin\g++.exe'
$inc = 'F:\WhaleGirlPet\.toolchains\SDL3\SDL3-3.4.20\x86_64-w64-mingw32\include'
& $gxx -std=c++17 -Wall -Wextra -c -I3d "-I$inc" 3d\sprite.cpp -o build\sprite_proto.o
```

结果：`exit=0`，无 warning；对象 2,069,533 B。临时链接检查用 `3d\build.ps1 -OutFile build\whale3d_sprite_link_test.exe`，`exit=0`；产物 1,374,720 B，只验证链接，未启动、未替换 `3d\whale3d.exe`。链接产物在 `build/` 忽略范围内，不是交付物。

## 下一步实测项

- 接入后单卡 `expression/happy`、动作 `action/wave` 的可见帧。
- 开/关 sprite 的 FPS、CPU、私有字节；当前私有字节 97,849,344 B，加图集估算约 99.9 MB，需确认是否过 100 MB。
- 卡面与 3D 脸的遮挡关系；默认右下角，若挡住桌宠主体再调锚点/透明度。
- 多卡快速切换时是否闪烁；当前是单 quad 覆盖，无队列。
