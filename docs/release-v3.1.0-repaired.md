## v3.1.0 安装修复版（2026-11-27 重发）

原 v3.1.0 的 3D 包有两个安装问题：`whale3d.exe` 是 console subsystem，启动会多弹一个终端框；安装器写死 `%LOCALAPPDATA%\WhaleGirlPet3D`，不询问安装目录，也不适合从旧版 2D 3.0.27 升级。

本次保留 **3.1.0** 版本号，替换 v3.1.0 Release 的安装包与便携包，只修发布链路，不改渲染/动画功能。最新版本仍是 **v3.1.1**；新环境优先下 v3.1.1，已经收藏 v3.1.0 链接的用户现在拿到的是修复包。

### 修复

| 项 | 改动 | 验收 |
|---|---|---|
| 终端框 | 用 v3.1.0 源码重新构建，`-mwindows`，PE subsystem=2；加 `3.1.0.0` 文件版本资源 | exe 1,316,864 B，SHA256 `04B248765B724F6F1471D7E56F8156812559D8B86C496858553F5BCBDD350C5B`；FileVersion/ProductVersion `3.1.0.0`；subsystem 2；GUI 启动测试通过 |
| 安装位置 | 恢复 `DisableDirPage=no`；`DefaultDirName={code:GetPreferredDir}`；`UsePreviousAppDir=no`；检测旧版 2D 时默认 `F:\WhaleGirlPetApp`，否则 `%LOCALAPPDATA%\WhaleGirlPet3D` | 安装器版本信息 `3.1.0.0`；目录页可改路径；不需要管理员权限 |
| 旧版 2D | 旧卸载器仍会报 `Cannot call ExtractTemporaryFile function during Uninstall`；安装器改为调用内嵌 `migrate_legacy.ps1`，保留设置/账号/记忆/语音/模型，删除旧程序、快捷方式和旧卸载登记 | 迁移脚本在等价副本上 exit 0、数据保留、旧程序与旧键移除；真实 19 GB 旧数据未执行完整迁移 |

### 资产

| 文件 | 大小 | SHA256 |
|---|---:|---|
| `WhaleGirlPet-3D-Setup-3.1.0.exe` | 4,417,521 B | `C4E0DBC20F4E26D9A85892CB64E9F1468CE6C71D1506754F27C865EAF34E0EB0` |
| `whale3d-whale-girl-v2.zip` | 2,805,751 B | `DA00B3ACDD22AC110A3333791DB76B91AF1F6C6D2E3B513D49A1724900F81EB4` |
| `whale3d.exe`（包内） | 1,316,864 B | `04B248765B724F6F1471D7E56F8156812559D8B86C496858553F5BCBDD350C5B` |

### 校验

```powershell
certutil -hashfile WhaleGirlPet-3D-Setup-3.1.0.exe SHA256
certutil -hashfile whale3d-whale-girl-v2.zip SHA256
```

### 边界

- 安装包**未签名**。发布时 SignPath Foundation 申请在审核；该申请后于 2026-11-27 未通过。SmartScreen 若提示“未知发布者”，先核对同名 `.sha256`。
- v3.1.0 修复包只保证安装链路；渲染能力仍是 3.1.0 的 VRM + 4 条 SpringBone，不含 v3.2 情绪总线和 v3.1.1 的 face cross-fade。
- 真实 `F:\WhaleGirlPetApp` 的 19 GB 用户数据没有在本轮删除或迁移；升级前仍建议先备份。

## Code signing policy

Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

The project submitted its SignPath Foundation OSS application on 2026-11-26; this release remains unsigned until approval. Policy: [`CODE_SIGNING_POLICY.md`](https://github.com/cnbprd/WhaleGirlPet/blob/main/CODE_SIGNING_POLICY.md). Privacy: [`PRIVACY.md`](https://github.com/cnbprd/WhaleGirlPet/blob/main/PRIVACY.md).
