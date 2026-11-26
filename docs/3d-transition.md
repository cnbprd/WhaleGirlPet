# 3D 转向：低面数鲸鱼娘 v1、ozz 采样接入、表情图集、体积与架构判定

日期：2026-11-26

## 结论

1. **3D 底座、低面数鲸鱼娘 v1、ozz 采样层和表情图集都已跑通**：SDL3 + OpenGL 3.3 透明窗口，加载自研 GLB 角色，2,076 三角形、28 骨骼、14 条 idle 旋转通道、2048×256 三帧内嵌贴图（open / blink / smile）；ozz 在启动时构建 `idle` + 程序化 `walk` 两条 clip。运行负载为 `whale3d.exe` 1,260,544 字节 + `SDL3.dll` 5,385,103 字节 + `whale_girl.glb` 350,332 字节，合计 **6,995,979 字节（6.67 MiB）**。
2. **ozz 只作为采样专项库接进来，没有引入 glTF importer、VRM 运行时或完整引擎。** 同一 exe 用 `WHALE3D_ANIMATOR=self` 可切回自研采样；实测 ozz 的 `update` 为 5.95–9.63 µs/帧，自研为 14.18–22.63 µs/帧（中位数约 6.6 vs 16.3 µs）；代价是 exe 增加 183,296 字节、私有字节约增加 1.2 MB。表情图集再增加 exe 1,536 字节、GLB 17,420 字节，但私有字节没有跨档。
3. **“20–30MB”只对“3D 宠物核心包”成立，对“现有全功能安装包”不成立。** 现有 PySide6 安装包 83,628,239 字节，`_internal` 解压后 177.7MB，其中 PySide6 目录 115.5MB。保留 Qt 壳，3D 化只会让包更大。
4. 因此路线应拆成两个包：**3D 宠物核心**（目标 20–30MB）+ **可选控制中心**（现有 PySide6 面板先保留，后续再决定是否重写）。这样既不丢云端功能，也不让核心包被 Qt 拖回 80MB+。
5. **当前最终核心包已推进到托盘固定 + 设置 + 同进程 in-place 模型缓存 + alpha 命中区**：exe 1,302,528 B，与 `SDL3.dll` 5,385,103 B、`whale_girl.glb` 350,332 B 合计 7,037,963 B（6.71 MiB）；`whale3d-whale-girl-v1.zip` 2,727,089 B，SHA256 `9EB9CCAAA1B42D5CFA440E77FFB4E331A0746F6EF35A07D0843B47CE712BE461`。默认换模在同一 PID/窗口/GL context 内切缓存，首次 placeholder 4ms、缓存命中 0ms，四轮私有字节 98.0–98.2MB；托盘 `IsPromoted=1` 已固定。命中区用每帧 alpha mask + `WM_NCHITTEST` + 每 6 帧 `SetWindowRgn`；OS 级真实鼠标透明角点击触发 underlay `BN_CLICKED`，角色中心拖拽通过。

## 实测对账

| 项目 | 实测值 | 说明 |
| :--- | :--- | :--- |
| `whale3d.exe` | 1,260,544 B / 1.20 MiB | C++ / SDL3 / OpenGL 3.3 + 自研 GLB 加载器 + ozz 静态链接 + 表情 UV 偏移 |
| `SDL3.dll` | 5,385,103 B | 随包分发 |
| `whale_girl.glb` | 350,332 B | 4,314 顶点 / 6,228 索引 / 2,076 三角形 |
| 运行负载合计 | 6,995,979 B / 6.67 MiB | 含模型；不含音频、配置、ozz 源码/静态库 |
| 窗口 | 420×620，透明、无边框、置顶、不抢焦点 | `SDL_WINDOW_TRANSPARENT` |
| 帧率 | 29.9 fps | 主动限 30fps |
| 骨骼 / 动画 | 28 关节 / GLB `Idle` + 程序化 `walk` / 14 条旋转通道 | 单 mesh、单 skin、单 material |
| 表情 | 3 帧 / 2048×256 / 32,232 B | open、blink、smile；`uFaceFrame` 横向偏移，无 morph |
| 工作集 | 62.6–63.1 MB | 表情版实测 62.6 MB；早期 1 次被回收到 50.1 MB |
| 私有字节 | 89.3–90.5 MB | 表情版两次 89.3 / 90.4；ozz 版 89.0–90.5 MB；1 次被回收到 76.9 MB，最终重测 75.7 MB |
| ozz 采样更新 | 5.95–9.63 µs/帧（idle）、5.62–10.60 µs/帧（walk） | 同进程 `SamplingJob` + `LocalToModelJob`；表情版单次 6.6–15.7 µs |
| 自研采样更新 | 14.18–22.63 µs/帧 | 同一模型、同一窗口的 A/B；中位数约 16.3 µs |
| CPU | 约 2%（单核，10 秒均值；单次 1.25–3.44%） | GTX 1060 6GB；端到端差异被驱动/DWM 噪声掩盖 |
| 透明验证 | 87.25% 窗口像素与关窗后完全一致 | 12.75% 变化，bbox=(139,178)-(329,531)，取自表情版打包解压后的 open 帧 |
| 拖拽验证 | 窗口跟随左键移动 | 最近一次 (-90,-45)；历史区间约 (-80~-100, -40~-50) |
| 退出验证 | 右键退出成功 | 透明角落与角色身上都会触发，命中区仍是整窗；这是表情版阶段的状态，第 7 步已改成 alpha 区域 |

上表是表情/ozz 阶段的历史数据，exe 不是当前包。当前 v3.1.0 VRM+SpringBone 版 exe 为 1,315,840 B，运行负载 7,052,651 B（6.72 MiB），工作目录私有字节 97.8–98.1MB，包内临时目录 98.3–98.4MB；见第 10 步。

## 第 3 步：低面数鲸鱼娘 v1

这版不是“再换一个占位方块”，而是按现有 JK 皮肤做的第一版可辨认角色：

