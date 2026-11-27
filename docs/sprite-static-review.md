# sprite 层静态审查

日期：2026-11-27  
审查范围：`3d/sprite.h`、`3d/sprite.cpp`、`3d/main.cpp` 的 sprite 接线、`3d/shell_ui.h/.cpp` 的 region 扩展。  
方式：只读代码，不编译、不启动第二个 3D；生产 exe 和当前 24h 浸泡不受影响。

## 结论

当前接线可以继续跑 24h，不需要为了浸泡中途改代码。以下问题按优先级记录，建议等 24h 结束、可见验收时一起处理。

## P1：建议在可见验收前修

### 1. manifest 解析只保护了 JSON 语法，没有保护字段缺失

`loadAtlas` 只对 `file >> j` 做了异常捕获；后面的 `j.at("sheet_size")`、`j.at("cards")`、`entry.at("rect")` 仍可能抛 `out_of_range` / `type_error`。如果 manifest 被裁坏、字段改名或某个卡缺 `rect`，`SpriteLayer::init` 可能直接抛出未捕获异常，而不是返回 `false`。

建议：

- 用 `try/catch` 包住整个 manifest 解析和字段读取；
- 校验 `sheet_size` 是 2 个正整数、`cards` 是数组、每个 `id` 非空且 `rect` 是 4 个整数；
- 重复 `id` 报错，而不是静默覆盖。

### 2. `draw` 改动的 GL 状态没有完整恢复

当前 `draw` 会改：

- `GL_DEPTH_TEST`（禁用后强制启用）
- `GL_CULL_FACE`（保存后恢复）
- `GL_BLEND` / `glBlendFunc`
- 当前 program、VAO、active texture、2D texture binding

其中 depth test 是“无条件启用”，不是恢复原值；texture/program 也没有解绑。现在主循环的状态刚好匹配，所以没暴露；以后如果模型绘制前关闭深度或改用别的混合函数，会被 sprite 覆盖。

建议：

- 保存 `glIsEnabled(GL_DEPTH_TEST)`、`glIsEnabled(GL_BLEND)`、`glIsEnabled(GL_CULL_FACE)` 和当前 blend func；
- 绘制后按原值恢复；
- 或者把 sprite 绘制封装成明确的“状态契约”，由主循环统一设置。

## P2：可接受，但要知道

### 3. 卡面区域每 6 帧才扩一次 region

`main.cpp` 里 `regionFrame++ % 6 == 0` 才调用 `updateWindowRegion`。卡面刚出现时，最多约 5 帧可能被旧 region 裁掉；TTL 到期收缩也最多延迟 5 帧。当前 29 fps 下约 170 ms，肉眼可能看到一次轻微跳变。

这不是错误，但可见验收时应专门看“卡面出现第一帧”和“TTL 到期”的边界。

### 4. `lastRect` 过期后不会清零

`visible()` 为 false 时，`main.cpp` 用空 `PixelRect` 传给 region，所以功能上没问题；但 `lastRect()` 本身会保留最后一次卡面的值。后续如果有新调用方直接读 `lastRect()` 而不先看 `visible()`，会拿到过期矩形。

### 5. 纹理尺寸检查发生在上传之后

`glTexImage2D` 先按实际图片尺寸上传，然后才比较 `w/h` 与 manifest 的 `sheet_size`。尺寸不匹配时 `init` 会失败并 `clearGl`，不会泄漏；但错误日志只说 `atlas size mismatch`，没有给出实际尺寸和 manifest 尺寸，排障不够直接。

### 6. `glGetError` 只在 `WHALE3D_SPRITE_TRACE` 下检查

不开 trace 时，sprite 的 GL 错误不会出现在日志里。对生产环境这没问题，但如果 24h 浸泡期间出现偶发纹理/绘制错误，现有日志看不到。

## P3：代码清洁度

- `3d/sprite.h` 顶部注释还写着“它还没有拥有渲染循环”，实际 `main.cpp` 已经接线，注释过期。
- `cards` 使用 `unordered_map`，重复 id 会静默覆盖；manifest QA 目前没检查唯一性。
- `showCard` 的 TTL clamp 是 `0.2–10 s`，但 `main.cpp` 的环境变量只接受 `200–10000 ms`；两个入口范围一致，没问题。
- `draw` 的 `lastRect` 用 `pixelHeight - py - cardH` 计算 top-left，和 `ShellUi` 的 top-left 坐标一致；静态看没有上下翻转错误。

## P1 补丁草稿

2026-11-27 已在独立 worktree 准备 P1 补丁，未合入 `main`、未编译：

- worktree：`F:\WhaleGirlPet\build\worktrees\fix-sprite-parser`
- 分支：`fix/sprite-parser`
- commit：`ee747c1`（`fix(sprite): validate manifest fields and restore GL state`）
- 内容：`loadAtlas` 全段 `try/catch`、字段/长度/重复 id 校验、纹理尺寸检查前移；`draw` 保存并恢复 depth/cull/blend/program/VAO/active texture/2D texture binding。
- 等 24h 结束再编译验证，不覆盖当前 `3d\whale3d.exe`。

## 未覆盖的实测项

- 17 张卡里只有 `expression/happy`、`action/wave` 做过 3D 可见验收。
- 卡面坐标的真实 `WM_NCHITTEST` / 点击穿透没有单独采样。
- 多卡快速切换、卡面与模型遮挡、TTL 到期 region 收缩没有逐帧验收。
- 2D PyInstaller 冻结包尚未做一次“打包后启动”回归。

这些都应安排在 24h 浸泡结束之后，避免第二个 3D 实例或可见窗口操作干扰当前任务。
