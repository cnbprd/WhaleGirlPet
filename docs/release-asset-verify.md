# Release 资产校验

生成时间：2026-11-27T15:00:08+08:00
版本：`3.2.0-sprite` / tag `v3.2.0-sprite`
结论：**PASS**（0 errors, 0 warnings）

> 只读校验：未启动 3D、未安装安装器、未构建、未修改生产 checkpoint。

| 状态 | 检查 | 详情 |
|---|---|---|
| PASS | 期望清单 JSON | F:\WhaleGirlPet\docs\release-assets-3.2.0-sprite.json |
| PASS | 3D exe 大小 | 1377792 |
| PASS | 3D exe SHA256 | 3B2BE72FE1823FF2BBDA2884A218EE538F19871A2641BC06FBFF056910E3635C |
| PASS | 便携 ZIP 大小 | 3187948 |
| PASS | 便携 ZIP SHA256 | BF310AB7D82342463FAEA2CEB7408F64024FB7C9A51B7654F0F440666F5928BE |
| PASS | 安装器 大小 | 4791434 |
| PASS | 安装器 SHA256 | 510D182B7358E6A1601B085244D70F23724A236C6857D4FEF28AA4AD803E6C96 |
| PASS | 安装器 .sha256 | hash=510D182B7358E6A1..., file=WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | 安装器 文件名含 3.2.0-sprite | WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | 安装器 文件名不含 -dev | WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | ZIP 可读 | 11 entries |
| PASS | ZIP 路径安全 | ok |
| PASS | ZIP whale3d.exe 大小 | 1377792 |
| PASS | ZIP whale3d.exe SHA256 | 3B2BE72FE1823FF2BBDA2884A218EE538F19871A2641BC06FBFF056910E3635C |
| PASS | ZIP assets/ui/pet.ico 大小 | 9001 |
| PASS | ZIP assets/ui/pet.ico SHA256 | 9F701BF34847EB00F0D51DAC01B61520EA58E3227A83D9E7A762AFE31303EE80 |
| PASS | ZIP assets/2d_bridge/atlas.png 大小 | 357857 |
| PASS | ZIP assets/2d_bridge/atlas.png SHA256 | 918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958 |
| PASS | ZIP assets/2d_bridge/manifest.json 大小 | 5354 |
| PASS | ZIP assets/2d_bridge/manifest.json SHA256 | EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D |
| PASS | 图集尺寸 | 1024x512 |
| PASS | 卡面 manifest JSON | parsed |
| PASS | 卡面 sheet_size | [1024, 512] |
| PASS | 卡面 slot_size | 160 |
| PASS | 卡面数量 | 17 |
| PASS | 卡面 id 完整 | missing=[], extra=[] |
| PASS | 卡面 id 无重复 | 17 ids |
| PASS | 卡面 rect 越界 | ok |
| PASS | 卡面 slot 越界 | ok |
| PASS | staging 存在 | build/3d-installer-payload/3.2.0-sprite |
| PASS | staging whale3d.exe 大小 | 1377792 |
| PASS | staging whale3d.exe SHA256 | 3B2BE72FE1823FF2BBDA2884A218EE538F19871A2641BC06FBFF056910E3635C |
| PASS | staging assets/ui/pet.ico 大小 | 9001 |
| PASS | staging assets/ui/pet.ico SHA256 | 9F701BF34847EB00F0D51DAC01B61520EA58E3227A83D9E7A762AFE31303EE80 |
| PASS | staging assets/2d_bridge/atlas.png 大小 | 357857 |
| PASS | staging assets/2d_bridge/atlas.png SHA256 | 918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958 |
| PASS | staging assets/2d_bridge/manifest.json 大小 | 5354 |
| PASS | staging assets/2d_bridge/manifest.json SHA256 | EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D |

## 限制

- 安装器内部 payload 未解包核对；本脚本核对安装器文件本身、`.sha256` sidecar 和构建 staging。
- 真实 24h 完成、17 卡目检、真实点击穿透仍需在浸泡结束后执行。
