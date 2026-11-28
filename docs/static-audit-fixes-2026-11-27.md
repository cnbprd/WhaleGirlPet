# 静态审计修复（2026-11-27）

状态：集成分支 `integrate/sprite-parser-static-20261127`，基于 `fix/sprite-parser` 合入 `fix/static-audit-20261127`；worktree `build/worktrees/integrate-sprite-parser-static`。
已在 24 小时浸泡结束后完成编译、P1 17 条夹具、17 卡可见和真实点击验收；未合入 `main`。

## 修复项

1. `3d/sprite.cpp`
   - 增加 `ready` 状态，只有 `init()` 完整成功后才允许 `showCard()` / `draw()` / `visible()`。
   - `loadAtlas()` 使用 P1 的 `sprite_manifest::parseJson()` / `validateAtlasSize()`，不再重复内联解析；图集尺寸校验通过后才提交 cards。
   - 初始化失败时清理 cards/current/ttl/age/lastRect，避免“init 返回 false 但 showCard 仍成功”。

2. `3d/main.cpp`
   - 用 `spriteReady` 门控环境变量卡面和 UDP 卡面，初始化失败后不再调用 `showCard()`。
   - 增加 `Local\WhaleGirlPet3D` 命名互斥量，阻止同用户会话内直接多开；`--relaunch` 辅助进程仍先于互斥量处理。
   - 卡面改为独立透明置顶 overlay 窗口：主窗口 region 只保留模型像素，overlay region 裁成卡面矩形；overlay 将卡面点击转发给下方窗口，避免主窗口 `HTTRANSPARENT` 跨进程失效。
   - overlay 创建/第二 GL context 失败时回退到旧的主窗口卡面路径。

3. `3d/shell_ui.cpp`
   - 全透明帧 `runs.empty()` 时显式安装空 region，避免保留上一帧的窗口形状和可点击区域。
   - 托盘图标创建失败改为“降级继续”：窗口子类化和命中测试仍有效，`TaskbarCreated` 后续可再尝试加图标；不再返回 false 留下半初始化 UI。

4. `3d/model.cpp`
   - `Model::update()` 和 `Model::draw()` 增加 `impl_` 空指针保护，`shutdown()` 后调用不会解引用空指针。

## 验证

- `git diff --check`：代码文件通过。
- 集成分支编译：通过；临时输出 `build/whale3d-overlay-test.exe`，未覆盖生产 `3d/whale3d.exe`。
- P1 夹具：`17/17 passed`。
- 17 卡可见：17/17 通过，证据 `docs/2d-card-visible-qa.json`、`docs/2d-card-visible-qa.md`。
- 点击穿透：`card_hit_test=-1`、`model_hit_test=1`、`target.received=true`，`docs/click-through-result.json`，脚本 `exit 0`。
- 安装器/Release 资产重算尚未执行。

## 未纳入本次补丁

- `EmotionBus::poll()` 连续多包只保留最后一包的设计，需先确认 2D 侧是否允许合并。
- Sprite 绘制后的完整 GL 状态保存/恢复，已由本分支继承的 `fix/sprite-parser` 补丁处理。
- 启动日志覆盖、全窗 `glReadPixels` 性能、高 DPI 坐标映射，留待浸泡结束后的实测/优化。
