# P1 sprite manifest test harness 设计

状态：**代码已落在分支，未编译。**  
目标：让 `fix/sprite-parser` 的 17 条坏 manifest 夹具可以在浸泡结束后、不启动 3D、不建 GL 上下文的情况下跑真实 C++ 解析回归。

## 问题

当前 `SpriteLayer::Impl::loadAtlas` 把两件事绑在一起：

1. 读 `assets/2d_bridge/manifest.json`，用 nlohmann 解析并校验字段；
2. 调 `stbi_load` 解码 atlas、比较尺寸、创建 GL 纹理。

`loadAtlas` 是 `Impl` 的私有成员，`SpriteLayer::init` 又要求 GL 入口点已加载。测试若直接调 `init`，即使 manifest 是坏的，也会先过 GL 初始化；而且每个 case 都要窗口/GL 上下文，不适合批量回归。

## 方案 A（推荐）：抽纯解析函数

新增不依赖 SDL/GL 的解析单元：

- `3d/sprite_manifest.h`
- `3d/sprite_manifest.cpp`

接口草案：

```cpp
namespace sprite_manifest {

struct CardRect {
    float u0 = 0.0f;
    float v0 = 0.0f;
    float u1 = 0.0f;
    float v1 = 0.0f;
    int w = 0;
    int h = 0;
};

struct Data {
    int sheet_w = 0;
    int sheet_h = 0;
    std::string sheet_rel;
    std::unordered_map<std::string, CardRect> cards;
};

bool parseJson(const std::string& text, Data& out, std::string& err);
bool validateAtlasSize(const Data& data, int actual_w, int actual_h,
                       std::string& err);

}  // namespace sprite_manifest
```

`parseJson` 只做 JSON/字段/rect 校验，保留现有错误字符串和顺序：

1. `sheet_size must be two integers`
2. `sheet_size must be positive`
3. `cards must be a non-empty array`
4. `empty card id`
5. `duplicate card id: <id>`
6. `card rect must be four integers: <id>`
7. `card outside atlas: <id>`
8. `sheet path missing`
9. 缺字段/类型错误/JSON 语法错误 → `manifest parse: ...`

`validateAtlasSize` 只比较声明尺寸和实际尺寸，保留：

```text
atlas size mismatch: actual <w>x<h>, manifest <w>x<h>
```

`loadAtlas` 改成：

1. 读 manifest 文件文本；
2. 调 `parseJson`；
3. `stbi_load` 解码；
4. 调 `validateAtlasSize`；
5. 建 GL 纹理。

这样解析错误和 atlas 尺寸错误都可以在无 GL 的测试里覆盖；STB 解码失败仍只在真实 `loadAtlas` 中发生。

## 测试 harness

实现文件：

- `3d/sprite_manifest.h`
- `3d/sprite_manifest.cpp`
- `3d/tests/test_sprite_manifest.cpp`
- `3d/build.ps1` 的 sources 已加入 `sprite_manifest.cpp`

新增 `3d/tests/test_sprite_manifest.cpp`：

- 读 `3d/tests/fixtures/sprite_manifest/cases.json`；
- 每个 case 取 `manifest` 序列化或 `raw_manifest` 原文；
- 调 `sprite_manifest::parseJson`；
- 按 `expect.ok` / `expect.error` / `expect.error_prefix` 比对：
  - `valid_minimal`：parse 成功，再用 `validateAtlasSize(..., 1024, 512)` 成功；
  - `atlas_size_mismatch`：parse 成功，再尺寸校验失败，错误精确匹配；
  - 其余 15 条：parse 必须失败，错误精确/前缀匹配；
- 打印 `PASS/FAIL <case>`，全部通过 exit 0，否则 exit 1。

不读生产 manifest，不复制/覆盖 `assets/2d_bridge`，不启动 `whale3d.exe`。

## 编译

浸泡结束后用 w64devkit 的 g++，只编纯解析单元和测试：

```powershell
Set-Location 'F:\WhaleGirlPet\build\worktrees\fix-sprite-parser'
$gxx = (Get-ChildItem 'F:\WhaleGirlPet\.toolchains\w64devkit' -Recurse -Filter 'g++.exe' | Select-Object -First 1).FullName
& $gxx -std=c++17 -O2 -I '3d' `
  '3d\tests\test_sprite_manifest.cpp' `
  '3d\sprite_manifest.cpp' `
  -o 'build\test_sprite_manifest.exe'
& '.\build\test_sprite_manifest.exe'
```

不链接 SDL3/GL，不跑 `3d\build.ps1`，不产出 `whale3d.exe`。

## 验收

- 17/17 case 输出 PASS；
- `valid_minimal` 成功；
- 16 条坏 manifest 全部失败，错误与 `cases.json` 一致；
- 不启动 3D、不创建 GL 上下文、不碰 24h 浸泡；
- 编译产物只在 `build\worktrees\fix-sprite-parser\build\`，不覆盖生产 exe。

## 不采用方案 B：test-only 入口直接调 `loadAtlas`

给 `SpriteLayer` 加 `friend` 或 `#ifdef` 测试入口看似改动小，但 `loadAtlas` 仍然绑定 `stbi_load` 和 GL 纹理创建，测试要么伪造 GL，要么还是开窗口。它不能解决“批量坏 manifest 快速回归”的问题，因此不采用。

## 风险与回滚

- 抽函数会改 `sprite.cpp` 结构；错误字符串和校验顺序必须逐条保留，靠 17 条 case 锁住。
- 纯解析测试不覆盖 STB 解码失败、GL 创建失败；这两条仍需真实 exe/安装包回归。
- 所有改动只在 `fix/sprite-parser` 分支；不合并、不覆盖生产 `3d\whale3d.exe`。若回归失败，直接回退 `sprite_manifest.*` 和 `sprite.cpp` 的这次重构，保留 `310259f` 夹具提交。

## 当前状态

- 夹具：`310259f`，17 条，lint PASS；
- P1 补丁：`ee747c1`，未编译；
- 本次实现：`sprite_manifest.*`、`test_sprite_manifest.cpp`、`build.ps1` source 列表已写入分支；未编译、未产出 exe。
- 静态自审：`docs/p1-static-self-review.md`，未发现阻断项；编译/17 条真实回归仍未发生。
