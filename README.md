# 鲸鱼娘桌宠 · WhaleGirlPet

> 一只住在 Windows 桌面上的 DeepSeek 鲸鱼娘（社区昵称「大肥鱼」），会走路、会打工、会跟你说话。

> **路线声明（2026-11-26）**：2D 主线已放弃，主线转向 3D。自 v3.0.28 起，新功能和新包只走 3D C++/SDL3/OpenGL 壳；v3.1.0 已落地最小 VRM 1.0 + 4 条两骨 SpringBone，v3.1.1 修复 Windows 安装/升级链路。2D 源码、素材和历史 Release 保留作归档/回滚，不再作为后续发布目标。全文见 [`DECLARATION.md`](DECLARATION.md)。

<p align="center">
  <img src="assets/ui/pet.ico" alt="WhaleGirlPet" width="96" />
</p>

<p align="center">
  <strong>3D 桌面壳主线 · C++/SDL3/OpenGL · 2D PySide6 历史归档</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pypi.org/project/PySide6/"><img src="https://img.shields.io/badge/PySide6-6.x-41CD52?style=flat&logo=qt&logoColor=white" alt="PySide6"></a>
  <a href="https://github.com/cnbprd/WhaleGirlPet/releases"><img src="https://img.shields.io/github/v/release/cnbprd/WhaleGirlPet?style=flat&logo=github&color=6e40c9" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-D22128?style=flat" alt="License"></a>
  <a href="https://github.com/cnbprd/WhaleGirlPet/stargazers"><img src="https://img.shields.io/github/stars/cnbprd/WhaleGirlPet?style=flat&logo=github" alt="Stars"></a>
</p>

---

## 这是什么

这不是「会说话的桌面挂件」，而是一个**把养成、工作流、语音、桌面维护缝在一起的小型桌面应用**。

大多数桌宠解决的是「屏幕上多一个会动的图」。本项目解决的是另一个问题：

> **一个人一天里被打断几十次，能不能让一个不烦人的东西，替你把琐事接住？**

所以它的定位很明确：

- **不是** 满屏弹窗的骚扰器：默认静音模式，闲聊只出气泡不出声，真正有事才开口。
- **不是** 纯观赏摆件：打工任务、定时任务、喝水久坐提醒、垃圾清理、桌面整理都在真做事。
- **不是** 云服务产品：本地跑，账号档案存在 `%APPDATA%\WhaleGirlPet`，可离线。

