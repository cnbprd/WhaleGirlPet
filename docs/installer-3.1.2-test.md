# 3.1.2 安装链路实测与 2D 对比

日期：2026-11-27  
范围：`installer/whale3d.iss`、测试版 `WhaleGirlPet-Setup-3.1.2-test.exe`、2D `installer/whale_pet.iss`

## 结论

3.1.2 的安装器有两个实际问题：

1. **升级默认目录没有沿用已有 3D 安装位置**：之前只看旧 2D 注册表，否则固定 `F:\WhaleGirlPetApp`；装在 D 盘/自定义目录的 3D 版升级时，默认会被拉回 F 盘。
2. **旧 2D→3D 迁移脚本在 Inno 里一调用就 `Type Mismatch`**：`GetDateTimeString('yyyymmdd-hhnnss', '', '')` 的空字符串分隔符参数类型不对，迁移还没开始就失败。这解释了“迁移没有完整跑完”。

两个都已在 `installer/whale3d.iss` 修复，并用隔离目录/伪造旧版注册表实测通过；**真实 `F:\WhaleGirlPetApp` 的 18.673 GB 数据也已在 2026-11-27 01:51 完成升级**，exit 0，数据保留、旧 2D 程序与旧卸载登记移除。

## 测试 1：已有 3D 安装，默认沿用自定义目录

做法：临时创建 `WhaleGirlPet3D_is1` 注册表项，`InstallLocation` 指向 `F:\WhaleGirlPet\build\installer-preferred-test`，然后静默安装测试包（不带 `/DIR`）。

结果：

- installer exit `0`
- `whale3d.exe` 落在伪造的已有目录，不是 `F:\WhaleGirlPetApp`
- 安装器正常写入自己的卸载信息

这条证明 `GetPreferredDir()` 的优先级已变为：**已有 3D 目录 → 旧 2D 目录 → F 盘 → LocalAppData**。目录页仍保留（`DisableDirPage=no`），用户可改。

## 测试 2：旧 2D→3D 迁移

做法：用伪造的旧版目录 `F:\WhaleGirlPet\build\legacy-migration-test`，放入 `WhaleGirlPet.exe`、`_internal`、`unins000.*`、`config.json`、`accounts.json`、`memory.db`、`knowledge.db`、`models` 等最小样本；临时把旧版注册表指向该目录，运行测试安装包。真实旧版注册表在测试前备份、测试后恢复。

结果：

- installer exit `0`
- `whale3d.exe` 已安装
- 旧 `WhaleGirlPet.exe` 已删除
- `config.json` / `accounts.json` / `memory.db` / `knowledge.db` 保留
- 旧卸载登记被移除
- 日志：`MigrateLegacy: exit=0`，随后 `Successfully installed the file`

修复前同一路径报：

```
Runtime error (at 11:305):
Type Mismatch.
```

修复点：`GetDateTimeString('yyyymmdd-hhnnss', '-', ':')`，不再传空字符串分隔符。

## 测试 3：真实 18.7 GB 升级

备份：`F:\WhaleGirlPet\build\userdata-before-3d-upgrade`（9.44 MB，含 `config.json`、`accounts.json`、`memory.db`、`knowledge.db`、`accounts`、`voices`、`tts_cache`、`workspace`、`reports`、`quarantine`、`scripts`、`ollama_library.json` 和旧卸载键 JSON）。

做法：不传 `/DIR`，让 `GetPreferredDir()` 读旧 2D 键，默认到 `F:\WhaleGirlPetApp`；`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART` 运行生产包。

结果：

- installer exit `0`
- 日志：`PrepareToInstall: existing3d=0 legacy=1 app=F:\WhaleGirlPetApp legacyDir=F:\WhaleGirlPetApp`、`MigrateLegacy: exit=0`
- 目录从 18.673 GB 变为 18.501 GB（减少的是旧 2D 程序文件）
- `whale3d.exe` 已落盘；旧 `_internal` / `WhaleGirlPet.exe` 已删除
- `config.json` 926 B、`accounts.json` 156 B、`memory.db` 24,576 B、`knowledge.db` 16,384 B、真实 TTS 缓存 69,264 B 均保留
- 旧键 `鲸鱼娘桌宠_is1` 已移除；新键 `WhaleGirlPet3D_is1` 建立，`UninstallString` 指向新的 `unins000.exe`
- 迁移临时备份目录已自动清理，没有残留 `WhaleGirlPetApp_userdata_*`

## 测试 4：和 2D 安装器对比

| 项 | 2D `whale_pet.iss`（3.0.27） | 3D `whale3d.iss`（3.1.2 修复后） |
|---|---|---|
| 目录页 | `DisableDirPage=yes`，自建“要把我装到哪儿呀？”页 | 标准 Inno 目录页，`DisableDirPage=no` |
| 默认目录 | 固定 `%LOCALAPPDATA%\WhaleGirlPetApp` | 已有 3D 目录 → 旧 2D 目录 → `F:\WhaleGirlPetApp` → `%LOCALAPPDATA%\WhaleGirlPet3D` |
| 用户改路径 | 有“浏览…选盘”，选盘根自动补 `WhaleGirlPetApp` | 标准目录框可直接输入/浏览 |
| 升级识别 | 没有读取旧安装位置，重装仍回 C 盘默认 | 读取 `WhaleGirlPet3D_is1` 的 `InstallLocation`，升级不丢自定义目录 |
| 旧版迁移 | 旧卸载器本身的 `ExtractTemporaryFile` bug 不可调用 | 安装器内 `migrate_legacy.ps1` 迁移，保留数据、删旧程序/旧登记 |

2D 的“给用户选择”是自建页 + 浏览；3D 用标准目录页，选择能力等价，但升级默认目录更准确。

## 产物

- 测试包：`WhaleGirlPet-Setup-3.1.2-test.exe`，仅测试；与生产包内容/哈希相同（`BuildSuffix` 只改输出文件名），测试后已清理。
- 生产包：`dist/3d/WhaleGirlPet-Setup-3.1.2.exe`，4,418,739 B / SHA256 `5AECE5A333A0AF8B5D357F32FF1E10F4438614F976911E8AE81E68E124D0A3D2`；真实升级使用此包。
- 线上 Release 的替换见 `docs/release-v3.1.2.md`。

## 边界

- 真实 18.7 GB `F:\WhaleGirlPetApp` 已在本机升级通过；其他机器的真实数据（尤其是自定义目录、不同盘符）未逐一实跑。
- 安装包未签名，SignPath 仍在审核。
- 2D 安装器未改；它是历史归档，不再作为新发布目标。
- 升级前备份仍在 `build/userdata-before-3d-upgrade`，确认稳定后可删除。