| 项 | 实现 |
| :--- | :--- |
| 设计参照 | `assets/skins/jk.png`：蓝发、水手服、 navy 百褶裙、白袜、黑鞋、鲸鱼尾 |
| 生成器 | `3d/tools/make_whale_girl_glb.py` |
| 规模 | 4,314 顶点 / 6,228 索引 / 2,076 三角形 |
| 骨架 | 28 关节：root / hips / spine / chest / neck / head / 肩臂手 / 大腿小腿脚 / 尾 / 尾尖 / 侧发 / 后发 |
| 动画 | 14 条 rotation 通道：头、胸、双臂、双腿、侧发、发尾、尾、尾尖 |
| 贴图 | 2048×256 图集，三帧 512×256：open x=0、blink x=512、smile x=1024，最后 512×256 纯白供顶点色相乘；PNG 32,232 B 内嵌 |
| 材质 | baseColorTexture + 顶点色 + baseColorFactor；单 material |
| 蒙皮 | 单关节刚性权重，权重 1.0 |
| 表情 | `uFaceFrame` 对 `vUV.x < 0.5` 的脸部顶点横向偏移 0.25；身体顶点固定采样白槽 0.875 |

实测结果：

- 角色可辨认：蓝发渐变、白色水手领、navy 蝴蝶结、百褶裙、白袜、黑鞋、右侧鲸鱼尾。
- 打开 / 关闭对比中 87.25% 的窗口像素完全一致，说明加模型后仍是逐像素 alpha，而不是黑底矩形（bbox=(139,178)-(329,531)）。
- 三张不同时刻截图在角色范围内均有差异；头、手臂、腿、侧发、尾巴都在动，网格没有炸开。
- 可运行包 `whale3d-whale-girl-v1.zip` 已更新为表情版，打包后解压到临时目录启动实测（大小与结果见下文“可运行包”）。

### 面数与体积

| 阶段 | 模型 | 三角形 | GLB 大小 | 运行负载 |
| :--- | :--- | :--- | :--- | :--- |
| 立方体底座 | 无 | 12 | 无 | 5,453,679 B / 5.20 MiB |
| 方块占位 | `placeholder.glb` | 216 | 38,288 B | 6,498,591 B / 6.20 MiB |
| 鲸鱼娘 v1 | `whale_girl.glb` | 2,076 | 332,912 B | 6,793,727 B / 6.48 MiB |
| 鲸鱼娘 v1 + ozz | `whale_girl.glb` | 2,076 | 332,912 B | 6,977,023 B / 6.65 MiB |
| 鲸鱼娘 v1 + ozz + 表情 | `whale_girl.glb` | 2,076 | 350,332 B | **6,995,979 B / 6.67 MiB** |

从 216 到 2,076 三角形，模型加载只增加 295,136 字节；接 ozz 再增加 183,296 字节；三帧表情图集再增加 GLB 17,420 字节、exe 1,536 字节。真正贵的是贴图和驱动侧显存。**模型面数不是当前包体积的主要矛盾，壳和贴图才是。**

### 内存为什么从 100.8 降到 89–90

第一版 1024×512 贴图带完整 mipmap 链，私有字节 100.8MB，贴着 100MB 上限。桌面宠物始终离镜头很近，mipmap 在这个尺度上几乎用不到；改成 `GL_LINEAR`、不生成 mip 链，并把脸部图集收窄到只保留有效区域后：

- 工作集：68.8 → **63.0 MB**
- 私有字节：100.8 → **89.0 MB**
- CPU：2.19% → **1.09%**
- 视觉：截图对比无可见退化

三帧表情版把图集扩到 2048×256：原始 RGBA 仍是 2 MB，但每帧从 1024×512 的 512×512 压到 512×256；第一版 2048×512 曾把私有字节推到 **98.0MB**，回退到 512×256 后为 **89.3–90.4MB**。所以这里的关键不是“图集更宽”，而是**不要为三帧同时保留三张 512×512 的 RGBA**。

### 踩过的坑

1. 第一版生成器的 buffer 偏移用了 `len(bin_parts)`（字节块个数），导致 bufferView 偏移全落在 0–16；C++ 读取 `img["bufferView"]` 时拿到 JSON 对象，nlohmann 抛异常后 `std::terminate`，退出码 `-1073741795`。修复为 `bytearray` 累计真实字节偏移、`align4()` 按字节长度对齐；图片 bufferView 改为整数索引。
2. 尾巴第一版做成了水平薄片，正面看只是一条蓝线；改成垂直鲸尾轮廓并加厚度后，正视图才读得出来。
3. 侧发第一版从耳前起，像两只蓝色角；下移并后移后，才像侧发。

## 第 4 步：ozz-animation 只接采样层

目标不是“把 ozz 整个塞进来”，而是只借它的骨骼采样和矩阵求值，验证它能否替掉自研采样，同时保留回退路径：

| 项 | 实现 |
| :--- | :--- |
| 源码 | `3d/third_party/ozz-animation-master`，MIT；`ozz-master.zip` 44,050,265 B |
| 静态库 | `libozz_animation_offline_r.a` 285,750 B + `libozz_animation_r.a` 157,842 B + `libozz_base_r.a` 51,600 B，合计 495,192 B |
| 构建 | w64devkit 自带 CMake 4.4.4，`MinGW Makefiles`，`BUILD_SHARED_LIBS=OFF`，tools/fbx/gltf/data/samples/howtos/tests 全 OFF |
| 骨架 | 由 GLB 节点 rest pose 构造 `RawSkeleton`，`SkeletonBuilder` 得到 28 关节 runtime skeleton；按关节名建立 `skinToOzz` 映射 |
| 动画 | GLB `Idle` 翻译为 `RawAnimation`（28 条 track，缺省 TRS 用 rest pose 填充，14 条 rotation 覆盖）；`walk` 为启动时生成的 2 秒正弦技术 clip |
| 每帧 | `SamplingJob` 采样 + `LocalToModelJob` 求全局矩阵；列主序 `Float4x4` 直接复制到现有 `Mat4`，再乘 GLB inverse bind |
| 回退 | `WHALE3D_ANIMATOR=self` 或 ozz 初始化失败时走原自研采样；`O` 键可在运行时切换 |

### ozz 实测

同一台机器、同一模型、同一窗口，分别跑 `WHALE3D_ANIMATOR=ozz` 与 `self`：

