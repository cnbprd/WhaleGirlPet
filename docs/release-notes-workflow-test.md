# release-notes workflow 本地行为测试

时间：2026-11-27 16:10 左右  
对象：分支 `fix/release-notes-tag` 的 `.github/workflows/release-notes.yml`。  
方式：用假 `gh` 脚本替换网络调用；未联网、未触发 GitHub Actions、未编辑任何 Release。

## 测试方法

- 从 YAML 抽出 `run` 脚本；
- 造一个本地 `gh` 替身：`release view` 返回可配置退出码，`release edit` 只记录参数；
- 四个 case 分别是：
  1. 合法 tag `v3.2.0-sprite`，notes 存在，Release 存在；
  2. 非法 tag `../bad`；
  3. notes 缺失 `v9.9.9`；
  4. Release 不存在（`v3.2.0-sprite` + `view` 返回 1）。

## 结果

```text
PASS valid_tag exit=0 edit=1
PASS invalid_tag exit=1 no_edit
PASS missing_notes exit=1 no_edit
PASS missing_release exit=1 no_edit
TEST_EXIT=0
```

四条路径符合预期：

- 合法 tag 只调用一次 `release edit`，参数包含 `--notes-file` 和 `docs/releases/v3.2.0-sprite.md`；
- 非法 tag 在调用 `gh` 前拒绝；
- notes 缺失在调用 `gh` 前拒绝；
- Release 缺失在 `release view` 后拒绝，没有执行 `release edit`。

## 限制

- 假 `gh` 不验证真实 GitHub 权限、组织策略或 API 行为；
- 没有验证 `gh` 对 tag 的实际解析；
- 没有触发真实 workflow；
- 测试脚本使用本机 Git Bash 和本地假 `gh`，不是 CI 测试。

## 结论

单 tag 分支的本地控制流成立；真实 GitHub Actions 仍要等发布阶段触发验证。
