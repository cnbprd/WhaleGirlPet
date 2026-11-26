# 鲸鱼娘 3.1.2（安装修复版，2026-11-27）

这是一次安装与发布链路修正，不改变 3D 渲染和动画功能。重点是把安装器名称统一成“鲸鱼娘”、默认目录优先沿用已有 3D 安装位置，并修复旧 2D→3D 迁移的 Inno `Type Mismatch`。

> 本版是 **v3.1.2 的替换资产**，不是新 tag。原安装包会在旧 2D 数据上升级时报 `Type Mismatch`，请使用本页的新包。

## 改了什么

1. **应用名统一为“鲸鱼娘”**
   - 安装器 `AppName / AppVerName / DefaultGroupName / UninstallDisplayName / SetupWindowTitle / VersionInfoDescription` 全部去掉“3D”。
   - 3D 窗口标题从 `WhaleGirl 3D Placeholder` 改为 `鲸鱼娘`。
   - 托盘提示改为 `鲸鱼娘 · 桌面宠物`，设置页标题改为 `鲸鱼娘 · 设置`。

2. **默认安装目录不再落到 C 盘**
   - 已有 3D 安装：优先读 `WhaleGirlPet3D_is1` 的 `InstallLocation`，升级不丢自定义目录。
   - 有旧版 2D：默认升级到旧目录。
   - 都没有：有 F 盘时默认 `F:\WhaleGirlPetApp`，否则回退 `%LOCALAPPDATA%\WhaleGirlPet3D`。
   - 目录页保留，安装位置仍可手动修改。

3. **旧 2D→3D 迁移修复**
   - 旧 2D 卸载器在 `InitializeUninstall()` 调 `ExtractTemporaryFile()`，Inno 直接拒绝；所以不调用旧卸载器。
   - 改由 `installer/art/migrate_legacy.ps1` 迁移：先把 `config.json / accounts.json / memory.db / knowledge.db / accounts / voices / tts_cache / workspace / reports / quarantine / scripts / models / runtime / updates / ollama_library.json` 移到临时备份，删除 `_internal`、`WhaleGirlPet.exe`、旧 `unins000.*`、旧快捷方式和旧卸载登记，再把数据移回。
   - 修复 `GetDateTimeString('yyyymmdd-hhnnss', '', '')` 的空分隔符参数类型错误，改为 `GetDateTimeString('yyyymmdd-hhnnss', '-', ':')`。

4. **安装包文件名去掉 `-3D-`**
   - 新文件名为 `WhaleGirlPet-Setup-3.1.2.exe`。

## 资产

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `WhaleGirlPet-Setup-3.1.2.exe` | 4,418,739 | `5AECE5A333A0AF8B5D357F32FF1E10F4438614F976911E8AE81E68E124D0A3D2` |
| `WhaleGirlPet-Setup-3.1.2.exe.sha256` | 98 | 同上的文本校验文件 |
| `whale3d-whale-girl-v3.zip` | 2,809,199 | `A98008C569A4A5686FA136EA091C0D1EAB4B338058B6D97D23433EE6EB8273C3` |
| `whale3d.exe`（包内） | 1,323,520 | `F67F2E00EB1C12CF63A44CEB8A1ADBBD7C61166A6BD4E0D8102A315123E00E84` |

## 实测

- **已有 3D 目录**：伪造 `WhaleGirlPet3D_is1` 指向自定义目录，静默安装不带 `/DIR`，exit 0，`whale3d.exe` 落在自定义目录。
- **伪造旧 2D**：最小旧目录迁移 exit 0，数据保留、旧程序/旧键移除。
- **真实 18.673 GB 升级**：`F:\WhaleGirlPetApp` 不传 `/DIR` 运行生产包，exit 0；日志 `PrepareToInstall: existing3d=0 legacy=1 app=F:\WhaleGirlPetApp`、`MigrateLegacy: exit=0`；升级后 18.501 GB，`whale3d.exe` 落盘，`config.json` / `accounts.json` / `memory.db` / `knowledge.db` / `tts_cache` 保留，旧 2D 程序文件和旧键移除，新键 `WhaleGirlPet3D_is1` 建立。
- 安装器窗口标题：`安装鲸鱼娘 3.1.2`
- 3D 主窗口标题：`鲸鱼娘`
- exe `FileVersion/ProductVersion`：`3.1.2.0`
- PE subsystem：`2`（GUI，不额外弹终端框）

## 发布状态

v3.1.2 Release 的同名资产已替换为上面的新包；从 GitHub 重新下载后校验为 4,418,739 B / `5AECE5A333A0AF8B5D357F32FF1E10F4438614F976911E8AE81E68E124D0A3D2`。tag 仍为 `v3.1.2`，未改版本号。

## 边界

- 安装包仍未签名，SignPath Foundation 的申请仍在审核。
- 本版只改安装器与命名，不改 3D 渲染/动画；ZIP 内的 `whale3d.exe` 与上一版相同。
- 真实迁移只在本机 `F:\WhaleGirlPetApp` 验证；其他机器的自定义目录/不同盘符未逐一实跑。
- 升级前用户数据备份仍保留在本地 `build/userdata-before-3d-upgrade`，不在 Release 资产里。
