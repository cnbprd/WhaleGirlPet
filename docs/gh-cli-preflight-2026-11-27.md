# GitHub CLI 发布路径预检

时间：2026-11-27 16:05 左右  
方式：只查本地 CLI、认证状态和命令帮助；未上传资产、未触发 workflow、未创建 Release。

## 结果

| 项 | 结果 | 状态 |
|---|---|---|
| `gh` 路径 | `C:\Program Files\GitHub CLI\gh.exe` | PASS |
| 版本 | `gh 2.105.0 (2026-11-17)` | PASS |
| 登录 | `github.com`，账号 `cnbprd`，keyring 认证 | PASS |
| token scopes | `gist`、`read:org`、`repo` | PASS |
| `gh release upload` | `--help` exit 0 | PASS |
| `gh workflow run` | `--help` exit 0 | PASS |
| 远程仓库读取 | `gh release view v3.2.0-dev --repo cnbprd/WhaleGirlPet` exit 0 | PASS |

`GH_TOKEN` / `GITHUB_TOKEN` 环境变量未设置；当前认证来自 `gh` keyring，不依赖临时环境变量。

## 结论

- 发布阶段可以直接用 `gh release create/upload`；
- 新的 tag 级 `release-notes.yml` 可以用 `gh workflow run release-notes.yml -f tag=v3.2.0-sprite` 触发；
- `repo` scope 足够覆盖当前仓库的 Release 和 workflow dispatch 操作；
- 不需要改网页替代路径。

## 未验证

- 没有实际上传文件；
- 没有实际触发 workflow；
- 没有检查 GitHub 网页端的组织策略/分支保护；
- 没有检查 code signing / SignPath 流程。

## 对 runbook 的影响

第 5.3 节的 `gh` 命令可以直接使用；如果未来 `gh` 认证失效，先运行 `gh auth login`，不要改用带明文 token 的命令写进文档。
