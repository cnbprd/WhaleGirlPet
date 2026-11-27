# 2D 卡面 manifest 结构 QA

日期：2026-11-27  
工具：`3d/tools/check_2d_manifest.py`（CPU-only，不启动 3D）  
输入：`assets/2d_bridge/manifest.json` + `assets/2d_bridge/atlas.png`

## 结果

- 卡面数：17 / 期望 17
- errors：0
- warnings：0
- `sheet_size`：1024×512，与 `atlas.png` 实际尺寸一致
- `slot_size`：160，所有 slot 尺寸正确且对齐
- 所有 `rect` 在图集内，且被各自 slot 包含
- 所有 `source` 文件存在
- 17 个 id 唯一，无缺失、无多余

JSON：`docs/2d-manifest-qa.json`

## 边界

这份检查验证的是 manifest 的数据结构和几何关系，不是 C++ `SpriteLayer::loadAtlas` 的异常处理。C++ 端对字段缺失/类型错误仍可能抛出未捕获异常（见 `docs/sprite-static-review.md` 的 P1）；本检查不会替代那段代码加固。

卡面内容对照仍以 `docs/2d-atlas-card-qa.md` 为准；3D 可见验收仍只完成 `expression/happy` 与 `action/wave`。
