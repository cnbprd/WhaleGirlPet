# 阶段 3：资产 cook 基线

日期：2026-11-28  
分支：`feat/v3.3-observe`  
CI：run `46137873849` success（Pillow + cook + 8 类负向夹具 + content verify）。  
状态：**基线工具、负向夹具、content 校验和 CI ZIP 包内 content 校验已通过；安装器读取 content 清单、运行时启动校验尚未完成，阶段 3 未收口。**

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
| package content | 本地合成 stage：3 文件 hash 一致；`verify_package_content.py --stage` 和 `--zip` 均 `ok:true` |
| 确定性 | 同输入、同 `build/content` 连续两次 cook，content hash 不变 |
| 报告 | `docs/asset-cook-report.json`，`ok:true`、errors 0、warnings 0 |
| 负向夹具 | 8 类坏输入全部拒绝：坏 rect、重复 id、缺 source、坏 slot、坏 atlas 尺寸、坏 humanoid node、坏 accessor count、坏 spring joint；CI `46137873849` 已跑 |

## 3. 已知边界

- `content.json` 目前只是 cook/package 产物；运行时仍直接读 VRM/manifest，没有启动校验。
- ZIP 打包已接入 `content.json` 与 `verify_package_content.py`；`verify_release_assets.py`、安装器脚本本身还没有读 content 清单。
- UV 方向没有做独立像素级方向校验；只验证 atlas/source 的 alpha 对齐。
- `walk` 是 `model.cpp` 里的程序化 clip，不在 VRM 动画列表里；cook 只记录 Idle。
- 没有做坏 accessor buffer 越界、坏材质纹理越界等全部边界；当前覆盖的是本轮夹具列出的 8 类。
- 生产 `3d/whale3d.exe`、Release 资产未改。

## 4. 下一步

1. 给 `verify_release_assets.py` 加 `content` 段：从 ZIP 读 package content，校验文件 hash/17 卡 id；不改已发布 3.2 的期望清单。
2. 安装器 staging 构建后检查 `content.json` 与 payload 文件 hash 一致。
3. 若要运行时启动校验，再在 `model.cpp`/启动路径加只读检查，单独跑无头回归。
4. 再评估是否值得做自定义 `content.bin`；没有实测加载/内存收益就不做。
