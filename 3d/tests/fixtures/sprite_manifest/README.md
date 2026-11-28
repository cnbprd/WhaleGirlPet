# P1 sprite manifest fixture cases

用途：给 `fix/sprite-parser` 的 `loadAtlas` 坏 manifest 校验准备回归输入。  
当前只准备输入，不编译、不启动 3D、不替换生产 `manifest.json`。  
实现代码已落在分支：`3d/sprite_manifest.*`、`3d/tests/test_sprite_manifest.cpp`，尚未编译。

## 文件

- `cases.json`：17 个 case，包含 1 个成功控制组和 16 个坏 manifest。
- `3d/tools/lint_sprite_manifest_fixtures.py`：只检查夹具表结构，不执行 C++。

## 解析语义

P1 分支 `loadAtlas` 的错误顺序：

1. `sheet_size` 必须是 2 个整数；否则 `sheet_size must be two integers`
2. 宽高必须为正；否则 `sheet_size must be positive`
3. `cards` 必须是非空数组；否则 `cards must be a non-empty array`
4. 空 id → `empty card id`
5. 重复 id → `duplicate card id: <id>`
6. rect 必须是 4 个整数；否则 `card rect must be four integers: <id>`
7. rect 越界 → `card outside atlas: <id>`
8. `sheet` 为空 → `sheet path missing`
9. atlas 实际尺寸不等于 manifest → `atlas size mismatch: actual WxH, manifest WxH`
10. 缺字段、类型错误、JSON 语法错误都落在 `manifest parse: ...`

`cases.json` 的 `expect.error` 是精确匹配，`expect.error_prefix` 是前缀匹配。

## 浸泡结束后怎么用

1. 在 `fix/sprite-parser` 编译临时测试 exe 或 harness，不覆盖生产 `3d\whale3d.exe`。
2. 对每个 case 建临时 assetBase：
   - `assets/2d_bridge/manifest.json`：写 `manifest` 或 `raw_manifest`；
   - `assets/2d_bridge/atlas.png`：复制生产图集（1024×512）。
3. 调 `SpriteLayer::init(tempBase)` 或等价的纯解析入口，比对 `error()` 与 `expect`。
4. `valid_minimal` 必须成功；其余 16 个必须失败，错误精确/前缀符合表。

当前 `loadAtlas` 在解析后还要建 GL 纹理，所以不能只靠生产 exe 直接喂 manifest；需要 P1 编译后的测试 harness，或把解析抽成无 GL 的纯函数。夹具本身不依赖 GL。

## 预检

```powershell
Set-Location 'F:\WhaleGirlPet\build\worktrees\fix-sprite-parser'
& '.\.venv\Scripts\python.exe' '3d\tools\lint_sprite_manifest_fixtures.py'
```

预期输出：`cases=17 success=1 failure=16`、`fixture lint: PASS`。
