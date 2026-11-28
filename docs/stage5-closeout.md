# 阶段 5 收口：内容包安装/升级/卸载、签名与后端决策

日期：2026-11-28  
分支：`feat/v3.3-observe`  
结论：**阶段 5 按“内容包安装/升级/卸载 + 签名 waiver + 后端 no-go”收口。内容包升级链路实测通过；签名仍为 `NotSigned`，SignPath 外部状态未知；不引入第二个渲染后端。未发公开 Release，生产 exe 未替换。**

## 1. 内容包升级测试

| 项 | 值 |
|---|---|
| 旧安装器 | `dist/3d/WhaleGirlPet-Setup-3.2.0-ci.exe`，4,812,568 B，SHA256 `2950B8845AFB6D554E56EF7E30A2C565F9AEFBAA1CFAC38202D37AC97007221A` |
| 新安装器 | `dist/3d/WhaleGirlPet-Setup-3.3.0-stage4.exe`，4,814,785 B，SHA256 `BA734D2EAA998C33086DBDAECAA43F36D6AFD79134D05009C6F80F893B1CD99D` |
| 阶段 4 CI 包 | `build/ci-package-46145187110/whale3d-whale-girl-v3.2.0-ci.zip`，3,220,152 B，SHA256 `84C5EBB6EF4DC37C785297939AF5F442AAC8E3791393B85810786B2E423315E9` |
| 包内 exe | 1,463,296 B，SHA256 `E792667E212822C44352781223728DBE07FC3F0652AC6250ECCD3D078931EB93` |
| 安装目录 | `build/stage5-upgrade-app`（测试后已清理） |

步骤与结果：

1. 旧安装器静默安装到测试目录，exit 0；旧 `whale3d.exe` 1,457,664 B；`verify_package_content.py --stage` 返回 `ok=True errors=0 files=3`；headless 60 帧 exit 0，日志 `Content manifest: verified package hashes`。
2. 新安装器覆盖同一 AppId / 同一目录，exit 0；`whale3d.exe` 变为 1,463,296 B，SHA256 `E792667E...`；`content.json` 随包更新；`verify_package_content.py --stage` 再次返回 `ok=True errors=0 files=3`。
3. 升级后的 exe 跑 `--headless --frames=60 --no-render`，exit 0；日志 `Content manifest: verified package hashes`。
4. 运行 `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`，exit 0；安装目录只剩运行日志 `whale3d.log`，已归档到 `build/stage5-upgrade-run.log` 后清理。
5. 新安装器另做一次全新安装到 `build/stage5-fresh-app`，exit 0；exe 1,463,296 B / `E792667E...`；`verify_package_content.py` 返回 `ok=True errors=0 files=3`；headless 60 帧 exit 0，日志 `Content manifest: verified package hashes`；卸载 exit 0，运行日志归档到 `build/stage5-fresh-run.log` 后清理。

证据：`build/stage5-install-old.log`、`build/stage5-upgrade-new.log`、`build/stage5-upgrade-run.log`、`build/stage5-install-fresh.log`、`build/stage5-fresh-run.log`。

## 2. 资产 hash 与公开 Release

公开 `v3.2.0-sprite` 便携 ZIP：`3d/whale3d-whale-girl-v3.2-sprite.zip`，3,076,613 B，SHA256 `B6D777D98FAA043C8215430FE7FB9809C43E321EF8F3A9A7C6BF5132A6E09AFF`。

阶段 4 包内三个内容资产与公开 Release 同路径文件逐项一致：

| 资产 | SHA256 | 与公开 Release |
|---|---|---|
| `assets/models/whale_girl.vrm` | `BFD19124F1435E1CD2936F451AB4DEEFF0CABD5CA9A99B72E57E037D2BDECB87` | 相同 |
| `assets/2d_bridge/manifest.json` | `EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D` | 相同 |
| `assets/2d_bridge/atlas.png` | `918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958` | 相同 |

公开 Release ZIP 本身没有 `content.json`，因此能确认的是“三个资产 hash 与 Release 一致”，不能写成“Release 已经带 content 清单”。

## 3. 签名状态

- `Cert:\CurrentUser\My` 代码签名证书 0 张；`Cert:\LocalMachine\My` 0 张。
- `signtool.exe` 不在 PATH。
- 新安装器和阶段 4 exe 的 Authenticode 状态均为 `NotSigned`。
- SignPath Foundation 外部审核状态未知；未批准前维持阶段 0 的 unsigned waiver，不买付费 OV，也不只替换 exe 假装签名。

## 4. 后端决策

当前没有跨平台或 D3D12/Vulkan 的明确需求；单 OpenGL 3.3 后端 + `NullRenderer` 已覆盖可见渲染和 headless/CI。**不引入第二个 `IRenderer` 后端。** 若以后出现跨平台发布或明确图形 API 需求，再单独立项评估，不把多后端混进本阶段。

## 5. 边界与未完成

- 安装器版本显示 `3.3.0`，但阶段 4 exe 的版本资源仍是 `3.2.0.0`；这是内部候选。若做公开发布，必须先统一 bump exe 版本资源，再重打安装器。
- 未发公开 Release；`资产 hash 与 Release 一致` 只覆盖三个内容资产，不覆盖安装器/exe 资产。
- 安装器自身仍不预检 `content.json`，预校验发生在首次启动；与阶段 3 边界相同。
- 升级只测同 AppId 覆盖升级，没有测降级、跨大版本迁移、真实用户配置保留。
- 没有做增量 patch；当前是整包覆盖，只有出现明确增量更新收益时才做 patch。
- #71 开机动画仍在 backlog，未实现。

## 6. 证据路径

- `F:\WhaleGirlPet\dist\3d\WhaleGirlPet-Setup-3.3.0-stage4.exe`
- `F:\WhaleGirlPet\build\ci-package-46145187110\whale3d-whale-girl-v3.2.0-ci.zip`
- `F:\WhaleGirlPet\build\stage5-ci-payload\`
- `F:\WhaleGirlPet\build\stage5-install-old.log`
- `F:\WhaleGirlPet\build\stage5-upgrade-new.log`
- `F:\WhaleGirlPet\build\stage5-upgrade-run.log`
- `F:\WhaleGirlPet\build\stage5-install-fresh.log`
- `F:\WhaleGirlPet\build\stage5-fresh-run.log`
- `F:\WhaleGirlPet\build\stage5-release-payload\`
- `F:\WhaleGirlPet\docs\3d-engine-roadmap-2026-11-28.md`
