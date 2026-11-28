# v3.2.0-sprite 发布证据索引

状态：**本地发布候选，尚未创建 GitHub Release。** 本页只做路径索引，不替代证据本身。

## 0. 24h 浸泡

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 任务 | `WhaleGirlSoak24hSprite`，标签 `soak_24h_sprite_task`，PID 7816 已退出 | 完成 |
| 启动 / 结束 | 2026-11-27T13:51:03+0800 / 2026-11-28T13:53:36+0800 | 完成 |
| 最终 gate | `3d/tools/check_soak_final.py`，`exit 0`、`valid=True`、`issues=[]` | PASS |
| 证据 | `docs/soak-final-2026-11-28.md`、同目录 `gate.txt`、checkpoint、`.log`、`.err.log` | 已归档 |
| 墙钟 / 样本 | 86,553.0s（24h 2m33s）；2880/2881 | 仅差最后一条采样 |
| 存活 | `alive_after_soak=True`，非中途退出 | PASS |

任务计划程序历史中的 `0x800710E0` 是 13:52:40 重复触发被拒绝，不是 PID 7816 失败；`healthy=false` 是进程正常退出后的状态。

## 1. P1 manifest 回归

| 项 | 路径 | 状态 |
|---|---|---|
| 纯解析代码 | `3d/sprite_manifest.h` / `.cpp`（集成分支） | 已提交 |
| harness | `3d/tests/test_sprite_manifest.cpp` | 已提交 |
| 17 条夹具 | `3d/tests/fixtures/sprite_manifest/cases.json` | 17 条 |
| 编译产物 | `build/test_sprite_manifest_integration.exe` | 已生成 |
| 运行结果 | `17/17 passed`，exit 0 | PASS |
| 分支 | `integrate/sprite-parser-static-20261127` | 未合入 main |

## 2. 17 卡可见验收

| 项 | 路径 | 状态 |
|---|---|---|
| 图集 / 清单 | `assets/2d_bridge/atlas.png`、`assets/2d_bridge/manifest.json` | 1024×512，17 卡 |
| 图集离线 QA | `docs/2d-atlas-card-qa.md`、`docs/2d-atlas-qa.json`、`docs/_2d_bridge_contact.png` | 17/17 通过 |
| 清单 QA | `docs/2d-manifest-qa.md`、`docs/2d-manifest-qa.json` | 17 卡，0 error / 0 warning |
| 17 卡 contact sheet | `docs/_3d_visible_17_cards.png` | 已生成 |
| 逐卡坐标 JSON | `docs/2d-card-visible-qa.json` | 17/17，`status=pass` |
| 验收报告 | `docs/2d-card-visible-qa.md` | 已写 |
| 验收实例 | 安装器静默安装到临时目录后的 `whale3d.exe` | 17/17 captured |

截图背景是透明卡面叠在桌面/浏览器上，背景文字不是卡面错误；卡面本身完整、正向、无图集网格。

## 3. 卡面点击穿透

| 项 | 路径 | 状态 |
|---|---|---|
| 探针 | `3d/tools/check_click_through.py` | 已更新 overlay 发现与 z 序提升 |
| 真实点击结果 | `docs/click-through-result.json` | `ok=true`、`card_hit_test=-1`、`model_hit_test=1`、`target.received=true`、exit 0 |
| 验收报告 | `docs/click-through-qa.md` | 已写 |
| 实现 | 独立透明 overlay + `PostMessage` 向下层窗口转发 | 通过 |

点击测试目标临时置顶，再把主窗和 overlay 提到目标上方；这是受控 z 序，不代表所有普通窗口 z 序都已覆盖。

## 4. 2D PyInstaller 冻结包

| 项 | 路径 | 状态 |
|---|---|---|
| spec | `WhaleGirlPet.spec` | datas 已含 `assets/2d_bridge` |
| AssetBridge | `app/asset_bridge.py` | 不依赖 PIL |
| 冻结包构建 / 启动 | 输出目录由 PyInstaller 决定 | **未在本轮执行**；不阻塞 3D sprite 发布 |

## 5. 安装器

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 安装器 | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe` | 4,791,958 B |
| SHA256 | `CA6C2525FCB50D21699F512AECFCB18CFEBDA37337C9DE07EC5554E5A6974A45` | 与 verifier 一致 |
| sidecar | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe.sha256` | 已写入 |
| staging | `build/3d-installer-payload/3.2.0-sprite` | 含新 exe 和 `assets/2d_bridge` |
| 构建脚本 | `installer/build_3d_installers.ps1` | sprite 条目已 cherry-pick 到集成分支 |
| 安装回归 | 临时目录静默安装 exit 0；`whale3d.exe`、`assets/2d_bridge` 哈希匹配；卸载 exit 0 | PASS |

## 6. Release 资产

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 3D exe | `3d/whale3d.exe` | 1,370,112 B；SHA256 `74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893` |
| 便携 ZIP | `3d/whale3d-whale-girl-v3.2-sprite.zip` | 3,076,613 B；SHA256 `B6D777D98FAA043C8215430FE7FB9809C43E321EF8F3A9A7C6BF5132A6E09AFF` |
| 期望清单 | `docs/release-assets-3.2.0-sprite.json` | 已写 |
| verifier | `3d/tools/verify_release_assets.py` | 38 checks、0 error / 0 warning PASS |
| 报告 | `docs/release-asset-verify.md`、`docs/release-asset-verify.json` | 已生成 |
| 限制 | 安装器内部 payload 由独立 smoke install 回放核对 | 通过 |

## 7. Release notes 与 CI

| 项 | 路径 | 状态 |
|---|---|---|
| 正式 Release notes | `docs/releases/v3.2.0-sprite.md` | 已更新为当前资产/验收 |
| 发布草稿 | `docs/release-3.2.0-sprite.md` | 已更新 |
| 执行手册 | `docs/post-soak-runbook.md` | 保留流程记录 |
| CI / Release 审计 | `docs/ci-release-static-audit.md` | `release-notes.yml` push 风险仍记录 |
| CI artifact 命名修复 | 分支 `fix/ci-artifact-name`，提交 `94d4fdd` | 未合入、未触发 CI |
| CI release-notes 修复 | 分支 `fix/release-notes-tag`，提交 `56ba124` | 未合入 |
| GitHub Release | `v3.2.0-sprite` | **未创建、未上传** |

## 发布前硬门槛

- [x] `check_soak_final.py` `exit 0`、`valid=True`、`status=done`、`alive_after_soak=True`
- [x] P1 harness 编译并 17/17 通过
- [x] 17 卡逐张可见目检完成
- [x] `docs/click-through-result.json` 满足 `-1` / `true`
- [ ] 2D 冻结包启动并读到 17 卡（本版不阻塞）
- [x] 安装器最终回归 exit 0
- [x] Release verifier 重跑 38 项 PASS
- [x] 文件大小 / SHA256 与 Release notes、期望清单一致
- [ ] `release-notes.yml` 触发条件已确认，不被误触改写旧 Release
- [ ] 代码签名（`NotSigned`，SignPath 审核状态未知）
- [ ] 创建 `v3.2.0-sprite` Release 并上传资产
