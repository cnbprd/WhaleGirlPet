# v3.2.0-sprite 发布证据索引

状态：**本地候选，未发布。** 本页只做路径索引，不替代证据本身；标“待补”的路径现在不存在，不能在发布说明里写成已通过。

## 0. 当前 24h 浸泡

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 任务 | `WhaleGirlSoak24hSprite`，标签 `soak_24h_sprite_task` | 运行中 |
| 启动 / 预计结束 | 2026-11-27 13:51:03 / 2026-11-28 13:51:03 | — |
| checkpoint | `3d/longrun_soak_24h_sprite_task.json` | 运行中，15:45:35 为 230 样本 |
| 日志 | `3d/longrun_soak_24h_sprite_task.log` | 运行中 |
| 最终 gate | `3d/tools/check_soak_final.py` | 结束后才能 `exit 0` |
| gate 合成测试 | `3d/tools/test_check_soak_final.py`、`docs/final-gate-test.md` | 8/8 已通过 |
| 运行中预检 | `docs/soak-prefinal-2026-11-27.md` | 已验证 `exit 3` |
| 浸泡记录 | `docs/soak-24h.md` | 已更新到 230 样本 |
| 失败取证 | `3d/tools/collect_soak_evidence.ps1`、`docs/soak-evidence.md` | 工具已 smoke test |
| 工具链预检 | `docs/toolchain-preflight-2026-11-27.md` | 路径/版本/磁盘 PASS；未构建 |
| 文档链接检查 | `docs/release-link-check-2026-11-27.md` | 11 个文件、14 个本地链接，0 死链 |

当前低 FPS 观察项：日志只有 1 行 `fps=3.7` / `update_us=237118.46`，随后回到 27.8；不是连续降速。

## 1. P1 manifest 回归（分支，未编译）

| 项 | 路径 | 状态 |
|---|---|---|
| 纯解析代码 | `build/worktrees/fix-sprite-parser/3d/sprite_manifest.h` / `.cpp` | 已写，未编译 |
| harness | `build/worktrees/fix-sprite-parser/3d/tests/test_sprite_manifest.cpp` | 已写，未编译 |
| 17 条夹具 | `build/worktrees/fix-sprite-parser/3d/tests/fixtures/sprite_manifest/cases.json` | 17 条，lint PASS |
| 静态自审 | `build/worktrees/fix-sprite-parser/docs/p1-static-self-review.md` | 未发现阻断项 |
| 设计说明 | `build/worktrees/fix-sprite-parser/docs/p1-sprite-manifest-harness.md` | 已写 |
| 分支 | `fix/sprite-parser`，HEAD `88a4e5d` | 未合入 main |

## 2. 17 卡可见验收

| 项 | 路径 | 状态 |
|---|---|---|
| 图集 / 清单 | `assets/2d_bridge/atlas.png`、`assets/2d_bridge/manifest.json` | 1024×512，17 卡 |
| 图集离线 QA | `docs/2d-atlas-card-qa.md`、`docs/2d-atlas-qa.json`、`docs/_2d_bridge_contact.png` | 17/17 通过 |
| 清单 QA | `docs/2d-manifest-qa.md`、`docs/2d-manifest-qa.json` | 17 卡，0 error / 0 warning |
| 单实例脚本 | `3d/tools/check_cards_visible.py` | 已写，只做过保护预检 |
| 17 卡 contact sheet | `docs/_3d_visible_17_cards.png` | 待补 |
| 逐卡坐标 JSON | `docs/2d-card-visible-qa.json` | 待补 |
| 已目检卡面 | `expression/happy`、`action/wave` | 只有 2 张 |

其余 15 张必须在浸泡结束后逐张目检；离线 QA 不能替代 3D 可见验收。

## 3. 卡面点击穿透

