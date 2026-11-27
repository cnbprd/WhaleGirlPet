# post-soak 工具链与磁盘预检

时间：2026-11-27 15:50 左右  
方式：只查路径、版本和磁盘空间；未编译、未构建、未启动第二个 3D。

## 结果

| 项 | 检查结果 | 状态 |
|---|---|---|
| g++ | `F:\WhaleGirlPet\.toolchains\w64devkit\w64devkit\bin\g++.exe`，GCC 16.2.0 | PASS |
| windres | 同目录 `windres.exe`，GNU Binutils 2.47 | PASS |
| SDL3 头文件 | `.toolchains\SDL3\SDL3-3.4.20\x86_64-w64-mingw32\include\SDL3\SDL.h` | PASS |
| SDL3 链接库 | 同 SDK 下 `lib\libSDL3.dll.a`、`libSDL3_test.a` | PASS |
| SDL3 运行 DLL | 同 SDK `bin\SDL3.dll`；项目 `3d\SDL3.dll` 存在 | PASS |
| Python | `.venv\Scripts\python.exe`，Python 3.14.7 | PASS |
| PyInstaller | 6.22.3，`import PyInstaller` 成功 | 版本可用；未做冻结构建 |
| Inno Setup | 项目内 `tools\inno\ISCC.exe`，FileDescription `Inno Setup Command-Line Compiler` | PASS |
| ISCC PATH | 不在 PATH，但 `installer\build_3d_installers.ps1` 固定用项目内路径 | PASS |
| F 盘空间 | 1223 GB 可用 / 640 GB 已用 | PASS |

## 结论

- post-soak 的 3D 编译、安装器编译和 2D PyInstaller 构建所需工具链都在本机；
- 不需要额外安装全局 Inno Setup，`build_3d_installers.ps1` 会使用 `tools\inno\ISCC.exe`；
- 不需要为了找 SDL3 改 `3d\build.ps1`，它默认读 `.toolchains\SDL3`；
- F 盘剩余空间足够，暂不构成构建阻塞。

## 未验证

- 没有实际跑 `g++` 编译，不能证明新增 P1 源文件在真实链接阶段通过；
- 没有跑 PyInstaller，不能证明 Python 3.14.7 + PyInstaller 6.22.3 的冻结包能启动；
- 没有跑 ISCC，不能证明当前安装器脚本能编出最终包；
- 没有检查签名工具/SignPath，因为当前安装包仍是未签名状态。

## 对 runbook 的影响

- 无需修改第 0.5 节的 g++ 路径；
- 安装器回归仍用 `dist\3d\WhaleGirlPet-Setup-3.2.0-sprite.exe`；
- 2D 冻结包构建仍按第 3 节执行，构建完再单独启动；
- 如果后续发现 PyInstaller 在 Python 3.14 下失败，先记录失败日志，不要用旧 2D 包冒充新构建。