| 指标 | ozz | self | 差值 |
| :--- | :--- | :--- | :--- |
| exe | 1,259,008 B（A/B 基线） | 1,259,008 B（同一 exe） | 运行时切换，不另打包；表情版 +1,536 B |
| update_us（idle） | 5.95–9.63 µs/帧 | 14.18–22.63 µs/帧 | 中位数约 6.6 vs 16.3 µs，约快 60% |
| update_us（walk） | 5.62–10.60 µs/帧 | — | 同量级 |
| 工作集（idle） | 62.8–63.1 MB | 62.7–62.8 MB | 约 +0.2 MB；ozz 有 1 次被回收到 50.1 MB |
| 私有字节（idle） | 89.0–90.5 MB | 89.1–89.6 MB | 约 +1.2 MB；ozz 有 1 次被回收到 76.9 MB |
| CPU（端到端） | 1.25–3.44% | 1.25–2.81% | 噪声内，不能据此下结论 |
| FPS | 29.3–29.9 | 29.4–29.9 | 都受 30fps 上限约束 |

下表 A/B 在无表情 ozz 版上测得；表情版是同一 exe 加 1,536 B，idle `update` 实测 6.6–15.7 µs，私有字节 89.3–90.4 MB，和表内 ozz 区间同档。exe 只增长 183,296 字节，而不是静态库总和的 495,192 字节：`-ffunction-sections -fdata-sections -Wl,--gc-sections` 把未引用的 importer、工具和 FBX/glTF 代码丢掉。代价是私有字节从 v1 的 89.0 MB 涨到约 90.2 MB，距 100 MB 只剩约 9.8 MB；表情版实测 89.3–90.4 MB，留出约 9.6–10.7 MB。

结论：**ozz 值得保留为采样层，但还不值得扩成完整动画运行时。** 当前收益主要是每帧采样成本；端到端 CPU 和帧率受 30fps 上限及驱动影响，不能拿单次 CPU 百分比当结论。下一步若要做 blend/IK/root motion，再评估是否继续加 ozz 层，而不是现在把 VRM/importer 一起拖进来。

## 第 5 步：三帧表情图集（open / blink / smile）

目标是在不引 VRM、不引 morph target、不拆 mesh/material/texture 的前提下，让脸有 2–3 个可切换状态：

| 项 | 实现 |
| :--- | :--- |
| 图集 | 2048×256；三个 512×256 脸槽 x=0 / x=512 / x=1024；最后 512×256 纯白给身体顶点色 |
| 生成器 | `3d/tools/make_whale_girl_glb.py` 先画 512×512 的 `face_open` / `face_blink` / `face_smile`，再用 LANCZOS 收到 512×256 贴进图集 |
| UV | 脸贴片 u=0.002–0.248；身体 `WHITE_UV=(0.875,0.5)` |
| Shader | `uniform int uFaceFrame`；`vUV.x < 0.5` 的片元做 `uv.x += frame * 0.25`，身体不受影响 |
| 状态 | `faceFrame` + `forcedFace` + `smile` + `nextBlink` + `blinkUntil`；`setFace("auto/open/blink/smile")` |
| 自动眨眼 | 启动后 2.0 秒首次，之后每 3.2 秒一次，持续 0.18 秒；smile 时基础帧 2，眨眼短暂覆盖为 1 |
| 控制 | `WHALE3D_FACE=auto|open|blink|smile`；`E` 切 smile，`B` 触发一次眨眼；日志每秒输出 `face=...` |

体积与视觉：

- GLB：332,912 → **350,332 B**（+17,420 B，主要是三帧 PNG）
- 图集 PNG：14,809 → **32,232 B**（+17,423 B）
- exe：1,259,008 → **1,260,544 B**（+1,536 B，shader uniform + 状态机）
- 顶点 / 索引 / 三角形 / 关节 / rotation 通道：4,314 / 6,228 / 2,076 / 28 / 14，全部不变
- 实测 open、blink、smile 三帧截图正常；`run_face_pkg_final4.err.log` 在正常 idle 运行中抓到 `face=blink`，证明自动调度生效
- 2048×512（每帧 512×512）第一版私有字节 **98.0MB**，太贴上限；改成 512×256 后 **89.3–90.4MB**，目视几乎无退化

这不是完整表情系统：blink 是闭眼线 + 睫毛弧；smile 是弯眼笑 + 张口笑弧 + 舌头，不是独立的面部骨骼或 morph。没有眼球转动、口型同步或情绪混合。它的价值是**用一条 2MB 纹理和 1,536 字节代码把“静态脸”变成可调度状态**，且不破坏单 mesh / 单 material / 单 texture 的加载路径。

## 第 6 步：Win32 托盘 + 最小设置页

目标：不引 Qt/PySide6，不引第二个 UI 框架，用 Win32 原生控件补上“启动/退出/切换模型/打开面板”，并保持 3D 核心包的体积和内存线。

| 项 | 实现 |
| :--- | :--- |
| 托盘 | `Shell_NotifyIconW` + `NOTIFYICON_VERSION_4`；`SDL_GetWindowProperties` 取 SDL 的 Win32 `HWND`，`SetWindowLongPtrW` 子类化 WndProc |
| 图标 | `3d/assets/ui/pet.ico` 9,001 B，含 16/32/48 三档；源 `assets/ui/pet_flat.ico` 140,034 B |
| 菜单 | 原生 `CreatePopupMenu`：隐藏/显示窗口、动画切到 Walk/Idle、表情子菜单（自动/Open/Blink/Smile）、设置…、退出 |
| 入口 | 左键托盘切换窗口显隐；右键托盘或右键宠物都弹同一个原生菜单 |
| 设置页 | 原生模态窗口，标题 `鲸鱼娘 3D · 设置`；客户区 420×360，整体约 426×389；只用 `COMBOBOX` / `BUTTON` / `STATIC` |
| 控件 | 模型（鲸鱼娘 v1 / 方块占位）、动画（idle / walk）、表情（auto / open / blink / smile）、采样器（ozz / self）、状态行、应用/关闭 |
| 模型切换 | 设置页正常路径是 `CreateProcessW` 子进程重启，环境变量 `WHALE3D_CLIP` / `WHALE3D_FACE` / `WHALE3D_ANIMATOR`；只有创建失败才回退 `Model::load` 进程内重载 |
| 退出 | `WM_CLOSE` / 托盘 1004 / 设置关闭后退出统一走 `running && !ui.quitRequested()` |
| 新文件 | `3d/shell_ui.h`、`3d/shell_ui.cpp`；`build.ps1` 增加 `shell_ui.cpp` 和 `-lshell32` |

三个托盘 bug 都是实测出来的，不是猜的：

