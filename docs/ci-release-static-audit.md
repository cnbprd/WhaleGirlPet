# CI / Release 流程静态审计

日期：2026-11-27  
范围：`.github/workflows/3d-build.yml`、`.github/workflows/release-assets.yml`、`.github/workflows/release-notes.yml`，以及 `installer/build_3d_installers.ps1`、`installer/whale_pet.iss`、`app/paths.py`、`DECLARATION.md` 的相关版本/发布逻辑。  
方式：只读文件、只解析 YAML 和脚本；没有触发 workflow、没有运行 ISCC/PyInstaller、没有安装、没有启动第二个 3D。

## 结论

3D 发布链路是“**本地打包 + 本地上传**”，CI 只做 3D exe/ZIP 构建和产物归档，不自动发 Release。这个方向本身没问题，但当前有两个高风险点：

1. `release-assets.yml` 仍是手动可触发的 2D 发布流程，带 `contents: write` 和 `gh release upload --clobber`，且版本号与 2D 安装器输出不一致；误触可能覆盖已有 Release 资产。
2. `3d-build.yml` 的 artifact 名仍写着 `whale3d-v3.1.2-ci`，而实际产物是 3.2.0.0 / sprite ZIP；CI 产物容易被误认成旧版。

## Workflow 映射

| Workflow | 触发 | 产物/动作 | 权限 | 是否发布 Release |
|---|---|---|---|---|
| `3d-build.yml` | push/PR `3d/**`，手动 | `whale3d.exe`、`whale3d-whale-girl-v3-ci.zip`、`.sha256` | `contents: read` | 否 |
| `release-assets.yml` | 仅手动 `workflow_dispatch` | 2D PyInstaller、2D 安装器、portable/source、`gh release upload --clobber` | `contents: write` | 是（手动） |
| `release-notes.yml` | push `docs/releases/*.md`，手动 | 遍历所有 release notes，`gh release edit` | `contents: write` | 只改说明，不改资产 |

## P1：2D 手动发布 workflow 可能覆盖 Release 资产

`release-assets.yml`：

- 仅 `workflow_dispatch`，但一旦手动触发，会执行 `gh release upload $tag $files --clobber`（第 104–105 行）。
- 版本来自 `app/paths.py` 的 `APP_VERSION = "3.1.0"`（第 20–24 行）。
- 安装器由 `installer/whale_pet.iss` 编译，但该文件写死 `AppVersion=3.0.27`、`OutputBaseFilename=WhaleGirlPet-Setup-3.0.27`（第 9–10、21 行）。
- 打包上传用 `Get-ChildItem dist -Filter "*$ver*"`，即 `*3.1.0*`（第 104 行）。这不会匹配新编出来的 `3.0.27` 安装器，却可能匹配 `dist` 里已有的旧 `WhaleGirlPet-Setup-3.1.0.exe`，于是把旧安装器当成新产物上传。
- `DECLARATION.md` 明确说 2D 已放弃，只保留手动归档；但该 workflow 没有确认参数、没有版本一致性断言，也没有环境保护。

**风险**：错误手动触发时，可能创建/更新 `v3.1.0` Release，并用旧 3.1.0 安装器覆盖资产；对 3.2 sprite 发布是噪声，也可能破坏历史 Release。

**建议**：

- 最安全：停用该 workflow 的 `workflow_dispatch`，或加一个必填 `confirm_2d_archive` 输入并在 job 首步 `if` 拒绝。
- 次选：在构建前断言 `whale_pet.iss` 的输出名与 `$ver` 一致；不一致直接 fail，不进入 upload。
- 上传前加 `if ($files.Count -eq 0) { throw }`，避免空资产上传。
- 不要在当前 3.2 sprite 发布周期运行它。

## P1：3D CI artifact 名称与版本不一致

`3d-build.yml`：

- 构建产物版本断言是 `ProductVersion -ne '3.2.0.0'`（第 83 行），对应 `whale3d.rc` 的 `3.2.0.0`。
- 但打包 ZIP 名是 `whale3d-whale-girl-v3-ci.zip`（第 100 行），上传 artifact 名是 `whale3d-v3.1.2-ci`（第 109 行）。
- 这不会自动发 Release，但会让人工下载 CI artifact 时误以为是 3.1.2 或非 sprite 包。

