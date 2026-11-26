# 3.2.0-dev 安装器回归

日期：2026-11-27（Asia/Shanghai）

对象：`WhaleGirlPet-Setup-3.2.0-dev.exe`，4,424,684 B，SHA256 `7E859016691F0816AAD5A605C4035C37E9CF9D05653EF30C183F575874A8E5FF`。

## 目的与边界

只验证临时目录的全新安装、启动、卸载，不覆盖本机已有的 `F:\WhaleGirlPetApp` 3.1.2 安装。已有目录包含大量用户数据，本轮不做原地升级回归；升级路径需要在有备份的独立环境另测。

## 步骤与结果

| 检查项 | 结果 |
|---|---|
| 安装前保护 | 导出 `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\WhaleGirlPet3D_is1`；确认无运行中的 `whale3d` 进程 |
| 静默安装 | `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOICONS /DIR=F:\WhaleGirlPet\build\_installtest_v32 /LOG=...`；退出码 0 |
| 安装文件 | `whale3d.exe` 1,332,224 B；`SDL3.dll` 5,385,103 B；`assets`、`LICENSE`、`README.md`、`THIRD_PARTY_NOTICES.txt`、`unins000.exe/.dat` 均存在 |
| exe 版本 | `FileVersion=3.2.0.0`、`ProductVersion=3.2.0.0` |
| 启动验收 | 真实窗口出现；日志 `Model springs: 4 chains, vrm=1`、`Pose bones: head=5 neck=4 spine=2 chest=3`、`Hit mask ready: 420x620 center_alpha=255`、`fps=26.5`；进程保持运行，关闭后退出 |
| 注册表 | 安装后 `DisplayName=鲸鱼娘 3.2.0`、`DisplayVersion=3.2.0`、`InstallLocation=F:\WhaleGirlPet\build\_installtest_v32\` |
| 卸载 | `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`；退出码 0 |
| 卸载后 | 安装目录只剩本次 smoke 日志；`WhaleGirlPet3D_is1` 注册表键已删除；Start Menu `鲸鱼娘` 组已删除 |
| 恢复原安装 | 删除测试残留日志；`reg import` 恢复 3.1.2 注册；重建 Start Menu 两个快捷方式指向 `F:\WhaleGirlPetApp`；复核 `DisplayVersion=3.1.2`、安装位置 `F:\WhaleGirlPetApp\`、稳定 exe 1,323,520 B / SHA256 `F67F...E84` |

## 结论

- 全新安装、启动、卸载三条路径均通过；安装器内嵌的 exe 与 ZIP 是同一份 3.2.0.0 构建。
- `/NOICONS` 没有阻止脚本创建 Start Menu 组，这是 Inno 脚本现有行为；卸载会删除该组，测试后已恢复原 3.1.2 快捷方式。
- 未验证：从现有 3.1.2 原地升级到 3.2.0-dev；旧版 2D 迁移路径；安装器签名。这三项仍是边界，不写成已完成。
