# 代码签名与 SmartScreen

## 当前状态

`WhaleGirlPet-3D-Setup-3.1.0.exe` 和 `WhaleGirlPet-3D-Setup-3.0.28.exe` 目前是**未签名**的 Inno Setup 安装包。

- 本机证书库（`Cert:\CurrentUser\My`、`Cert:\LocalMachine\My`）没有可用的代码签名证书。
- 仓库里也没有 `.pfx` / `.p12` 代码签名私钥。
- 因此当前只能提供同名 `.sha256` 做完整性校验，无法消除 Windows SmartScreen 的“未知发布者”提示。

## 为什么不能靠改安装脚本解决

SmartScreen 校验的是 Authenticode 签名及其证书链，不读取安装脚本里的说明文字。没有受信任证书时：

- 不签名：公开分发会出现较强的 SmartScreen 拦截。
- 自签名：默认只适合本机测试；公开用户没有安装你的根证书，仍会被拦截，不能当成正式发布方案。
- 只改 README / Release 文案：不会改变 SmartScreen 行为。

## 可选路径

| 方案 | 适用性 | 需要什么 |
|---|---|---|
| **SignPath Foundation**（开源免费，OV 级托管签名） | 最适合当前公开 MIT 项目 | 在 [signpath.org](https://signpath.org/) 申请，审核通过后把签名接入 GitHub Actions |
| **Azure Artifact Signing**（原 Trusted Signing） | 微软当前推荐的非商店分发方案 | Azure 订阅、身份验证和签名账户 |
| **传统 OV 代码签名证书**（DigiCert / Sectigo / GlobalSign 等） | 可脱离 Azure 使用 | 付费证书，通常配 HSM/硬件令牌；导出 PFX 或使用证书指纹 |
| **Microsoft Store MSIX** | 商店分发免签名 | 需要打包 MSIX 并通过商店认证，当前 EXE 发布链路不适用 |

参考：[Microsoft 代码签名选项](https://learn.microsoft.com/en-ca/windows/apps/package-and-deploy/code-signing-options)、[SignPath Foundation](https://signpath.org/)。

## 拿到证书后的签名顺序

1. 先签安装包内的 `whale3d.exe`，再重新打 ZIP / 安装包，避免只签外壳、内部 exe 仍是未签名。
2. 编译 `WhaleGirlPet-3D-Setup-<version>.exe`。
3. 签安装包。本机没有 `signtool.exe`，可先用 PowerShell 自带的 `Set-AuthenticodeSignature`（需要证书带私钥，且在 `Cert:\CurrentUser\My` 或 PFX 导入后）：
   ```powershell
   $cert = Get-Item Cert:\CurrentUser\My\<thumbprint>
   Set-AuthenticodeSignature -FilePath .\dist\3d\WhaleGirlPet-3D-Setup-3.1.0.exe `
     -Certificate $cert -TimestampServer http://timestamp.digicert.com -HashAlgorithm SHA256
   ```
   如果使用 `signtool`，命令是 `signtool sign /fd SHA256 /tr <timestamp-url> /td SHA256 /sha1 <thumbprint> <file>`；有 PFX 时加 `/f`、`/p`。
4. 用 `Get-AuthenticodeSignature`（或 `signtool verify /pa /v`）复核，状态应为 `Valid`；自签名通常是 `UnknownError`，不能作为公开发布。
5. 重新生成 `.sha256` 并上传 Release，替换旧的未签名资产。

> OV/EV 签名解决“未知发布者”，但 SmartScreen 信誉仍需时间积累；不能承诺签名后所有机器立刻零提示。

## 最短路径（当前 MIT 公开仓库）

1. 用仓库所有者账号登录 [SignPath Foundation](https://signpath.org/)，提交项目：公开仓库 `cnbprd/WhaleGirlPet`、MIT 许可证、构建脚本 `installer/build_3d_installers.ps1`。
2. 审核通过后，把 `whale3d.exe` 与 Setup 的签名步骤接入 GitHub Actions 或 SignPath 的托管构建；签名后再上传 Release。
3. 若不想走审核，则购买 OV 证书（DigiCert / Sectigo / Certum 等），把 PFX + 密码或证书指纹交给我，我在本机按上面的顺序签。

## 需要提供的信息

要真正生成签名安装包，需要以下任一项：

- 代码签名 PFX 的路径和密码；或
- 证书库中代码签名证书的 SHA1 指纹；或
- SignPath / Azure Artifact Signing 的项目与签名凭据。
