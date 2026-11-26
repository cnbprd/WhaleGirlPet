# 3.1.2 安装链路实测与 2D 对比

日期：2026-11-27  
范围：`installer/whale3d.iss`、测试版 `WhaleGirlPet-Setup-3.1.2-test.exe`、2D `installer/whale_pet.iss`

## 结论

3.1.2 的安装器有两个实际问题：

1. **升级默认目录没有沿用已有 3D 安装位置**：之前只看旧 2D 注册表，否则固定 `F:\WhaleGirlPetApp`；装在 D 盘/自定义目录的 3D 版升级时，默认会被拉回 F 盘。
2. **旧 2D→3D 迁移脚本在 Inno 里一调用就 `Type Mismatch`**：`GetDateTimeString('yyyymmdd-hhnnss', '', '')` 的空字符串分隔符参数类型不对，迁移还没开始就失败。这解释了“迁移没有完整跑完”。

两个都已在 `installer/whale3d.iss` 修复，并用隔离目录/伪造旧版注册表实测通过；**真实 `F:\WhaleGirlPetApp` 的 18.7 GB 数据没有动**。

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

## 测试 3：和 2D 安装器对比

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
- 生产包：`dist/3d/WhaleGirlPet-Setup-3.1.2.exe`，4,418,739 B / SHA256 `5AECE5A333A0AF8B5D357F32FF1E10F4438614F976911E8AE81E68E124D0A3D2`。
- 旧包备份测试后已清理；线上 Release 仍是旧包。

## 边界

- 真实 18.7 GB `F:\WhaleGirlPetApp` 仍未迁移；本次只在最小伪造目录验证逻辑。真正升级前仍应先备份用户数据。
- 安装包未签名，SignPath 仍在审核。
- 2D 安装器未改；它是历史归档，不再作为新发布目标。
- 生产包 `dist/3d/WhaleGirlPet-Setup-3.1.2.exe` 已在本地重建，但尚未上传 Release；线上 v3.1.2 资产仍是旧包。
