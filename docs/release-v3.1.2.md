# 鲸鱼娘 3.1.2（2026-11-27）

这是一次安装与发布链路修正，不改变 3D 渲染和动画功能。重点是把用户能看到的名称统一成“鲸鱼娘”，并把默认安装位置从 C 盘改到 F 盘。

## 改了什么

1. **应用名统一为“鲸鱼娘”**
   - 安装器 `AppName / AppVerName / DefaultGroupName / UninstallDisplayName / SetupWindowTitle / VersionInfoDescription` 全部去掉“3D”。
   - 3D 窗口标题从 `WhaleGirl 3D Placeholder` 改为 `鲸鱼娘`。
   - 托盘提示改为 `鲸鱼娘 · 桌面宠物`，设置页标题改为 `鲸鱼娘 · 设置`。

2. **默认安装目录不再落到 C 盘**
   - 检测到旧版 2D 3.0.27 时，仍然默认升级到它所在的旧目录。
   - 没检测到旧版 2D 时，如果机器有 F 盘，默认 `F:\WhaleGirlPetApp`。
   - 只有机器上没有 F 盘，才回退 `%LOCALAPPDATA%\WhaleGirlPet3D`。
   - 目录页保留，安装位置仍可手动修改。

3. **安装包文件名去掉 `-3D-`**
   - 新文件名为 `WhaleGirlPet-Setup-3.1.2.exe`。

4. **CI 对齐**
   - 3D 构建 workflow 校验版本 `3.1.2.0`，并新增一条断言：`FileDescription` 不得含 `3D`。
   - GitHub Actions run `45861666963` 通过，耗时 53 秒。

## 资产

| 文件 | 字节 | SHA256 |
|---|---:|---|
| `WhaleGirlPet-Setup-3.1.2.exe` | 4,418,364 | `96B1377F31220C5B603A2D4E8976491385B0D23FD27BF14F80AA70D898BFA699` |
| `whale3d-whale-girl-v3.zip` | 2,809,199 | `A98008C569A4A5686FA136EA091C0D1EAB4B338058B6D97D23433EE6EB8273C3` |
| `whale3d.exe`（包内） | 1,323,520 | `F67F2E00EB1C12CF63A44CEB8A1ADBBD7C61166A6BD4E0D8102A315123E00E84` |

## 验收

- 安装器窗口标题：`安装鲸鱼娘 3.1.2`
- 目录页路径框：`F:\WhaleGirlPetApp`（旧版 2D 存在时）
- 3D 主窗口标题：`鲸鱼娘`
- exe `FileVersion/ProductVersion`：`3.1.2.0`
- PE subsystem：`2`（GUI，不额外弹终端框）
- ZIP 与安装包均从 CI 产物重打；安装包 `FileVersion/ProductVersion` 为 `3.1.2.0`

## 边界

- 真实 `F:\WhaleGirlPetApp` 的约 19 GB 用户数据迁移仍未完整执行；旧 2D 程序文件和旧卸载登记可能仍与新版并存。
- 安装包仍未签名，SignPath Foundation 的申请仍在审核。
- 只有没有 F 盘的机器才会回退到 `%LOCALAPPDATA%`；这类机器仍会看到 C 盘默认路径。
