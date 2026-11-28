# 用户数据存放位置

时间：2026-11-28

## 目标

账号、聊天记录、记忆库、知识库、TTS 缓存和语音文件，默认跟安装文件放在同一个目录，不再无条件写到 C 盘 `%APPDATA%`。

## 当前实现（Python 2D 树）

`app/paths.py` 的规则：

1. **安装版（PyInstaller frozen）**：默认数据目录 = `whale3d.exe` / `WhaleGirlPet.exe` 所在目录，也就是安装目录。
2. **安装目录不可写**（例如装进 `Program Files`）：回退到 `%APPDATA%\WhaleGirlPet`，避免启动失败。
3. **源码运行**：仍用 `%APPDATA%\WhaleGirlPet`，避免把账号/聊天记录写进仓库。
4. **旧指针兼容**：`%APPDATA%\WhaleGirlPet\data_root.txt` 里的旧迁移位置继续认；安装目录里的 `data_root.txt` 优先。
5. **旧数据保护**：安装目录还没有数据、旧 `%APPDATA%` 目录有时，先继续用旧目录，等用户用设置里的“储存位置 → 迁移到这里”搬过来；不会静默丢账号。

3D C++ 壳只负责渲染和输入，不拥有账号/聊天/记忆/TTS 目录；这些数据仍由 Python 2D 树读写。

## 本机状态（2026-11-28）

- 活跃数据目录：`F:\WhaleGirlPetApp`，与安装文件同目录；`data_root.txt` 之前指向这里。
- `C:\Users\<用户>\AppData\Roaming\WhaleGirlPet` 是旧副本（482 个文件与 F 盘重复，5 个核心文件 F 盘更新）；已打包备份到 `F:\WhaleGirlPetApp\_backup_legacy_c_2026-11-28.zip`，然后删除。
- `C:\Users\<用户>\AppData\Local\WhaleGirlPet3D` 是 3.1.0 旧安装（无卸载登记），一并打包进同一个备份后删除。
- 备份含 `WhaleGirlPet3D\whale3d.exe`、`WhaleGirlPet\data_root.txt`、`WhaleGirlPet\accounts.json`；共 495 个 entry。

## 验证

- `build/test_paths_default.py`：冻结态默认目录 = 安装目录；安装目录无数据时回退旧目录；安装目录有数据时优先；旧指针仍生效。
- 本机冻结态模拟：`sys.executable=F:\WhaleGirlPetApp\whale3d.exe` → `default=F:\WhaleGirlPetApp`、`data=F:/WhaleGirlPetApp`、`accounts=F:/WhaleGirlPetApp\accounts.json`。

## 限制

- 该改动只改 Python 2D 树的默认根；3D C++ 壳本身不读写这些用户数据。
- 已安装的旧 exe 不会因为源码改动自动改变行为；要重新打包/安装后才会生效。
- 安装到只读目录时仍会回退 `%APPDATA%`，这是为了不让程序直接启动失败。
