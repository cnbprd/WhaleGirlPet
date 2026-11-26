# 鲸鱼娘 3D 3.1.1

这次只修发布链路，不改渲染/动画功能。

## 修复

1. **终端框**：`whale3d.exe` 重新按 GUI subsystem 构建（PE subsystem 2），不会再额外带一个控制台窗口；日志改写到 exe 同目录的 `whale3d.log`，可用 `WHALE3D_LOG` 覆盖路径。
2. **安装位置**：安装向导恢复“选择安装目录”页，默认 `%LOCALAPPDATA%\WhaleGirlPet3D`，不需要管理员权限；可以点 Browse 改到其他目录。
3. **旧版 2D 升级**：检测到 3.0.27 时默认回到旧版安装目录。旧版卸载器自身会在卸载时调用 `ExtractTemporaryFile`，Inno 直接报 `Cannot call ExtractTemporaryFile function during Uninstall`，所以 3.1.1 不再调用它，改为由安装器直接迁移：保留设置、账号、记忆、语音、模型等用户数据，删除旧程序文件、快捷方式和旧卸载登记。
4. **3D CI**：新增 `.github/workflows/3d-build.yml`，用 w64devkit 2.11.0 + SDL3 3.4.20 在 GitHub Actions 构建 `whale3d.exe`，校验 GUI subsystem 和版本号，并上传便携 ZIP artifact；首次运行 `45854256592` 通过（53 秒），release 使用的 exe 来自该 artifact。SignPath 申请表里的 Build System 现在与仓库实际构建方式一致。
5. **安装包**：`WhaleGirlPet-3D-Setup-3.1.1.exe`，4,419,862 B，SHA256 `bb1a46f19425ab9e8f8cf7ec02eb931a3991f95ac1b31703d3e06b09970b6e76`。

## 资产

| 文件 | 大小 | SHA256 |
|---|---:|---|
| `WhaleGirlPet-3D-Setup-3.1.1.exe` | 4,419,862 B | `96FD16551759B8E493FABCBBE638ACA4F8B3292B40DCDE2B6F181C8EB078897C` |
| `whale3d-whale-girl-v3.zip` | 2,809,167 B | `4DB8C1D5884C069363C4F7F0B8BCE8DDA73D44D3D85242B18F687D6A6CA9794E` |
| `whale3d.exe`（包内） | 1,323,520 B | `CCCA98BB05BB40332DF80A3BFD0E11AEF71D926DFB60C0432C5C210218C832E0` |

## 验证

- GUI 目检：安装向导显示目录选择页，检测到 3.0.27 时路径框默认 `F:\WhaleGirlPetApp`，Browse 可用。
- 迁移脚本在 `F:\WhaleGirlPetApp_migration_test` 的等价副本上实测：exit 0；`config.json`、`accounts`、`models` 等保留；`_internal`、`WhaleGirlPet.exe`、旧卸载键全部移除。
- `whale3d.exe` 验收：PE subsystem 2，ProductVersion/FileVersion `3.1.1.0`，日志 `fps=27.5 update_us=8.75`。

## 边界

- 安装包**仍未签名**。SignPath Foundation 申请已提交、仍在审核；SmartScreen 可能显示“未知发布者”，请先对照 `.sha256`。
- 没有在真实 `F:\WhaleGirlPetApp` 的 19 GB 数据上跑完整升级；迁移脚本只在等价副本上验证。正式升级前建议先备份旧目录。
- 如果迁移中途被强制结束，旧目录里会留下 `WhaleGirlPetApp_userdata_<timestamp>` 备份；数据不会主动删除，可人工移回。
