# 2D 冻结包与安装器静态审计

日期：2026-11-27  
范围：`WhaleGirlPet.spec`、`installer/whale3d.iss`、`installer/build_3d_installers.ps1`、`installer/whale_pet.iss`、`tools/release.ps1`，以及现有 ZIP / payload staging。  
方式：只读文件、只解析脚本；没有 PyInstaller 构建、没有 ISCC 编译、没有安装器安装、没有启动第二个 3D。

## 结论

2D 冻结包的素材声明没有发现问题；**3D 安装器的自动构建脚本有一个可复现性问题**：当前 `build_3d_installers.ps1` 的包列表只有 `3.2.0-dev`，没有 `3.2.0-sprite`。现有的 `WhaleGirlPet-Setup-3.2.0-sprite.exe` 能存在，说明它是按单独参数手工编出来的；如果下次直接跑脚本，产物会是 dev，不是 sprite。

## P1：安装器构建脚本缺少 sprite 包

`installer/build_3d_installers.ps1` 原列表：

```text
3.2.0 -> 3d\whale3d-whale-girl-v3.2-dev.zip  (-dev)
```

当前需要发布的 ZIP 是：

```text
3d\whale3d-whale-girl-v3.2-sprite.zip
```

ZIP 内已确认包含：

- `whale3d.exe`
- `assets/ui/pet.ico`
- `assets/2d_bridge/atlas.png`
- `assets/2d_bridge/manifest.json`

现有 staging `build\3d-installer-payload\3.2.0-sprite\assets\2d_bridge` 也包含上述两个 2D 文件。

### 修复草稿

已在独立分支准备：

- worktree：`F:\WhaleGirlPet\build\worktrees\fix-installer-sprite`
- 分支：`fix/installer-build-sprite`
- commit：`86b139b`（`fix(installer): build the sprite 3.2 payload reproducibly`）

改动：

- 包列表新增 `3.2.0-sprite`；
- 每个包增加独立 `PayloadKey`，避免 `3.2.0-sprite` 和 `3.2.0-dev` 共用同一个 `build\3d-installer-payload\3.2.0` 目录；
- 失败信息带上 suffix，避免只看到 `3.2.0` 分不清是哪个包。

已用 PowerShell Parser 解析通过；**未运行 ISCC、未构建、未安装**。

## 2D 冻结包

`WhaleGirlPet.spec`：

- `datas` 第 4 行显式包含 `('assets/2d_bridge', 'assets/2d_bridge')`；
- `EXCLUDES` 排除了 `PIL`，但 `app/asset_bridge.py` 只用 `json`、`pathlib`、`socket` 等，不依赖 PIL，静态上没有冲突；
- `COLLECT` 是 onedir；冻结后 `paths.resource_path()` 走 `sys._MEIPASS`，素材会落在 `_internal/assets/2d_bridge`，安装器复制整个 `dist\WhaleGirlPet`，路径上可达。

这部分静态结论：**2D 素材声明完整，没有发现漏包。**

## P2：2D 旧发版链路版本号不一致

`tools/release.ps1`：

- 从 `app/paths.py` 读 `APP_VERSION`；当前是 `3.1.0`；
- 构建后检查 `dist\WhaleGirlPet-Setup-$new.exe`。

`installer/whale_pet.iss`：

- `OutputBaseFilename=WhaleGirlPet-Setup-3.0.27`，版本号写死。

因此如果直接跑 `release.ps1` 的 2D 打包路径，预期文件名和实际输出名不一致，可能报“没找到安装包”。这属于旧 2D 发版链路，不应作为 3.2 sprite 的发布入口；建议明确标注为 deprecated，或另开分支统一版本号。

## 未发现问题的项

- `whale3d.iss` 的 `Source: "{#PayloadDir}\*"` 会递归复制 payload；只要 payload 是 sprite ZIP 解出来的，`assets/2d_bridge` 会进安装目录。
- `SetupIconFile=..\3d\assets\ui\pet.ico` 存在。
- `AppId=WhaleGirlPet3D` 固定，升级覆盖路径与旧安装器一致。
- `VersionInfoVersion={#AppVersion}.0` 在 `AppVersion=3.2.0` 时有效；sprite 只应放在 `BuildSuffix`，不要写成 `AppVersion`。
- 安装器 `CloseApplications=yes` 会在安装时关闭正在运行的 `whale3d.exe`；这正是不能在 24h 浸泡期间安装的原因。

## 发布前建议

1. 把 `fix/installer-build-sprite` 的改动合入后，才把 `build_3d_installers.ps1` 作为 3.2 sprite 安装器的可复现构建入口。
2. 2D 旧链路 `release.ps1` / `whale_pet.iss` 先标 deprecated，不要和 3D sprite 发布混用。
3. 重新构建安装器必须等 24h 浸泡结束，且输出到临时目录，不覆盖当前生产 `3d\whale3d.exe`。

## 证据文件

- `F:\WhaleGirlPet\WhaleGirlPet.spec`
- `F:\WhaleGirlPet\installer\whale3d.iss`
- `F:\WhaleGirlPet\installer\build_3d_installers.ps1`
- `F:\WhaleGirlPet\installer\whale_pet.iss`
- `F:\WhaleGirlPet\tools\release.ps1`
- `F:\WhaleGirlPet\3d\whale3d-whale-girl-v3.2-sprite.zip`
- `F:\WhaleGirlPet\build\3d-installer-payload\3.2.0-sprite\assets\2d_bridge`