1. **NOTIFYICON_VERSION_4 的 lParam 高字带 icon id**。原代码把整个 `lParam` 与 `WM_LBUTTONUP` 比较，真实点击永远不匹配；改成 `LOWORD(lParam)` 后用 `PostMessage(WM_APP+42, 0, (1<<16)|WM_LBUTTONUP)` 实测左键隐藏/显示成功。
2. **`TPM_RETURNCMD` 的返回值被忽略**。菜单用了 `TPM_RETURNCMD | TPM_NONOTIFY`，选中项不发 `WM_COMMAND`；原代码不处理返回值，点“退出/设置/切换动画”都没动作。改成 `const int command = TrackPopupMenu(...); if (command) handleCommand(command);` 后，点“退出”返回 `command=1004` 并正常退出，点“设置”能打开设置页。
3. **`SetForegroundWindow` 对 `SDL_WINDOW_NOT_FOCUSABLE` 返回 0**。菜单能显示，但点菜单外不会消失。`SDL_SetWindowFocusable(true/false)` 能让菜单获得焦点，但会在退出时 `SDL_QuitFilesystem` 崩溃，已放弃；最终临时清 `WS_EX_NOACTIVATE`，`SetWindowPos(...SWP_FRAMECHANGED)`，再用 `AttachThreadInput(foregroundThread,currentThread,TRUE)` 包住 `SetForegroundWindow`，菜单结束后恢复 exstyle。实测 `Tray menu command=1004 foreground=1`，点菜单外可关闭。

设置页还暴露一个 MinGW 宽字符格式问题：`swprintf` 用 `%s` 输出 `toWide(...).c_str()` 时按窄字符串解释，状态行显示成 `当前：i / o / o`；改成 `%ls` 后正常显示 `当前：idle / open / ozz 2076 三角形 / 28 关节`。

退出崩溃是 2D→3D 底座阶段就带入的旧 bug，与托盘无关：`main.cpp` 曾对 `SDL_GetBasePath()` 返回的内部缓存指针调用 `SDL_free`，导致 `SDL_QuitFilesystem` 里 double free，退出码 `0xC0000374`（`STATUS_HEAP_CORRUPTION`）。gdb 栈为 `SDL_Quit_REAL → SDL_QuitFilesystem → msvcrt!free`。删除该 `SDL_free` 并加注释后，直接退出、托盘菜单退出、设置页关闭后退出均返回 **0**。旧表情版包里的 exe 也有同样 bug。

模型切换做过两版：

- **进程内 `Model::load` 重载**：可行，但驱动/GL 资源不回落；初始私有约 95.7MB，先切 placeholder 再切回鲸鱼娘，私有涨到 **100,499,456 → 102,600,704 B**，超过 100MB 线，放弃。
- **子进程重启（旧版）**：`ShellUi::restartWithModel` 用 `GetModuleFileNameW` 取自身 exe，设置三个环境变量，`CreateProcessW` 以新模型为 `argv[1]` 启动新进程，旧进程立即 `SDL_HideWindow`、`quit_=true`、`PostMessage(settings, WM_CLOSE)`；另起 4 秒 watchdog。实测旧窗口隐藏，旧 PID 在 6 秒内消失，新进程接管；placeholder 稳态 private **85,905,408 B**、RSS 61,014,016 B；切回鲸鱼娘稳态 private **93,392,896 B**、RSS 66,703,360 B。新进程启动 2.5s 时曾测到 **141,410,304–149,041,152 B** private 峰值，10s 后回落到上述稳态。这个双进程重叠峰值已被第 8 步的模型缓存取代；`--relaunch` 仍保留为可选 A/B/fallback。

本轮实测（同一台 GTX 1060 6GB / 582.78 / OpenGL 3.3.0）：

| 项 | 数值 |
| :--- | :--- |
| `whale3d.exe` | **1,294,336 B**，SHA256 `B03B2B079AC667F50114523055B960C432822D140FA8EE46C861C4F1CDB9D1FD` |
| exe 增量 | 表情版 1,260,544 → 1,294,336，**+33,792 B** |
| 运行负载（exe + SDL3.dll + GLB） | 1,294,336 + 5,385,103 + 350,332 = **7,029,771 B（6.70 MiB）** |
| 托盘图标 | 9,001 B；`Shell_NotifyIconGetRect` 返回 `rect=(1611,0)-(1643,48)`（Win11 的 `^` 按钮，不是图标本体） |
| 设置页 | 客户区 420×360，整体约 426×389；状态行 y=246，按钮 y=300 |
| FPS | 正常 29–30；设置模态打开时 0.7–13，关闭后恢复 |
| 私有字节，启动 | 92,200,960–95,662,080（两次运行） |
| 私有字节，设置页开/关 | 94,806,016 / 95,363,072，打开关闭无持续增长 |
| 私有字节，placeholder 重启后 | 85,905,408（10s）；RSS 61,014,016 |
| 私有字节，鲸鱼娘重启后 | 93,392,896（10s）；RSS 66,703,360 |
| CPU | 10s 窗口 1.7–3.1% 单核；启动首窗 6.2% |
| 退出码 | 直接退出 / 托盘菜单退出 / 设置关闭后退出均为 **0** |

上表是**第 6 步托盘版**（exe 1,294,336 B）；当前最终 exe 已加上第 7 步的 alpha 命中区，体积和内存以第 7 步表格为准。第 6 步旧的 `B03B...` hash 与旧 `12E1...` 包 hash 不能再用于当前包。

截图与日志：

- `docs/_3d_settings.png`：最终 420×360 设置页（模型/动画/表情/采样器/状态行）。
- `docs/_3d_settings_applied.png`：旧 330 布局，Walk/Smile/ozz 已应用；仅作历史。
- `docs/_3d_settings_failed.png`：旧布局，self+Walk 未应用。
- `docs/_3d_settings_placeholder.png` / `_3d_settings_whale_back.png`：进程内 reload 版设置页。
- `docs/_3d_model_placeholder.png` / `_3d_model_whale_back.png`：进程内 reload 版窗口。
- `docs/_3d_model_placeholder_restart.png` / `_3d_model_whale_restart.png`：子进程重启版窗口。
- `docs/_3d_tray_menu.png` / `_3d_tray_menu_zoom.png`：原生托盘菜单。
- `docs/_3d_tray_icon_source.png`：`pet.ico` 转出的 48×48 图标。
- `docs/_3d_tray_overflow.png`：Win11 隐藏图标浮层；截图中没有直接看到鲸鱼娘图标。
- `docs/_3d_tray_icon.png`：1611–1643 的 `^` 按钮裁剪，不是实际图标，不能当托盘证据。

