# 阶段 3 收口：资产 cook、content 清单与运行时校验

日期：2026-11-28  
分支：`feat/v3.3-observe`  
结论：**阶段 3 在“资产校验 + 清单 + 可重复打包 + 运行时校验”范围内完成；安装器自身不做预校验，首次启动由 `whale3d.exe` 校验。若把“安装器安装前预校验”也列为退出条件，则该项仍未满足，阶段 3 只能算条件退出。** 阶段 4 的渲染 pass 边界尚未开始。

## 1. 正向 cook

| 项 | 值 |
|---|---|
| model | `3d/assets/models/whale_girl.vrm`，351,708 B，SHA256 `BFD19124F1435E1CD2936F451AB4DEEFF0CABD5CA9A99B72E57E037D2BDECB87` |
| model 结构 | nodes 29、meshes 1、materials 1、textures 1、images 1、skin joints 28、humanoid bones 19、springs 4、animations 1（Idle，14 channels） |
| atlas | `assets/2d_bridge/atlas.png`，1024×512，slot 160，SHA256 `918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958` |
| manifest | 17 cards，SHA256 `EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D` |
| content.json | SHA256 `009A8AB750E218556EFFBCCD99E0C9744F48940E5A56CA500FB97C1B2137CE61` |
| 稳定性 | 同输入、同 `build/content` 连续两次 cook，content hash 不变 |
| 负向夹具 | 8 类坏输入全部拒绝：坏 rect、重复 id、缺 source、坏 slot、坏 atlas 尺寸、坏 humanoid node、坏 accessor count、坏 spring joint |
| content verify | `3d/tools/verify_content.py` 通过 3 个 cooked 文件及所有 source hash；篡改 model hash 的副本返回 1 |

## 2. 包清单与 CI ZIP

`3d/tools/package_content.py` 把 cook 路径转换成包根布局，并先核对 stage 实际文件 hash；`verify_package_content.py` 对 stage/ZIP 独立校验 schema、3 个文件 hash、17 卡 id。

- CI `46138563544`（第一版 package/ZIP）：`whale3d-whale-girl-v3.2.0-ci.zip`，3,206,085 B，SHA256 `41DD283337CC3D0C7A2A061C86B06D0418B340CCDFFC7BEAF952385A55B2BC4F`；stage/ZIP 均 `ok:true files=3 errors=0`。
- CI `46139915847`（加入运行时校验）：`whale3d-whale-girl-v3.2.0-ci.zip`，3,216,957 B，SHA256 `AF28BEE328AC35348542565A67B665379A6ED217562E43F5EAF7266C36A3C4FE`；包内 `content.json` 校验通过。
- 新 CI 包内 `whale3d.exe`：1,457,664 B，SHA256 `05CD6B495CA978E6C87247FCDD180D065A9FB5B1B1BC17BD1AF89C912DAAFCE9`。
- `verify_release_assets.py` 新增可选 `content` 段：对 CI ZIP 通过 9 checks；把 model 的 bytes 改成 123 的副本返回 `package content 文件 hash` 错误。

## 3. 运行时校验

`3d/content_manifest.cpp` 在启动时读取 `<exe目录>/content.json`：

- 校验 `whale3d-content-package-v1` schema、3 个文件的大小/SHA256（Windows BCrypt）、17 卡数量和 model/atlas/manifest 归属。
- 有 manifest 且不匹配：`Content manifest: FAIL (...)`，退出码 1。
- 没有 manifest：`Content manifest: absent; legacy asset paths`，继续旧路径。
- 只校验 package content 文件，不重做 GLB/VRM 结构校验，也不替换运行时的 VRM/manifest 加载器。

本机实测：

- 带 content 的 stage：`--headless --frames=60 --no-render` 和真实 headless 均输出 `Content manifest: verified package hashes`，退出 0；日志随后 `Model loaded: ...whale_girl.vrm (2076 triangles, 28 joints, 1 animations)`。
- 给 model 追加 1 字节：`--no-render` 退出 1，日志 `Content manifest: FAIL (content file mismatch: assets/models/whale_girl.vrm)`。
- 删除 content.json：`Content manifest: absent; legacy asset paths`，退出 0，模型照常加载。

## 4. 安装器与 17 卡

从 `46139915847` 的 ZIP 编译安装器：

- `dist/3d/WhaleGirlPet-Setup-3.2.0-ci.exe`：4,812,568 B，SHA256 `2950B8845AFB6D554E56EF7E30A2C565F9AEFBAA1CFAC38202D37AC97007221A`。
- 静默安装到 `build/installer-3.2.0-ci-runtime-app`，exit 0。
- 安装目录 `verify_package_content.py --stage`：`ok=True errors=0 files=3`。
- 安装目录直接启动 `--headless --frames=60`：exit 0，`Content manifest: verified package hashes`，模型加载成功。
- `check_cards_visible.py` 从安装目录抓 17/17 卡，contact sheet `build/installer-cards-3.2.0-ci-runtime/_3d_visible_17_cards.png`；自动状态仍是 `needs_visual_review`，我目检 17 张均有对应卡面。
- 卸载 exit 0；安装目录只剩测试产生的 `whale3d.log`/`headless-summary.json`，已清理。

## 5. 已知边界

- 安装器本身不解析 `content.json`，只把 content 随 payload 安装；预校验发生在首次启动。若要求“安装前预检”，需要另加安装器脚本/哈希工具，本轮未做。
- 运行时校验只覆盖 package content 的 3 个文件；GLB/VRM 内部结构、材质/纹理越界等仍由 cook 阶段负责。
- 17 卡 QA 的自动状态没有改成 pass；通过依据是 contact sheet 目检，和阶段 2 同一口径。
- CI 只跑 `--no-render` 的 content 校验；真实 GL 渲染、17 卡截图是本机 GTX 1060 结果，不是 CI GPU runner 结果。
- 生产 `3d/whale3d.exe`、已发布 `v3.2.0-sprite` 资产未替换；本阶段产物是 CI ZIP 和本地测试安装器。
- 未做自定义 `content.bin`；没有实测加载/内存收益前不做。

## 6. 证据路径

- `F:\WhaleGirlPet\docs\asset-cook.md`
- `F:\WhaleGirlPet\docs\asset-cook-report.json`
- `F:\WhaleGirlPet\build\content\content.json`
- `F:\WhaleGirlPet\build\ci-package-46139915847\...\whale3d-whale-girl-v3.2.0-ci.zip`
- `F:\WhaleGirlPet\build\installer-content-verify-3.2.0-ci.json`
- `F:\WhaleGirlPet\build\installer-cards-3.2.0-ci-runtime\2d-card-visible-qa.json`
- `F:\WhaleGirlPet\build\installer-cards-3.2.0-ci-runtime\_3d_visible_17_cards.png`
- CI：`46137873849`、`46138563544`、`46139915847`