**建议**：统一改成 `whale3d-v3.2.0-ci` / `whale3d-whale-girl-v3.2.0-ci.zip`，或从 `whale3d.rc` 读取版本后生成名字。

**修复状态**：`fix/ci-artifact-name` 已改为从构建出的 `whale3d.exe` 读取 `ProductVersion`，生成 `whale3d-v3.2.0-ci` artifact 和 `whale3d-whale-girl-v3.2.0-ci.zip`；已随集成分支合入本地 `main`，尚未 push、未触发 CI。

## P2：3D CI 不构建安装器，Release 必须本地做

`3d-build.yml` 只复制 `whale3d.exe`、`SDL3.dll`、模型、`assets/2d_bridge` 并压 ZIP（第 87–104 行），没有 ISCC 步骤。  
`release-assets.yml` 是 2D 专用，不能拿来构建 3D 安装器。  
因此 3.2.0-sprite 的发布路径仍是：

1. `installer/build_3d_installers.ps1` 本地构建安装器；
2. `3d\tools\verify_release_assets.py` 本地校验；
3. 手动上传 ZIP + 安装器 + `.sha256` 到 `v3.2.0-sprite`。

这不是缺陷，但需要在发布说明里写清楚，避免有人等 CI 自动出安装器。

## P2：`release-notes.yml` 会遍历并改写所有已有 Release

`release-notes.yml` 原先在 `docs/releases/*.md` push 时遍历所有 notes 文件，对每个已存在的 tag 执行 `gh release edit`（第 29–33 行）。
它不改资产，但如果某个历史 notes 文件被修改，会连带改写对应旧 Release 的说明。现在已有 `docs/releases/v3.2.0-sprite.md`；如果把它 push 到 `main`，旧 workflow 可能在 tag 尚不存在时运行并遍历旧 notes。

**修复状态**：`fix/release-notes-tag` 已移除 push 触发，改为手动 `workflow_dispatch`，只接收一个 `tag` 输入，只更新 `docs/releases/<tag>.md` 对应的一个 Release；已随集成分支合入本地 `main`，尚未 push、未触发 workflow。

## P3：版本硬编码的维护点

- `whale3d.rc` 固定 `3.2.0.0`；
- `3d-build.yml` 固定断言 `3.2.0.0`；
- `installer/build_3d_installers.ps1` 的包列表固定 `3.2.0` / `-dev`；
- `installer/whale3d.iss` 默认 `AppVersion=3.1.2`，必须靠 `-DAppVersion` 覆盖。

这些在 3.2.0-sprite 当前版本可用，但下一版要同步改四处；建议以后把版本收敛到一个 `version.json` 或 `whale3d.rc` 派生变量。

## 对当前发布的建议

| 项 | 结论 |
|---|---|
| `release-assets.yml` | 不运行；2D 归档与 3.2 sprite 发布无关 |
| `3d-build.yml` | 只作为 CI 构建证据，不作为 Release 资产 |
| 3.2.0-sprite 资产 | 本地构建、`verify_release_assets.py` 38 项 PASS 后手动上传 |
| tag | `v3.2.0-sprite`，不要复用 `v3.2.0-dev` |
| Release notes | `docs/releases/v3.2.0-sprite.md` 已就绪；工作流已改为单 tag 手动触发，旧 push 遍历逻辑已合入本地 `main` |
| 远程状态 | 本地 `main` 领先 `origin/main`；尚未 push，remote 仍是旧 workflow；首次 push 后会更新为本地合并后的 workflow |

## 证据文件

- `.github/workflows/3d-build.yml`
- `.github/workflows/release-assets.yml`
- `.github/workflows/release-notes.yml`
- `installer/build_3d_installers.ps1`
- `installer/whale_pet.iss`
- `installer/whale3d.iss`
- `3d/whale3d.rc`
- `app/paths.py`
- `DECLARATION.md`
- `docs/package-static-audit.md`
- `docs/release-3.2.0-sprite.md`