当前状态：托盘、右键菜单、设置页、模型切换、退出都已实测通过；`assets/ui/pet.ico` 已进包；`README.md` 和本节已写第 6 步数字。云端 `ai_profiles`、`_chat_cloud`、云端 API 路由仍在 Python 服务侧，不能拆。

## 第 7 步：alpha 命中区与透明点击穿透

目标：窗口仍是 420×620 透明画布，但只有角色像素属于 Win32 窗口，透明角落和腿部空隙不再挡住桌面点击。

实现分两层：

| 层 | 做法 |
| :--- | :--- |
| 像素 mask | `main.cpp` 维护 `hitMask`（420×620 RGBA，约 1.04 MB）；每帧 `glReadBuffer(GL_BACK)` + `glReadPixels(0,0,pw,ph,GL_RGBA,...)` 读回 back buffer alpha；`ui.setHitTest` 接收 mask，client 坐标换算到 mask 坐标，alpha > 16 才算命中 |
| Win32 命中测试 | `ShellUi` 子类化 WndProc 的 `WM_NCHITTEST` 把屏幕坐标 `ScreenToClient`，角色像素返回 `HTCLIENT`，透明像素返回 `HTTRANSPARENT` |
| 窗口区域 | `HTTRANSPARENT` 官方只保证同线程窗口穿透；`ShellUi::updateWindowRegion` 用 alpha mask 生成水平 run，`ExtCreateRegion` 后每 6 帧 `SetWindowRgn`，透明像素从系统窗口区域里移除，跨进程点击落到下层窗口 |
| 退出 bug | 这次没有重新引入 `SDL_GetBasePath()` 的 `SDL_free`；直接退出、托盘退出、设置关闭后退出仍为 0 |

实测（`region_accept.err.log` / `region_test.err.log`）：

| 检查 | 结果 |
| :--- | :--- |
| `SendMessageW(WM_NCHITTEST)` 角色中心 | `1`（`HTCLIENT`） |
| 左上角 / 下边缘 / 腿部空隙 | `-1`（`HTTRANSPARENT`） |
| `WindowFromPoint` 透明角落 | 干净 topmost underlay 实测返回测试窗的子 `BUTTON`（早期 HWND 7146702；最新 final 构建 HWND 17564498），角色中心返回 pet 的 `SDL_app`（最新 HWND 5967352）；在另一个已有 Notepad 覆盖的包里则返回 Notepad 的 `RichEditD2DPT`，两者都不是 pet |
| 角色身上拖拽 | 窗口 rect `(1420,430)-(1840,1050)` → `(1460,450)-(1880,1070)`，位移 +40/+20 |
| OS 级真实鼠标：透明角落 | `SetCursorPos` + `mouse_event` 点击后，underlay 按钮收到 `BN_CLICKED id=1 count=1`（不是 `PostMessage`，也不是 `BM_CLICK`） |
| OS 级真实鼠标：角色中心 | 从角色中心按下并拖到 +35/+25，pet rect `(1200,300)-(1620,920)` → `(1235,325)-(1655,945)`，underlay 点击计数仍为 1 |
| 最新 final 构建复跑 | underlay HWND 11797366 / button 17564498 / pet HWND 5967352（PID 18292）；corner=button，center=pet，`BN_CLICKED count=1`，`moved=True`，pet exit=0 |
| 截图 | `docs/_3d_hit_region.png`；角色正常，无矩形裁剪痕迹 |
| 日志 | `Hit mask ready: 420x620 center_alpha=255`；真实鼠标日志 `3d/real_mouse_accept.log` |
| FPS | 26.8 首采样，随后 28.8–29.0；alpha 回读 + 区域更新没有把帧率打崩 |
| 私有字节 | 97,366,016（5s）→ 96,624,640（10s）；RSS 70.7 MB；距 100 MB 线约 2.6–3.4 MB |

**闭环方式**：把“点击穿透”拆成三段验收。第一段是命中目标：干净 topmost underlay 在 pet 的透明角落时，`WindowFromPoint` 返回测试窗的 `BUTTON`，角色中心仍返回 pet，说明系统命中路由没有把透明点算成 pet。第二段是回调路径：对该 `BUTTON` 执行 `BM_CLICK`，父窗口收到 `WM_COMMAND`（`wParam=1`）并写出 marker。第三段是 OS 级真实鼠标：`SetCursorPos` + `mouse_event` 点击透明角落，underlay 收到 `BN_CLICKED`；从角色中心拖拽，pet 窗口移动且 underlay 点击计数不变。三段都通过后，透明区域的点击穿透成立。

**仍未复现的只有物理手点击**：这次 `SetCursorPos` + `mouse_event` 的 OS 级注入已经通过，透明角落确实触发了 underlay 的 `BN_CLICKED`，角色中心拖拽也移动了窗口；之前 marker 没写出来是旧 ctypes WndProc 的 LPARAM 截断/`DefWindowProc` 溢出，不是窗口区域路由失败。物理鼠标人工点一次仍建议由用户做最终目检。

## 第 8 步：同一进程、同一 GL 上下文的模型缓存（默认）

目标：切换模型不再重启进程，也不隐藏窗口；同一 `HWND`、同一 OpenGL context 内直接切模型。

实现：

- `Model` 内部维护 `cache_`（`std::vector<Impl*>`）。每个路径第一次加载时创建一个 `Impl`；之后同一路径直接复用。
- `Model::load(path)` 命中缓存时只把 `impl_` 指向缓存的 `Impl*`，不解析 GLB、不建 shader、不重建 VBO/EBO/VAO/纹理。
- 未命中时新建 `Impl` 并解析；失败则保留旧 active `Impl`，不破坏当前画面。
- `ShellUi::applySettings` 默认走 `model_->load(newModelPath)`；`restartWithModel` / `--relaunch` 只在 `WHALE3D_SWITCH=relaunch` 时启用，保留作 A/B 与 fallback。
- 不调用 `SDL_HideWindow`、不设置 `quit_`、不启动子进程。

实测（`3d/inplace_switch.err.log` / `3d/inplace_switch.log`，`WHALE3D_SWITCH` 未设置）：

