# 2D 图集 QA：17 卡逐张对照

日期：2026-11-27
对象：`assets/2d_bridge/atlas.png` + `manifest.json`
工具：`3d/tools/check_2d_atlas.py`
结果：**17/17 通过，0 失败**

## 检查项

对每个 manifest 卡面：

1. rect 是整数且不越出 1024×512 图集；
2. atlas 区域非空、alpha bbox 存在；
3. 源 PNG 按图集生成脚本同样的“透明裁剪 + 缩放到 rect”后，与 atlas 区域比较：
   - alpha MAE；
   - RGB MAE（非透明区域）；
   - alpha 覆盖率差（阈值 `alpha > 8`）。
4. 生成一张带 id 标签的 contact sheet，人工看卡面朝向、是否裁到头发/尾巴/道具。

## 实测数值

| 指标 | 结果 |
| :--- | ---: |
| 卡面数 | 17 |
| 失败 | 0 |
| max alpha MAE | **0.0** |
| max RGB MAE | **0.005** |
| max coverage delta | **0.0** |
| 图集尺寸 | 1024×512 |
| 图集压缩体积 | 357,857 B |
| RGBA 显存 | 2,097,152 B |

RGB MAE 0.005 是 PNG 解码/合成造成的 1 个色阶内误差，不是卡面错位；alpha 与覆盖率完全一致。

## 产物

- 机器可读报告：`docs/2d-atlas-qa.json`（17 条 rect/MAE/ok）。
- 人工检查图：`docs/_2d_bridge_contact.png`（6×3，深色底，白字 id）。
- 重跑：

```powershell
python 3d\tools\check_2d_atlas.py
```

## 边界

- 只验证“图集与源 PNG 一致”和“rect 合法”，不验证卡面在 3D 屏幕上的实际大小、位置、遮挡。
- 没有验证 `@2x` 源；图集按 1x 卡面构建，`@2x` 仍留给未来高 DPI 资源。
- 没有验证 9 套皮肤缩略图；本图集只含 10 表情 + 7 动作，共 17 卡。
- contact sheet 用 PIL 默认字体，标签较小；它用于 QA 目检，不是对外宣传图。
