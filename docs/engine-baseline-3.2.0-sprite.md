# 3D 引擎基线：v3.2.0-sprite

日期：2026-11-28  
状态：**阶段 0 基线冻结中；发布已闭环，2D 冻结包 / SignPath / 普通 z 序仍有未决项。**

## 1. 发布基线

| 项 | 值 |
|---|---|
| Release | `https://github.com/cnbprd/WhaleGirlPet/releases/tag/v3.2.0-sprite` |
| 状态 | 公开、非 prerelease、非 draft |
| 发布时间 | 2026-11-28T06:52:28Z（14:52:28 UTC+8） |
| tag | `v3.2.0-sprite` → `a2ef92c` |
| `main` | `d0e61e8`（含发布后文档） |
| CI | `Build 3D (Windows)` run `46117963651` 成功 |
| 资产 | 安装器、安装器 `.sha256`、便携 ZIP、单独 `whale3d.exe` |

## 2. 资产基线

| 资产 | 大小 | SHA256 |
|---|---:|---|
| `3d/whale3d.exe` | 1,370,112 B | `74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893` |
| `3d/whale3d-whale-girl-v3.2-sprite.zip` | 3,076,613 B | `B6D777D98FAA043C8215430FE7FB9809C43E321EF8F3A9A7C6BF5132A6E09AFF` |
| `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe` | 4,791,958 B | `CA6C2525FCB50D21699F512AECFCB18CFEBDA37337C9DE07EC5554E5A6974A45` |

安装器 sidecar：`dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe.sha256`，与安装器同哈希。

## 3. 引擎基线

| 项 | 值 | 来源 |
|---|---|---|
| 渲染 | 手写 OpenGL 3.3 + SDL3 + ozz | `3d/README.md` |
| 模型 | 单模型 2,076 三角形 | `3d/README.md` |
| 窗口 | 420×620，透明、置顶、不可聚焦 | `3d/README.md` |
| FPS | 28.3–29.0 | `3d/README.md` |
| private bytes | 约 97.8–98.2 MB | `3d/README.md` |
| CPU | 31.1–35.8% of one core | `3d/README.md` |
| 24h 浸泡 | `exit 0`、`valid=True`、`issues=[]`、`alive_after_soak=True`；墙钟 86,553.0s；样本 2880/2881 | `docs/soak-final-2026-11-28.md` |
| 24h FPS | min 0.0 / max 29.3 / avg 27.25 / last 9.6 | `docs/soak-final-2026-11-28.md` |

## 4. 验收门禁基线

| 门禁 | 状态 | 证据 |
|---|---|---|
| 24h 浸泡 | PASS | `docs/soak-final-2026-11-28.md`、`gate.txt` |
| P1 夹具 | PASS 17/17 | `build/test_sprite_manifest_main.exe` |
| 17 卡可见 | PASS 17/17 | `docs/2d-card-visible-qa.json`、`docs/_3d_visible_17_cards.png` |
| 点击穿透（受控 z 序） | PASS | `docs/click-through-result.json` |
| 点击穿透（普通桌面） | **部分通过** | 非 topmost 跨进程 target 已过；第三方 Notepad/Chrome/Explorer 未测 |
| 安装器安装/卸载 | PASS | `docs/installer-smoke-3.2.0-sprite.md` |
| 资产 verifier | PASS 38/38 | `docs/release-asset-verify.md` |
| 2D 冻结包 | **部分通过** | 包内 atlas/manifest 存在；`load_cards` 17；未验 UI 发包 |
| 代码签名 | **NotSigned / 外部审核未知** | 0 张代码签名证书；无 `signtool.exe` |

## 5. 阶段 0 未决项

### 5.1 2D PyInstaller 冻结包

- 已用 `WhaleGirlPet.spec` 在 2026-11-28 15:17 构建到 `build/2d-freeze-3.2.0-sprite/WhaleGirlPet`，exe 4,811,143 B，SHA256 `4ABE595EEB084070525A01EFBA71594239D90C0629DFC291A7DECB8EF82893BE`。
- 包内 `_internal/assets/2d_bridge/manifest.json` 和 `atlas.png` 均存在；manifest SHA256 `EAD6F972...`、atlas SHA256 `918194E5...`，`load_cards(packaged manifest)` 返回 **17** 张卡。
- 冻结 exe 启动 8 秒仍存活（RSS 81.6 MB / private 51.4 MB），stderr 只有 `pyi_splash` 的 `_PYI_SPLASH_IPC` 警告，没有 `[asset_bridge] disabled` 错误。
- 仍缺：通过 2D UI 真实触发 `action/wave` 并让 3D 收到；本轮只证明“包内资产 + manifest 解析 + 启动不报错”。
- 旧 `dist/WhaleGirlPet/WhaleGirlPet.exe`（2026-11-26 14:13:07，4,759,286 B）没有 `manifest.json` / `atlas.png`，不作为本轮证据。

### 5.2 SignPath

- `Cert:\CurrentUser\My` 和 `Cert:\LocalMachine\My` 均无代码签名证书。
- `signtool.exe` 不在本机 PATH。
- `3d/whale3d.exe` 和安装器均 `NotSigned`。
- SignPath Foundation 审核状态需要外部确认；批准后必须重新构建/签名/上传，不能只替换 exe。未批准则记录 waiver，不买付费 OV。

### 5.3 普通桌面 z 序

- 已通过的是“测试 target 先置顶，再把主窗和 overlay 提到 target 之上”的受控 z 序。
- 2026-11-28 新增非 topmost 跨进程 target 测试：`ok=true`、`target_topmost=false`、`clicks_before=0`、`clicks_after=1`；证据 `docs/ordinary-zorder-result.json`、`docs/ordinary-zorder.log`。
- 仍未验证：Notepad、Chrome、Explorer 等真实第三方窗口；`findWindowBelow` 对子窗口、管理员权限窗口、UWP/WPF 目标的行为。

## 6. 阶段 0 退出判断

当前**不能宣布阶段 0 完成**。要关闭阶段 0，至少需要：

- 2D 冻结包：已部分通过（包/资产/启动/17 卡解析），但还要 UI 发包或明确 waiver；
- SignPath：signed 或明确 waiver；
- 普通 z 序：非 topmost target 已通过；第三方应用或明确 waiver；
- 本文件提交到 `docs/`，并作为阶段 1 的基线。

阶段 0 不做引擎代码改动；阶段 1 才进入 `FrameStats`、trace 和 `--headless`。