| 项 | 数值 |
| :--- | :--- |
| 首次加载 placeholder | 4 ms |
| 缓存命中（placeholder → whale、再切回） | 0 ms |
| 私有字节，鲸鱼娘稳态 | 98,004,992 B |
| 私有字节，切 placeholder 后 | 98,201,600 B |
| 私有字节，切回鲸鱼娘 / 再切两轮 | 98,201,600 B，四轮不增长 |
| 进程 | 同一 PID 11748；无子进程；退出码 0 |
| 窗口/画面 | 不隐藏、无空窗；截图 `docs/_3d_inplace_whale_before.png`、`_3d_inplace_placeholder.png`、`_3d_inplace_whale_back.png` |

结论：默认换模是真正的 in-place：没有进程重启、没有窗口交接、没有 helper，内存稳定在 **98.0–98.2MB**，低于 100MB；切换本身 0–4ms。旧的双进程 helper 仍保留，但不是默认路径。

### 可选的延迟交接 helper（A/B/fallback）

`WHALE3D_SWITCH=relaunch` 时仍走 `whale3d.exe --relaunch <old_pid> "<model>"`：

- helper 在 `SDL_Init` 前分派，不建窗口/托盘/GL；等旧 PID 最多 12s，超时才 `TerminateProcess`，再启动新 pet。
- 旧进程立即隐藏、2.5s watchdog；新 pet 等旧进程退出后才启动。
- 实测 helper 2,064,384 B；旧 pet + helper 峰值 97,333,248 B（whale→placeholder）/ 97,456,128 B（placeholder→whale）；新 pet 1.55–1.61s 出现。代价是约 1.6s 隐藏空窗，所以只作 A/B/fallback。

## 第 9 步：Win11 托盘图标固定

实现：`ShellUi::promoteTrayIcon` 在 `Shell_NotifyIcon(NIM_ADD)` 后枚举
`HKCU\Control Panel\NotifyIconSettings`，用 `ExecutablePath` 匹配当前 exe，写入
`IsPromoted=1`（REG_DWORD）。`IsPromoted=0` 表示在溢出区，`1` 表示固定到任务栏。

实测：

| 项 | 结果 |
| :--- | :--- |
| 当前 key | `HKCU\Control Panel\NotifyIconSettings\674768749172540869` |
| 写入值 | `IsPromoted=1`（DWORD），已导出备份 `docs/tray_registry_backup.reg` |
| Explorer | 重启一次后生效 |
| 任务栏 rect | `(1611,0)-(1643,48)`；精确裁剪 `docs/_3d_tray_promoted_rect.png` 显示蓝发鲸鱼娘图标，不是 `^` |
| 应用启动日志 | `ShellUi: tray promotion set for key=674768749172540869` |

注意事项：Explorer 只在启动时读取该值；新安装第一次运行后仍需重启一次 Explorer/重新登录。当前机器已完成这次重启并目检。

依据：Microsoft Q&A 关于 Win11 通知区域隐藏/固定的回答，以及 Geek Rewind 的 Win11 托盘溢出说明，均指出 `HKCU\Control Panel\NotifyIconSettings\<App ID>\IsPromoted` 的 DWORD 语义为 1=固定、0=溢出。链接：
`https://learn.microsoft.com/de-de/answers/questions/4067817/windows-11-pro-taskbar-infobereich-ausgebledete-ob?page=2`
`https://geekrewind.com/how-to-hide-or-show-system-tray-icons-in-the-taskbar-overflow-menu-on-windows-11/`

## 为什么不能“只把 2D 贴图换成 3D 模型”

现有 2D 安装包不是“贴图大”，而是“壳大”：

| 组成 | 体积 |
| :--- | :--- |
| 安装包 `WhaleGirlPet-Setup-3.0.27.exe` | 83,628,239 B |
| 安装目录 `_internal`（解压后） | 177.7 MB |
| 其中 PySide6 | 115.5 MB |
| 其中 assets | 22.8 MB |

即使 3D 模型和动画完全不占空间，只要还捆 PySide6，安装包就不可能回到 20–30MB。**3D 化的第一步不是换模型，而是换壳。**

## 推荐架构

| 层 | 选择 | 体积状态 | 当前进度 |
| :--- | :--- | :--- | :--- |
| 平台壳 | SDL3 + Win32 托盘/菜单/命中区 | 6.71 MiB 实测（exe 1,302,528 + SDL3 5,385,103 + GLB 350,332；含 ozz/表情/托盘/设置/alpha region/in-place 模型缓存） | 窗口/拖拽/托盘/右键菜单/退出/透明点击穿透/同一进程换模 <100MB 已通 |
| 渲染 | OpenGL 3.3 core | 含在上项 | 透明/光照/蒙皮/动画已通 |
| 模型 | 自研 glTF 加载器 + 最小 VRM 1.0 容器，不引完整运行时 | 含在上项；VRM 351,708 B | 低面数鲸鱼娘 v1 + 4 条两骨 SpringBone 已通；MToon/表情/碰撞体未接 |
| 骨架动画 | 自研采样 + ozz 采样专项库 | static libs 495,192 B；exe +183,296 B | ozz 已接 idle + walk；self 保留对照 |
| 表情 | 2048×256 三帧图集 + shader 偏移 | GLB +17,420 B；exe +1,536 B | open / blink / smile 已通；自动眨眼生效 |
| 行为 | C++ 状态机 + 现有动作语义 | 未实测 | 未接入 |
| 云端/AI | 现有 Python 服务独立为可选模块 | 不进入核心包 | 保留现有实现 |
| 控制面板 | 原生 Win32 设置页；PySide6 控制中心后续再迁 | 核心包已含最小设置页 | 模型/动画/表情/采样器 + 应用/关闭已通 |

## 体积预算（目标，不是实测）

| 项 | 预算 |
| :--- | :--- |
| 壳 + 渲染 + 加载器 | 6–7 MB（已实测 6.70 MiB，含 v1 模型 + ozz 链接增量 + 表情图集 + 托盘/设置） |
| 正式角色 + 压缩纹理 | 10–18 MB（按 1K 贴图、2–4 万面估算） |
| 骨骼动画库 + 动画数据 | 1–3 MB（ozz 已实测：exe +183,296 B，RAM 约 +1.2 MB） |
| 音频/配置/图标 | 1–2 MB |
| 合计 | 20–30 MB |

