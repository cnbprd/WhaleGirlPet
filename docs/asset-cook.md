# 阶段 3：资产 cook 基线

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：`46137873849` success（Pillow + cook + 8 类负向夹具 + content verify）；`46138563544` success（package content + stage/ZIP verify，ZIP SHA256 `41DD283337CC3D0C7A2A061C86B06D0418B340CCDFFC7BEAF952385A55B2BC4F`）。
状态：**基线工具、负向夹具、content 校验、CI ZIP 包内校验、release verifier 的 content 段和运行时启动校验已通过；安装器 payload 已包含 content，待用新 CI 包复跑安装器/17 卡，阶段 3 暂未正式收口。**

## 1. 工具

`3d/tools/cook_assets.py`：

- 校验 VRM/GLB：magic/version/length、JSON/BIN chunk、mesh primitive 的 POSITION/NORMAL/TEXCOORD_0/JOINTS_0/WEIGHTS_0、indices、accessor、material/texture/image。
- 校验 VRM：19 个 humanoid 骨骼、28 个 skin joints、4 条 spring 链、动画 channel/accessor。
- 校验 2D：atlas 1024×512、slot 160、17 个 card id、rect 在 atlas/slot 内、source 存在且非全透明、atlas/source alpha MAE ≤ 4.0。
- 只复制 model、manifest、atlas 到 `build/content`，写确定性 `content.json`；不做自定义 `content.bin`。

`3d/tools/package_content.py`：

- 把 cook 的仓库路径转成 package 根路径（`3d/assets/...` → `assets/...`）。
- 在写 `content.json` 前校验 stage 中 model/manifest/atlas 的大小和 hash；不一致直接失败。
- 输出 `whale3d-content-package-v1`，带 `cook_sha256`，供 ZIP/安装器读取。

`3d/tools/verify_package_content.py`：

- 对 stage 或 ZIP 内的 `content.json` 做独立校验：schema、3 个文件 hash/大小、17 卡 id、model/manifest/atlas 是否在文件清单里。
- 不启动渲染器，不跑安装器。

## 2. 正向结果

| 项 | 值 |
|---|---|
| model | `3d/assets/models/whale_girl.vrm`，351,708 B，SHA256 `BFD19124F1435E1CD2936F451AB4DEEFF0CABD5CA9A99B72E57E037D2BDECB87` |
| model 结构 | nodes 29、meshes 1、materials 1、textures 1、images 1、skin joints 28、humanoid bones 19、springs 4、animations 1（Idle，14 channels） |
| atlas | `assets/2d_bridge/atlas.png`，1024×512，slot 160，SHA256 `918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958` |
| manifest | 17 cards，SHA256 `EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D` |
| content.json | SHA256 `009A8AB750E218556EFFBCCD99E0C9744F48940E5A56CA500FB97C1B2137CE61` |
| content 校验 | `3d/tools/verify_content.py` 通过：3 个 cooked 文件、所有 source hash 一致；篡改 model hash 的副本被拒绝 |
| package content | 本地合成 stage 和真实 CI ZIP：`verify_package_content.py` 均 `ok:true`、3 文件 hash 一致 |
| CI ZIP | `46138563544` 产出 `whale3d-whale-girl-v3.2.0-ci.zip`，3,206,085 B，SHA256 `41DD283337CC3D0C7A2A061C86B06D0418B340CCDFFC7BEAF952385A55B2BC4F`；包内 `content.json` 校验通过 |
| release verifier | `verify_release_assets.py` 的 `content` 段对 CI ZIP 通过（9 checks）；把 model 的 bytes 改成 123 的另一份 ZIP 被拒绝 |
| runtime content | 新构建在带 `content.json` 的 stage 中 `--headless --no-render` 和真实 headless 均输出 `Content manifest: verified package hashes`；改 model 一字节后 `--no-render` 退出 1，日志为 `content file mismatch` |
| 确定性 | 同输入、同 `build/content` 连续两次 cook，content hash 不变 |
| 报告 | `docs/asset-cook-report.json`，`ok:true`、errors 0、warnings 0 |
| 负向夹具 | 8 类坏输入全部拒绝：坏 rect、重复 id、缺 source、坏 slot、坏 atlas 尺寸、坏 humanoid node、坏 accessor count、坏 spring joint；CI `46137873849` 已跑 |

## 3. 已知边界

- `content.json` 已由运行时启动路径校验；校验失败直接退出，缺失时按 legacy/dev 路径继续。
- ZIP 打包已接入 `content.json` 与 `verify_package_content.py`；`verify_release_assets.py` 已支持可选 `content` 段；安装器本身不解析 content，只负责把 content 随 payload 安装。
- 运行时校验用 Windows BCrypt SHA256；只校验 package content 里的 3 个文件，不做 GLB/VRM 结构重校验。
- UV 方向没有做独立像素级方向校验；只验证 atlas/source 的 alpha 对齐。
- `walk` 是 `model.cpp` 里的程序化 clip，不在 VRM 动画列表里；cook 只记录 Idle。
- 没有做坏 accessor buffer 越界、坏材质纹理越界等全部边界；当前覆盖的是本轮夹具列出的 8 类。
- 生产 `3d/whale3d.exe`、Release 资产未改。

## 4. 下一步

1. 用新 CI 包重跑安装器静默安装 + 安装目录 content 校验 + 17 卡目检，拿到最终包/安装器 hash。
2. 再评估是否值得做自定义 `content.bin`；没有实测加载/内存收益就不做。
3. 阶段 3 收口后，阶段 4 再动渲染 pass 边界；不改运行时的内容加载语义。
