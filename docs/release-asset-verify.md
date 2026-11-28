# Release 资产校验

生成时间：2026-11-28T14:35:37+08:00
版本：`3.2.0-sprite` / tag `v3.2.0-sprite`
结论：**PASS**（0 errors, 0 warnings）

> 只读校验：未启动 3D、未安装安装器、未构建、未修改生产 checkpoint。

| 状态 | 检查 | 详情 |
|---|---|---|
| PASS | 期望清单 JSON | F:\WhaleGirlPet\docs\release-assets-3.2.0-sprite.json |
| PASS | 3D exe 大小 | 1370112 |
| PASS | 3D exe SHA256 | 74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893 |
| PASS | 便携 ZIP 大小 | 3076613 |
| PASS | 便携 ZIP SHA256 | B6D777D98FAA043C8215430FE7FB9809C43E321EF8F3A9A7C6BF5132A6E09AFF |
| PASS | 安装器 大小 | 4791958 |
| PASS | 安装器 SHA256 | CA6C2525FCB50D21699F512AECFCB18CFEBDA37337C9DE07EC5554E5A6974A45 |
| PASS | 安装器 .sha256 | hash=CA6C2525FCB50D21..., file=WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | 安装器 文件名含 3.2.0-sprite | WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | 安装器 文件名不含 -dev | WhaleGirlPet-Setup-3.2.0-sprite.exe |
| PASS | ZIP 可读 | 11 entries |
| PASS | ZIP 路径安全 | ok |
| PASS | ZIP whale3d.exe 大小 | 1370112 |
| PASS | ZIP whale3d.exe SHA256 | 74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893 |
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
| PASS | staging whale3d.exe 大小 | 1370112 |
| PASS | staging whale3d.exe SHA256 | 74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893 |
| PASS | staging assets/ui/pet.ico 大小 | 9001 |
| PASS | staging assets/ui/pet.ico SHA256 | 9F701BF34847EB00F0D51DAC01B61520EA58E3227A83D9E7A762AFE31303EE80 |
| PASS | staging assets/2d_bridge/atlas.png 大小 | 357857 |
| PASS | staging assets/2d_bridge/atlas.png SHA256 | 918194E5E7AB077A4CCFBFBB049D1514BC6D8E464A782153DCBAF4AB6C085958 |
| PASS | staging assets/2d_bridge/manifest.json 大小 | 5354 |
| PASS | staging assets/2d_bridge/manifest.json SHA256 | EAD6F972E41409A72C3ECB3B7658F69F4DFD07738CA597E028D7D7809078335D |

## 限制

- 安装器内部 payload 本脚本不展开；安装器已另做静默安装回放，安装退出码 0，`whale3d.exe`、`assets/2d_bridge` 哈希与 staging 一致。
- 真实 24h、17 卡目检和真实点击穿透已完成，证据见 `docs/soak-final-2026-11-28.md`、`docs/2d-card-visible-qa.md`、`docs/click-through-qa.md`。