这些是预算，不是承诺。当前 in-place 缓存版私有字节：稳态鲸鱼娘 **98.0MB**，切 placeholder 后 **98.2MB**，四轮切换不增长；距 100MB 线约 1.8MB。`--relaunch` helper 的可选路径峰值 97.3–97.5MB。正式角色、更多表情和更多动画接进来后必须重新压测；缓存现在会同时保留鲸鱼娘和 placeholder 两套模型资源。

## 可运行包

`3d\whale3d-whale-girl-v1.zip` 为 **2,727,089 B（2.60 MiB）**，SHA256 `9EB9CCAAA1B42D5CFA440E77FFB4E331A0746F6EF35A07D0843B47CE712BE461`。内容：`whale3d.exe` 1,302,528 B、`SDL3.dll` 5,385,103 B、`README.md` 16,287 B、`THIRD_PARTY_NOTICES.txt` 4,188 B、`assets/models/whale_girl.glb` 350,332 B、`_whale_girl_atlas.png` 32,232 B、`placeholder.glb` 38,288 B、`assets/ui/pet.ico` 9,001 B。

已解压到临时目录并启动该包内的 exe：日志确认 `Tray icon ready`、`ozz ready: 28 joints, clips=idle/walk`、`Model loaded ... 2076 triangles, 28 joints`、`Animator: ozz; clip: idle; face: open`、`Hit mask ready: 420x620 center_alpha=255`。随后通过 `WM_COMMAND 1003` 打开设置页，选择 `placeholder.glb + idle + open + ozz`，`WM_COMMAND 2004` 应用后日志出现 `In-place model switch requested`、`In-place model load: placeholder.glb ok=1 ms=4`，没有 helper/新进程；切回鲸鱼娘时日志为 `In-place model load: whale_girl.glb ok=1 ms=0`。两轮切换后 PID 仍为 11988，无子进程，退出码 0。包内 exe 的 SHA256 为 `53F6113B757276BA029C2EB16A829FF2D69FF1805D3216782B9965203B6D0478`，与工作目录构建一致。日志：`docs/_3d_package_verify_inplace.log`。注：包测试从临时路径启动，`NotifyIconSettings` 没有该新路径的 key，日志为 `tray promotion registry key not found`；托盘固定是在实际路径 `F:\WhaleGirlPet\3d` 上验证的。

旧表情版包保留为 `3d\whale3d-whale-girl-v1-expression.zip` **2,695,131 B**，exe `1,260,544 B`、SHA256 `534FA2B87C83D2ACFDB5B380B3954F9E07D2815168EE5B20845D11A76C161435`，不要与新包混用。透明对比取自旧表情包解压后的 open 帧：87.25% 像素完全一致，bbox=(139,178)-(329,531)；新包的模型/图集/渲染路径未变。

## 第 10 步（v3.1.0）：VRM 1.0 身体与 SpringBone 二次动力学

这一轮只做第一层“3D 身体”，不接 ASR/LLM/TTS，也不把认知层塞进渲染进程。

| 项 | 实现 | 实测 |
| :--- | :--- | :--- |
| 默认角色格式 | `tools/make_whale_girl_vrm.py` 从原 GLB 生成 `whale_girl.vrm`；`main.cpp` 默认加载 `.vrm`，失败回退 `.glb`，再回退 placeholder | `Model loaded: whale_girl.vrm (2076 triangles, 28 joints, 1 animations)` |
| VRM 元数据 | `VRMC_vrm` 1.0 + 19 个 humanoid bones；`VRMC_springBone` 4 条两骨链：`hair_side.L/R` `[22,23]/[24,25]`、`hair_back` `[26,27]`、`tail` `[20,21]` | 文件 **351,708 B**，SHA256 `BFD19124F1435E1CD2936F451AB4DEEFF0CABD5CA9A99B72E57E037D2BDECB87` |
| 弹簧求解 | 每帧半隐式角弹簧；窗口位移作为惯性输入，呼吸正弦作为微动；root 旋转后按 `newRoot * inverse(oldRoot) * oldTip` 重建 tip | `Model springs: 4 chains, vrm=1, enabled=1` |
| VRM 参数映射 | `k = 50 + stiffness*100`、`drag = 9 + dragForce*20`；头发振幅 0.075 rad、尾巴 0.12 rad，限幅约 ±0.30 rad | 4 条链全部初始化并参与每帧求解 |
| A/B 开关 | `WHALE3D_SPRING=0` 关闭弹簧层；`WHALE3D_FREEZE=1` 冻结基础 clip 便于同帧对比（仅测试用） | `spring_accept.py` 跑两组进程 |
| 视觉验收 | 冻结 idle 后，spring on/off 各抓 3 帧；`docs/_3d_spring_on_*.png` / `_off_*.png` | 三帧平均 RGB 差 **0.797 / 0.765 / 1.523**；第 2 帧头发区差 **14.3**、尾巴区差 **96.7**（RGB 和） |
| 窗口惯性接线 | `main.cpp` 每帧 `SDL_GetWindowPosition` 差值传给 `setMotionInput(dx,dy)` | 拖拽路径仍通过，未出现网格拉伸/炸开 |
| 设置页 | 模型下拉改为 `鲸鱼娘 v1 (VRM)`；切换仍走 in-place cache | 切 placeholder 首次 4–8 ms，切回 `.vrm` 缓存命中 0 ms |
| 回归 | 真实鼠标、托盘、in-place 缓存沿用 v3.0.28 路径 | 透明角 underlay `BN_CLICKED id=1 count=1`；中心拖拽 `(1200,300)-(1620,920)` → `(1235,325)-(1655,945)`；同一 PID、无子进程、exit 0 |
| Release 资产 | v3.1.0 只发 3D 包；旧的 `.github/workflows/release-assets.yml` 改为手动触发，避免 `app/**` 变更再自动构建 2D portable/source | Release 页面最终只有 `whale3d-whale-girl-v2.zip` 与其 `.sha256` |

### 体积与内存

