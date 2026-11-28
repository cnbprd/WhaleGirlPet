# 代码签名与认证预检

时间：2026-11-27 18:55 左右  
方式：只查本机证书库、Authenticode 状态、SignPath 文档记录和仓库策略；未签名、未上传、未触发 CI。

## 结果

| 项 | 结果 | 状态 |
|---|---|---|
| GitHub CLI 认证 | `gh` 2.105.0，账号 `cnbprd`，`repo` scope | PASS |
| 用户证书库 | `Cert:\CurrentUser\My` 代码签名证书 0 张 | 缺证书 |
| 机器证书库 | `Cert:\LocalMachine\My` 代码签名证书 0 张 | 缺证书 |
| `3d\whale3d.exe` | `Get-AuthenticodeSignature` 为 `NotSigned` | 未签名 |
| `dist\3d\WhaleGirlPet-Setup-3.2.0-sprite.exe` | `Get-AuthenticodeSignature` 为 `NotSigned` | 未签名 |
| `signtool.exe` | 本机 PATH 与 Windows Kits 均未找到 | 缺工具 |
| SignPath | 2026-11-26 提交；2026-11-27 邮件回复未通过（公开可见度不足） | 未通过，未签发 |
| SignPath 申请截图 | `docs/_signpath_application_submitted.png` 存在 | 有证据 |
| `PRIVACY.md` | 存在 | 有材料 |
| 签名策略 | `CODE_SIGNING_POLICY.md` 已把产品版本改为 `3.2.0.0`、安装器名称改为 `鲸鱼娘` | 已同步 |

## 现在能做的

- 保持 GitHub / SignPath 账号 MFA；不要把 token、PFX 密码写进仓库或文档；
- 保持 `CODE_SIGNING_POLICY.md`、`PRIVACY.md`、`3d-build.yml` 与当前 3.2.0.0 构建一致；
- 发布前先签 `whale3d.exe`，再打 ZIP/安装器，最后签安装器并重算 `.sha256`；
- 先跑 `verify_release_assets.py` 和 `Get-AuthenticodeSignature`，确认未签名状态没有被误写成已签名。

## 现在不能做的

- 不能实际签 `whale3d.exe` 或安装器：证书库为空，SignPath Foundation 已拒绝；
- 不能用自签名冒充正式发布：公开用户没有根证书，SmartScreen 仍会拦截；
- 不能只改 README/Release 文案来消除 SmartScreen；
- 不能在没有证书的情况下把“已签名”写进 Release notes。

## 可选路径

1. SignPath Foundation 免费路径：本次已拒绝；先积累公开可见度，再重新申请。
2. 购买 OV 代码签名证书，提供 PFX/证书指纹；本机可先用 `Set-AuthenticodeSignature`。
3. Azure Artifact Signing（原 Trusted Signing）：需要 Azure 订阅和签名账户，当前未配置。
4. SignPath 付费订阅：跳过 Foundation 审核，按 `https://docs.signpath.io/change-subscription` 走。

## 限制

- 2026-11-27 已收到 SignPath 明确拒绝邮件；2026-11-28 门户复查账号下无组织/项目，和拒绝结果一致；
- 没有检查 GitHub 组织策略、分支保护或 MFA 实际状态；
- 没有执行任何签名命令。