| 项 | 路径 | 状态 |
|---|---|---|
| 探针 | `3d/tools/check_click_through.py` | 已写，`--pid 7816` 干跑 `exit 2` |
| 真实点击结果 | `docs/click-through-result.json` | 待补 |
| 判定 | `card_hit_test=-1` 且 `target.received=true` | 未执行 |

设计上卡面不进入 `hitTest`；在真实坐标采样前，不能写成“点击穿透已通过”。

## 4. 2D PyInstaller 冻结包

| 项 | 路径 | 状态 |
|---|---|---|
| spec | `WhaleGirlPet.spec` | datas 已含 `assets/2d_bridge` |
| AssetBridge | `app/asset_bridge.py` | 不依赖 PIL |
| 静态审计 | `docs/package-static-audit.md` | 已完成 |
| 冻结包构建 / 启动 | 输出目录由 PyInstaller 决定 | 待浸泡结束 |

## 5. 安装器

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 安装器 | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe` | 4,791,434 B |
| sidecar | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe.sha256` | 已写入 |
| SHA256 | `510D182B7358E6A1601B085244D70F23724A236C6857D4FEF28AA4AD803E6C96` | 与 verifier 一致 |
| staging payload | `build/3d-installer-payload/3.2.0-sprite` | 含 `assets/2d_bridge` |
| 安装器脚本 | `installer/whale3d.iss`、`installer/build_3d_installers.ps1` | 自动构建缺 sprite 条目，修复分支 `fix/installer-build-sprite` 未合入 |
| 回归 | 临时目录安装/启动/卸载 exit 0 | 已有记录；最终安装器重建后需复跑 |

## 6. Release 资产

| 项 | 路径 / 值 | 状态 |
|---|---|---|
| 3D exe | `3d/whale3d.exe` | 1,377,792 B；SHA256 `3B2BE72FE1823FF2BBDA2884A218EE538F19871A2641BC06FBFF056910E3635C` |
| 便携 ZIP | `3d/whale3d-whale-girl-v3.2-sprite.zip` | 3,187,948 B；SHA256 `BF310AB7D82342463FAEA2CEB7408F64024FB7C9A51B7654F0F440666F5928BE` |
| 期望清单 | `docs/release-assets-3.2.0-sprite.json` | 已写 |
| verifier | `3d/tools/verify_release_assets.py` | 38 checks、0 error / 0 warning PASS |
| 报告 | `docs/release-asset-verify.md`、`docs/release-asset-verify.json` | 已生成 |
| 限制 | 安装器内部 payload 未解包核对 | — |

## 7. Release notes 与 CI

| 项 | 路径 | 状态 |
|---|---|---|
| 正式 Release notes | `docs/releases/v3.2.0-sprite.md` | 本地草稿，未发布 |
| 发布草稿 | `docs/release-3.2.0-sprite.md` | 已链接正式 notes |
| 执行手册 | `docs/post-soak-runbook.md` | 含 P1、17 卡、点击、安装器、上传顺序 |
| CI / Release 审计 | `docs/ci-release-static-audit.md` | 已审计；`release-notes.yml` 的 push 风险已记录 |
| CI artifact 命名修复 | 分支 `fix/ci-artifact-name`，提交 `94d4fdd` | 未合入、未触发 CI |
| GitHub Release | `v3.2.0-sprite` | 未创建、未上传 |

## 发布前硬门槛

- [ ] `check_soak_final.py` `exit 0`、`valid=True`、`status=done`、`alive_after_soak=True`
- [ ] P1 harness 编译并 17/17 通过
- [ ] 17 卡逐张可见目检完成
- [ ] `docs/click-through-result.json` 满足 `-1` / `true`
- [ ] 2D 冻结包启动并读到 17 卡
- [ ] 安装器最终回归 exit 0
- [ ] Release verifier 重跑 38 项 PASS
- [ ] 文件大小 / SHA256 与 Release notes、期望清单一致
- [ ] `release-notes.yml` 触发条件已确认，不被误触改写旧 Release

任何一项没有证据，发布说明只能写“待验证”，不能写成“已通过”。
