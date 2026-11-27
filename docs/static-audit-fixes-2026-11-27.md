# 静态审计修复（2026-11-27）

状态：集成分支 `integrate/sprite-parser-static-20261127`，基于 `fix/sprite-parser` 合入 `fix/static-audit-20261127`；worktree `build/worktrees/integrate-sprite-parser-static`。
未编译、未启动第二个 3D、未合入 `main`；24 小时浸泡 `WhaleGirlSoak24hSprite`（PID 7816）未受影响。

## 修复项

1. `3d/sprite.cpp`
   - 增加 `ready` 状态，只有 `init()` 完整成功后才允许 `showCard()` / `draw()` / `visible()`。
   - `loadAtlas()` 使用 P1 的 `sprite_manifest::parseJson()` / `validateAtlasSize()`，不再重复内联解析；图集尺寸校验通过后才提交 cards。
   - 初始化失败时清理 cards/current/ttl/age/lastRect，避免“init 返回 false 但 showCard 仍成功”。

2. `3d/main.cpp`
   - 用 `spriteReady` 门控环境变量卡面和 UDP 卡面，初始化失败后不再调用 `showCard()`。
   - 增加 `Local\WhaleGirlPet3D` 命名互斥量，阻止同用户会话内直接多开；`--relaunch` 辅助进程仍先于互斥量处理。

3. `3d/shell_ui.cpp`
   - 全透明帧 `runs.empty()` 时显式安装空 region，避免保留上一帧的窗口形状和可点击区域。
   - 托盘图标创建失败改为“降级继续”：窗口子类化和命中测试仍有效，`TaskbarCreated` 后续可再尝试加图标；不再返回 false 留下半初始化 UI。

4. `3d/model.cpp`
   - `Model::update()` 和 `Model::draw()` 增加 `impl_` 空指针保护，`shutdown()` 后调用不会解引用空指针。

## 验证

- `git diff --check`：通过。
- 静态路径复核：通过。
- 未执行 C++ 编译、未运行 GL、未运行 17 卡截图、未运行安装器。
- 运行时验证统一留到 24 小时浸泡结束后的 `docs/post-soak-runbook.md` 流程。

## 未纳入本次补丁

- `EmotionBus::poll()` 连续多包只保留最后一包的设计，需先确认 2D 侧是否允许合并。
- Sprite 绘制后的完整 GL 状态保存/恢复，已由本分支继承的 `fix/sprite-parser` 补丁处理。
- 启动日志覆盖、全窗 `glReadPixels` 性能、高 DPI 坐标映射，留待浸泡结束后的实测/优化。