仓库只放源码与文档；可执行安装包走 [Releases](https://github.com/cnbprd/WhaleGirlPet/releases)。

## 当前 3D 主线（v3.1.2，v3.2 开发中）

这一版把“身体”先接上了，认知层还没有搬进来：

| 能力 | 状态 |
|---|---|
| 透明无边框 3D 窗口、置顶、拖拽 | 已通；420×620，OpenGL 3.3 |
| 点击穿透 / Win11 托盘固定 / 同进程 in-place 换模 | 已通；真实鼠标和四轮内存实测在 `docs/3d-transition.md` |
| 角色格式 | 最小 VRM 1.0 `3d/assets/models/whale_girl.vrm`，19 humanoid bones + 4 条两骨 SpringBone |
| 基础动画 | ozz 采样 idle/walk；自研采样保留 A/B |
| 头发/尾巴二次动力学 | 已通；窗口位移惯性输入，`WHALE3D_SPRING=0` 可关闭 |
| 情绪参数总线 | v3.2 step 1/1b/4/5 已通；本机 UDP `127.0.0.1:47832`；`happy 0.8` 是 80% 的笑，`curve.attack_ms/release_ms` 控制进出包络；可选 `gaze/lean` 转 head/neck、倾 spine/chest，见 `docs/3d-emotion-bus.md` |
| 姿态层 | v3.2 step 5 已通；可选 `gaze` / `lean` 小角度骨旋转，不带字段时回正；只是“转头”不是眼骨/BlendShape，见 `docs/3d-emotion-bus.md` |
| 认知层 | Python 侧已接情绪桥：`P_USER / P_LLM / P_AUTO` 仲裁后发本机 UDP；ASR/TTS 仍未进 3D 渲染进程 |
| 情绪桥 | v3.2 step 3 已通；聊天发送/回复/情绪衰减三路接入，TTS 实际播放期间延长 P_LLM，3D 端日志可看到 `source=P_USER/P_LLM`，见 `docs/3d-emotion-bus.md` |

细节：[`3d/README.md`](3d/README.md)、[`docs/3d-transition.md`](docs/3d-transition.md)。下面的“功能概览”是 2D 历史归档能力，不代表当前 3D 核心包已全部迁移。

---

## 功能概览

| 模块 | 能力 | 说明 |
|---|---|---|
| 桌宠本体 | 透明无边框、始终置顶、拖拽、站立/走/跑/摔倒/翻滚 | 真透明合成（不用硬边蒙版），窗口外扩 18% 给动作留活动余量 |
| 养成系统 | Lv / 经验 / 金币 / 饱食度 / 心情 / 亲密度 | 投喂四种零食，拍拍涨好感，频繁戳会抗议 |
| 打工任务 | 写工作总结、学习知识点、清理临时目录 | 完成结算金币与经验，清理只动临时目录 |
| 时间管理 | 定时任务、喝水 / 久坐提醒、22 点休息 | 夜间自动切换成低活动量 |
| 聊天 | 流式对话、气泡模式、聊天面板 | 支持 OpenAI 兼容 / 智谱 / Ollama / dafeiyu.cpp 本地模型 |
| 语音 | Edge TTS + 8 种方言人格 + 真人音色提炼 + 唤醒词 | 唤醒词：`大肥鱼`、`你好，大肥鱼`、`你好，<当前角色名>` |
| 记忆与知识 | 长期记忆、知识库、联网搜索 | 对话里自动召回 |
| 环境播报 | 天气、科技新闻、全屏自动躲避、拔电省电 | 全屏应用时自动隐藏，退出全屏回来 |
| 桌面维护 | 满屏跑撞图标掉落与复位、桌面擦除、垃圾清理 | 图标掉落后会自己慌张地摆回去 |
| 安全体检 | 启动项 / 防火墙 / 补丁 / 账号风险分项检查 | 只读检查项与本地模拟修复，不做破坏性操作 |
| 外观 | 多形态多皮肤、三档主题（跟随系统 / 浅色 / 深色）、macOS 风格侧边栏面板 | 主题读注册表 `AppsUseLightTheme` |
| 更新 | GitHub Releases 检查 + 分块下载 + SHA256 校验 | 同版本不提示，装机版自动调安装器 |

---

## 快速开始

### 方式一：3D 核心包（当前主线）

前往 [Releases](https://github.com/cnbprd/WhaleGirlPet/releases/latest) 下载：

| 文件 | 说明 |
|---|---|
| `whale3d-whale-girl-v3.zip` | 3D 核心包，解压即用；含 `whale3d.exe` + `SDL3.dll` + `assets/models/whale_girl.vrm`；VRM + 4 条两骨 SpringBone；exe 为 GUI subsystem，不会额外弹终端框 |
| `WhaleGirlPet-Setup-x.y.z.exe` | 鲸鱼娘安装包，无需管理员权限；目录页可改安装位置。默认目录按顺序：已有 3D 安装的 `InstallLocation` → 旧版 2D 3.0.27 目录 → `F:\WhaleGirlPetApp` → `%LOCALAPPDATA%\WhaleGirlPet3D`。检测到旧版 2D 时由安装器直接迁移（保留用户数据，删除旧程序/旧卸载项）。v3.0.28 / v3.1.0 / v3.1.1 / v3.1.2 共用同一安装位置，后装覆盖升级 |

安装包当前未签名；SmartScreen 若提示“未知发布者”，请先对照同名 `.sha256` 校验，再选择“更多信息 → 仍要运行”。受信任代码签名方案和接入条件见 [`docs/code-signing.md`](docs/code-signing.md)。

### Code signing policy

**Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).**

Status (2026-11-26): the SignPath Foundation application has been submitted and is pending review. Until it is approved and signing is executed, the current Release artifacts remain unsigned and Windows may show “Unknown publisher”.

Signing scope is the Windows artifacts: `whale3d.exe` and `WhaleGirlPet-Setup-<version>.exe`. Authors / reviewers / approver: [cnbprd](https://github.com/cnbprd) (repository owner); all team members use MFA for GitHub and SignPath. Full policy: [`CODE_SIGNING_POLICY.md`](CODE_SIGNING_POLICY.md). Privacy statement: [`PRIVACY.md`](PRIVACY.md).

2D 安装包是历史归档，不再作为新版本发布目标；下表只用于旧 Release 说明：

| 文件 | 说明 |
|---|---|
| `WhaleGirlPet-Setup-x.y.z.exe` | 2D 安装包，含开始菜单与卸载项（历史） |
| `WhaleGirlPet-x.y.z-portable.zip` | 2D 免安装，解压即用（历史；onedir：根目录里是 `WhaleGirlPet.exe` + `_internal\`，别只拖走 exe） |
| `WhaleGirlPet-x.y.z-source.zip` | 源码快照（历史） |
| `*.sha256` | 校验值，`certutil -hashfile <文件> SHA256` 对比 |

### 方式二：3D 源码构建

```powershell
git clone https://github.com/cnbprd/WhaleGirlPet.git
cd WhaleGirlPet
powershell -ExecutionPolicy Bypass -File 3d\build.ps1
.\3d\whale3d.exe
```

工具链、SDL3、ozz 静态库和模型说明见 [`3d/README.md`](3d/README.md)。`3d\build.ps1` 只编译 `main.cpp` / `model.cpp` / `shell_ui.cpp`，不依赖 Qt 或 Python。

### 方式三：2D 源码运行（历史归档）

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app\main.py
```

> 本地大模型（可选）：把 `dafeiyu.cpp` 运行时与 `.gguf` 模型放到 `runtime/`，程序会自动探测；不装则退回在线接口。
> 想让她能看屏幕（本地视觉）：再放一份与主权重配套的 `mmproj*.gguf`（例如 `gemma4-e2b-it.gguf` 配 `mmproj-gemma4-e2b-f16.gguf`）到同一目录，启动时自动加 `--mmproj`。

### 打包自己的版本

```powershell
.\build.ps1                 # PyInstaller onedir → dist\WhaleGirlPet\ （exe + _internal）
tools\inno\ISCC.exe installer\whale_pet.iss   # Inno Setup → dist\WhaleGirlPet-Setup-x.y.z.exe
```

> v3.0.18 起是 **onedir**：发布物是一个目录，不是单个 exe。单文件（onefile）每次冷启动都要把 64MB 解到 `%TEMP%`，实测就绪 4.55s / 常驻 170MB；onedir 是 0.76s / 83MB。

---

## 目录结构

```
WhaleGirlPet/
├── app/                 # 全部业务代码（PySide6 + 线程 + 本地模型接入）
│   ├── main.py          # Controller：托盘、快捷键、语音、自主行动、定时
│   ├── pet_window.py    # 桌宠窗口：绘制、动作、拖拽、右键菜单
│   ├── panel.py         # 控制面板：10 个页面 + 侧边栏
│   ├── panel_v2.py      # 音频库 / 自定义模型 / 安全 / 账号 / 定时任务（记忆页已不挂载）
│   ├── tts.py           # Edge TTS 封装 + 音色档位
│   ├── voice_profile.py  # 真人音色提炼映射（基频 → pitch 反查）
│   ├── updater.py       # GitHub Releases 检查与下载校验
│   ├── theme.py         # auto / light / dark 解析
│   └── …                # 养成、任务、记忆、安全、天气、图标等模块
├── assets/              # 立绘、表情、UI qss、音效
├── installer/           # Inno Setup 脚本
├── docs/                # 架构、功能、更新日志
├── build.ps1            # 一键打包
└── WhaleGirlPet.spec    # PyInstaller 配置
```

架构与模块边界见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。

---

## 配置

配置与数据都在 `%APPDATA%\WhaleGirlPet\`：

| 路径 | 内容 |
|---|---|
| `accounts\<档案>\config.json` | 位置、缩放、皮肤、主题、语音、AI 后端等 |
| `accounts\<档案>\voices\` | 音效与 TTS 缓存 |
| `memory\`、`kb\` | 记忆库与知识库 |

常用配置项：

| 键 | 默认 | 说明 |
|---|---|---|
| `theme` | `auto` | `auto` / `light` / `dark` |
| `mute_idle` | `true` | 静音模式：闲聊/播报只出气泡不出声 |
| `tts_on` | `false` | 是否用 TTS 说话 |
| `voice_profile` | `linluo` | 音色档位（`linluo` / `jingjing` / `off`） |
| `alpha_mask` | `false` | 硬边蒙版开关（开启会有锯齿与裁边，默认关） |
| `auto_on` | `true` | 自主行动 |
| `update_repo` | `cnbprd/WhaleGirlPet` | 联网更新仓库 |

---

## 快捷键

| 组合 | 作用 |
|---|---|
| `Alt+Shift+F` | 显示 / 隐藏桌宠 |
| `Ctrl+Alt+V` | 语音说一句（先说唤醒词再说话可连续对话） |

托盘图标：左键单击切换显示，右键出菜单（面板 / 显示隐藏 / 自主行动 / 静音 / 主题 / 退出）。

---

## 已知限制

- 立绘放大到 0.7 倍时素材 alpha 边缘会有台阶（非蒙版造成），需要 2 倍超采样才能彻底平掉。
- 摔跤类 60°+ 翻转贴到屏幕最边缘时，仍可能轻微出界。
- 不同皮肤立绘来自不同批次的生成，脸与服装细节不完全一致（正在统一重绘）。
- 语音唤醒需要先按 `Ctrl+Alt+V`，不是常驻离线监听。
- 仅支持 Windows（依赖 `winreg`、DWM、`GetSystemPowerStatus`）。

---

## 更新日志

见 [`CHANGELOG.md`](CHANGELOG.md)。当前版本 **v3.1.2**。

---

## 贡献

1. Fork，建分支 `feat/your-feature`
2. 提交信息建议 [Conventional Commits](https://www.conventionalcommits.org/)
3. 发 PR，附上复现步骤或截图

提交前请确认没有把 `dist/`、`build/`、`runtime/`、`.venv/`、`%APPDATA%` 下的配置与密钥带进来。

---

## 许可与声明

代码以 [MIT](LICENSE) 许可开源。

- 角色形象为 DeepSeek 鲸鱼娘（社区昵称「大肥鱼」）的同人二创，**角色相关权利归原权利方**，本仓库不主张任何角色版权。
- 立绘与音效由生成/公开素材整理而来，仅供个人非商业使用；商业用途请自行确认授权。
- 本项目与 DeepSeek 官方无隶属关系。

### 第三方与参考（动画引擎）

`app/skeletal.py`（v3.0.13 起的骨骼动画）**未复制任何第三方源码**，代码自写，
仅在架构设计上参考了两份开源资料，完整声明见 [`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md)：

- **Godot Engine 4.x** 的 2D 骨骼系统（`Skeleton2D` / `Bone2D` / `Polygon2D` 顶点权重蒙皮），MIT 许可 —
  https://docs.godotengine.org/en/stable/tutorials/animation/2d_skeletons.html
- **Inochi2D**（开源 2D rigging，Live2D 的开源替代），BSD 2-Clause —
  https://inochi2d.com

明确**未使用**：Spine Runtime（许可要求最终用户自行持有 Spine Editor 授权，不适合免费分发）、
Live2D Cubism SDK（专有许可）。

如果这个项目对你有用，点个 Star 就是最实在的支持。