| 项 | 实测 |
| :--- | :--- |
| `whale3d.exe` | **1,315,840 B**；比 v3.0.28 的 1,302,528 B 增加 **13,312 B** |
| `whale_girl.vrm` | **351,708 B**（原 `.glb` 350,332 B 仍保留作 fallback） |
| 运行负载（exe + SDL3.dll + VRM） | **7,052,651 B（6.72 MiB）** |
| 可运行包 `whale3d-whale-girl-v2.zip` | **2,803,800 B（2.67 MiB）**，SHA256 `C76621D1856F092F859D9A97BE0DE64E70C56D3988E0DD6BD4F721D3422B871E` |
| 工作目录 in-place 私有字节 | 97,837,056 首次；98,078,720 切 placeholder/切回 `.vrm`/两轮后不增长；PID 15860，无子进程 |
| 包内临时目录私有字节 | 98,328,576 首次；98,365,440 四轮切换后不增长；PID 32988，无子进程；仍低于 100,000,000 B |
| 帧率 | 28.2–29.0；切换后的首帧 4.4–6.1，随后恢复 |
| CPU | 31.1–35.8% 单核（10 秒窗口；spring on/off 无显著差异，渲染与 alpha 回读为主） |
| RSS | 约 70.1 MB |

### 已知边界

1. 这是**最小 VRM 子集**：只有 humanoid 映射和两骨 `VRMC_springBone`；没有 MToon、expressions/BlendShape、look-at、spring colliders 和逐关节完整链条。
2. 弹簧只作用于 root/tip 两骨链，tip 跟随 root 的局部相对变换；不是完整 VRM 逐关节物理。视觉上已经能让头发/尾巴摆，但不能宣称“任意 VRM 直接可跑”。
3. 基础 idle 动画仍由 ozz 采样；弹簧是叠加层。`WHALE3D_ANIMATOR=self` 时当前不应用弹簧层，这是下一步要补的接线。
4. CPU 约三分之一单核并不低；主要成本在每帧 alpha 回读与 30fps 渲染，不在 4 条弹簧。后续优化要从回读频率/窗口区域更新入手，不能把账算到 SpringBone。
5. 没有用外部第三方 VRM 样例验证兼容性；当前 `.vrm` 是项目自有 GLB 的扩展容器。

## 风险与未决

1. **透明 OpenGL 在混合显卡/不同驱动上不保证一致。** SDL3 源码对 Windows 透明窗口有 `FIXME: does not work on all hardware configurations with different renders` 的注释；本机 GTX 1060 通过，但需要在核显/双显卡机器上复测。
2. **透明命中区已按“目标 + 回调”两段闭环。** `WM_NCHITTEST` 在角色中心返回 `HTCLIENT`、透明角落返回 `HTTRANSPARENT`；`SetWindowRgn` 后，干净 topmost underlay 的 `WindowFromPoint` 在透明角落返回测试按钮 `BUTTON`，角色中心仍返回 pet。进一步用 `SetCursorPos` + `mouse_event` 的真实 OS 级输入：透明角落触发 underlay `BN_CLICKED count=1`，角色中心拖拽把窗口从 `(1200,300)-(1620,920)` 移到 `(1235,325)-(1655,945)`，underlay 计数仍为 1。物理手人工点击仍可做最终目检，但合成输入层的旧 harness bug 已排除。
3. **v1 仍是风格化低面数**：曲面脸贴片、近似的侧发/后发、单片鲸尾、没有落地阴影；表情只有 open / blink / smile 三帧，没有眼球转动、口型同步或情绪混合。它是可辨认的第一版，不是美术定稿。
4. **PySide6 面板和云端功能尚未迁移。** `ai_profiles`、`_chat_cloud`、云端 API 路由都还在 Python 侧；在 C++ 核心稳定前，不要拆掉现有服务。
5. **VRM 已接入最小子集；ozz 只接到采样层。** 当前证明的是壳、glTF 加载、蒙皮、ozz 采样、VRM humanoid 映射和两骨 SpringBone；未证明 MToon、expressions/BlendShape、look-at、spring colliders、blend/IK 或 root motion 管线。
6. **“单包 20–30MB 且全功能保留”仍不成立。** 若坚持单包，PySide6 必须重写为 Win32/D2D 或本地 HTML；这是下一阶段的大工程，不是接个 VRM 就能解决。
7. **模型切换已改为默认 in-place 模型缓存，不再重启进程。** 同一 PID、同一 GL context、同一窗口，切换只换 active `Impl*`；首次 placeholder 加载 4ms，缓存命中 0ms；私有字节 98.0–98.2MB，四轮不增长。`--relaunch` helper 仅作为 `WHALE3D_SWITCH=relaunch` 的 A/B/fallback，峰值 97.3–97.5MB、空窗 1.55–1.61s。
8. **Win11 托盘图标已写入固定标记。** `ShellUi::promoteTrayIcon` 按 `ExecutablePath` 匹配 `HKCU\Control Panel\NotifyIconSettings\674768749172540869`，写 `IsPromoted=1`；Explorer 重启一次后，`(1611,0)-(1643,48)` 的精确裁剪显示蓝发鲸鱼娘图标。新安装首次运行仍需用户重启一次 Explorer/重新登录，应用没有自动重启 Explorer。

## 下一步

1. **托盘/设置/模型切换已收口**：启动、右键菜单、设置页开关、`walk + smile + ozz` 应用、失败组合提示、模型切换、退出 0 都已实测；本轮不继续扩托盘功能。
2. **命中区已按“目标 + 回调”两段收口。** `WindowFromPoint` 在干净 topmost underlay 的透明角返回测试按钮 `BUTTON`，角色中心返回 pet；`SetCursorPos` + `mouse_event` 的 OS 级输入已触发按钮 `BN_CLICKED`，角色中心拖拽也通过。下一步只保留用户物理手最终目检，不再改命中区。
3. **模型切换已真正 in-place**：同一 PID/窗口/GL context 内切换 active `Impl*`，首次 placeholder 加载 4ms、缓存命中 0ms；四轮后私有字节 98.2MB，不增长。`--relaunch` 仅作 A/B/fallback。
4. 把云端/AI 作为独立可选服务保留，核心包不打包 Python；`ai_profiles`、`_chat_cloud`、云端 API 路由不能丢。
5. 若要继续动画，再评估 ozz 的 blend/IK/root motion；当前不把 glTF importer 或 VRM 运行时一起拖进来。
6. 每一步都记录“新增字节数”和“私有字节增量”，不让包体积和 RAM 在无感知的情况下回涨。
7. **第 10 步（v3.1.0）已完成**：`.vrm` 默认加载、4 条两骨 SpringBone、窗口位移惯性输入、A/B 开关和包内实测都已收口。下一步按路线进入 v3.2.x：先做情绪参数总线（`emotion/intensity/gaze_target/body_lean/source`），再接 ASR/TTS/LLM 的独立服务闭环；在此之前不把认知层塞进 3D 渲染进程。
