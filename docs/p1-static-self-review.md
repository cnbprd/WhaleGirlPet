# P1 sprite manifest 静态自审

日期：2026-11-27  
范围：`fix/sprite-parser` 分支的 `3d/sprite_manifest.h`、`3d/sprite_manifest.cpp`、`3d/sprite.cpp`、`3d/tests/test_sprite_manifest.cpp`、`3d/build.ps1`，以及 `3d/tests/fixtures/sprite_manifest/cases.json`。  
方式：只读逐行检查；未编译、未链接、未启动 3D、未改生产 exe。

## 结论

**静态检查未发现阻断项。** 纯解析函数和 `loadAtlas` 的边界划分符合设计，17 条夹具的错误期望与解析代码一致。剩余风险集中在“没有编译”和“没有覆盖 STB/GL 失败”。

## 逐项核对

| 项 | 结果 | 说明 |
|---|---|---|
| 纯解析无 SDL/GL | PASS | `sprite_manifest.*` 只依赖 nlohmann、string、unordered_map |
| 错误字符串顺序 | PASS | 10 类错误与旧 `loadAtlas` 一致；缺字段/类型错误仍为 `manifest parse:` |
| `cards` 赋值时机 | PASS | 解析全部成功后才 `cards = std::move(data.cards)`；失败不留下半成品 |
| atlas 尺寸校验 | PASS | 独立 `validateAtlasSize`，错误文本保持 `actual WxH, manifest WxH` |
| `loadAtlas` GL 边界 | PASS | 解析、STB 解码、尺寸校验、GL 纹理创建顺序清晰 |
| 构建入口 | PASS | `3d/build.ps1` sources 已加入 `sprite_manifest.cpp` |
| 测试 harness | PASS（静态） | 17 条 case、成功/失败/atlas 尺寸三条分支都有处理 |
| 夹具覆盖 | PASS | 17 条 = 1 成功 + 16 失败；lint 已 PASS |

## 与旧实现的差异

1. 旧实现边解析边写 `Impl::cards`；新实现先写局部 `Data`，成功后移动。解析失败时旧实现可能残留前几张卡，新实现保持空 map。由于 `init` 失败后不会使用卡面，这个差异不影响运行。
2. 旧实现用 `file >> json`；新实现先把文件读成字符串再 `json::parse`。两者对正常 manifest 等价；新实现把文件读取和 JSON 解析分开，便于纯测试。
3. 旧实现 catch 包住解析 + STB + GL；新实现把 STB/GL 留在 `loadAtlas`，解析异常只在 `parseJson` 内捕获。错误字符串已保持。

## 未验证项

- 没有 g++ 编译，不能证明头文件/源文件链接、`std::move`、`std::stringstream`、nlohmann 版本兼容性都成立。
- 没有跑 17 条真实 case；`test_sprite_manifest.cpp` 的遍历、`contains`、错误匹配逻辑只是静态检查。
- 没有覆盖 `stbi_load` 失败、`glGenTextures`/`glTexImage2D` 失败；这些仍要等真实 exe 或安装包回归。
- 没有验证 `build.ps1` 增加 source 后 CI 的 `3d-build.yml` 仍能通过；要等下一次构建。

## 结论口径

静态自审可以降低第一次编译的返工概率，但不能把“代码已写”说成“解析已验证”。浸泡结束后的第一道 P1 验证仍是：

```powershell
Set-Location 'F:\WhaleGirlPet\build\worktrees\fix-sprite-parser'
& $gxx -std=c++17 -O2 -I '3d' `
  '3d\tests\test_sprite_manifest.cpp' `
  '3d\sprite_manifest.cpp' `
  -o 'build\test_sprite_manifest.exe'
& '.\build\test_sprite_manifest.exe'
```

预期 `17/17 passed`。
