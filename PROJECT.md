# 鲸鱼娘桌宠 · 项目交接

> 这是给「新窗口」看的入口文件。豆包会话之间的上下文不互通，所以上一轮对话的结论、改了什么、
> 怎么跑、坑在哪，全部写在这里。项目自带 Python 环境，整个目录可以整体搬走或复制。

- 版本号：`2.9.5`（`app/paths.py` 的 `APP_VERSION`，安装脚本 `installer/whale_pet.iss` 同步）
- 平台：Windows 10/11，Python 3.14.7
- 远端仓库：https://github.com/cnbrd/WhaleGirlPet （`git remote -v` 可查，SSH 443 通道已配好）
- 发布产物：CI 的 `release-assets.yml` 现在从 `app/paths.py` 读版本号，Release 不存在会自动创建，
  所以以后升版本只改 `paths.py` 与 `whale_pet.iss` 两处，push 到 main 即自动打包上传

---

## 一、怎么跑（不装环境也能跑）

```powershell
cd F:\WhaleGirlPet
.\.venv\Scripts\python.exe app\main.py      # 直接跑源码
```

- `.venv` 是**项目自带**的虚拟环境（Python 3.14.7 + PySide6 6.12 + edge-tts + psutil + pycaw），
  已经不再依赖 `C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\.venv`。
- 依赖清单见 `requirements.txt`；重装：
  `.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- 打包：`.\build.ps1`（PyInstaller 走 `WhaleGirlPet.spec`，再 `installer\whale_pet.iss` 出安装包）。

## 二、目录地图

| 路径 | 内容 | 体积 |
|---|---|---|
| `app\` | 全部源码（40 个 py）：`main.py` 主控、`panel.py` 面板、`panel_v2.py` 五个分页、`pet_window.py` 窗口与动作、`tts.py` 语音、`persona.py` 人格、`audio_manager.py` 播放、`model_dl.py` 模型下载、`voice_tweak.py` 音色指令解析 | 数百 KB |
| `assets\` | 皮肤 `skins/`、表情 `expressions/`、动作帧 `actions/`、萝莉形态 `loli/`、图标 `ui/`；`_raw` 是历史原图备份，`_matting` 是抠图/对比/录屏抽帧的工作区 | 0.43 GB |
| `runtime\models\` | 4 个 gguf：Qwen3-4B-Q4_K_M、qwen35-4b-Q4_K_M、gemma4-e2b-it、deepseek-coder-6.7b-instruct | 11.8 GB |
| `runtime\dafeiyu\` | 本地 llama.cpp 服务端（`dafeiyu-server.exe` + DLL） | 3.7 GB |
| `dist\` | 历史安装包（2.6.0 → 2.9.3 的 exe/zip/sha256） | 16.47 GB |
| `docs\` | `ARCHITECTURE.md` / `FEATURES.md` / `CHARACTER.md`（角色母版规范）/ `github-桌宠参考.md` | 26 KB |
| `tools\` | 抠图、批量派生、录屏分析、去底等一次性工具脚本 | 40+ 个 |
| 根目录 `test_*.py` | 59 个历史自检脚本，按版本命名（`test_v293.py`、`test_v294.py` 等） | 几十 KB |
| `.venv\` | 项目自带 Python 环境 | ~840 MB |

## 三、面板现状（10 页）

`养成` / `打工` / `番茄钟-提醒` / `聊天` / `设置` / `语音人格` / `模型库` / `安全体检` / `账号形态` / `定时`

### v2.9.5（2026-11-25）的三项

1. **启动屏**：`app/splash.py` 的 `LoadingSplash` —— 无边框浮层，圆角卡片 + 鲸鱼娘立绘浮动 +
   「鲸鱼娘加载中」+ 三个呼吸点 + 细进度条；`main()` 里先显示它，`Controller(defer_show=True)`
   分三步初始化，最少驻留 2 秒后淡出，`show_pet()` 才把桌宠一次性露出来。`PetWindow.__init__`
   新增 `show_now` 参数，构造时不再自动 `show()`。
2. **启动不再弹更新框**：自动检查更新 6 秒 → 20 秒；`_on_update_result` 的 `silent` 分支只发托盘
   通知并把 `pending_update` 写进 config，不再 `QMessageBox.exec()`。手动点「检查更新」仍会弹。
3. **对话气泡式安装向导**：`installer/whale_pet.iss` 重写 [Code] —— 三张自定义页（装哪 / 桌面图标 /
   装完叫醒），左侧白色气泡提问 + 右侧立绘 + 两个选项按钮；美术在 `installer/art/`
   （`whale.png` 立绘、`bubble.png` 气泡、`small.png` 右上角小图，全部透明底）。

### 上一轮（2026-11-24）的四项改造，仍然生效

1. **音频库页已移除**（动作音效与音量仍留在「设置」页，那不是音频库）。
2. **记忆知识页已移除**；查看方式改为托盘右键 →「打开数据目录（记忆 / 知识库 / 音色缓存）」，
   直接打开 `%APPDATA%\WhaleGirlPet\accounts\default`（里面有 `memory.db`、`knowledge.db`、`tts_cache`）。
3. **模型库分两段**：上面「■ 已安装模型（N 个，可直接用）」扫 `runtime\models\*.gguf`（非内置的自定义 gguf 也列出来），
   下面「■ 内置模型（一键下载）」。中间输入框可贴 `.gguf` 直链或 hf-mirror 仓库页 → 下完自动进「已安装」。
4. **音色实验台**（在「语音人格」页）：
   「拉取音色列表」（后台线程拉微软音色库，实测 318 个，中文 14 个排最前）→ 选音色 →
   「试听选中」→ 用一句话指令改（「尖一点」「慢 10%」「音高 20」「音量 60」「默认」）→
   「存为我的音色」（写进 `config["custom_voices"]`，和 8 个内置人格并列）。

## 四、数据与配置在哪（不在项目里）

| 内容 | 路径 |
|---|---|
| 账号数据（记忆库、知识库、语音缓存、导入的音效） | `%APPDATA%\WhaleGirlPet\accounts\default\` |
| 配置 `config.json` | 同上 |
| 模型文件 | 项目内 `runtime\models\`（可迁移） |
| 日志 | 项目内 `runtime\*.log` |

配置里存的音效路径都是 `%APPDATA%` 的绝对路径，跟项目目录搬不搬家无关。

## 五、已知问题 / 坑（都是实测过的）

1. **Edge TTS 的音量参数在服务端不生效**：同一句用 100%/70%/40% 合成，mp3 字节数三次完全相同（23616）。
   所以音量改由播放端 `QAudioOutput.setVolume` 控制（`audio_manager.play_file(path, priority, volume)`），
   实测 `volume=40 → output.volume()==0.400`，不传则按全局音频设置（80%）。
2. **双屏下桌宠会"消失"**：`pet_window._clamp_to_screen` 已改为「窗口至少 65% 留在主屏」，`follow` 分支每帧也 clamp。
   本机是 1920×1032 主屏 + 1440×900 副屏，改前能被推到副屏。
3. **睡眠表情曾用错脸且尺寸跳大**：已按母版脸重绘（303×512、透明 63.4%），窗口 339×485，与 default 314×485 同量级。
4. **GitHub 网页上传 Release 资产永远失败**：`input#releases-upload` 是 1×1 的 `sr-only` 隐藏控件，注入与拖放都无效。
   不要再试网页路径，改走 `.github\workflows\release-assets.yml`（runner 上打包 + `gh release upload`）。
5. **`gh auth login --web` 在 device flow 第一跳超时**（家宽对 github.com 阻断；`api.github.com` 与 SSH 443 正常）。
6. **离屏渲染截图里的中文会显示成方块**（offscreen 平台没有中文字体），结构可核对但字体效果必须看真实桌面。
7. **Inno 的 `TBitmapImage.Bitmap.LoadFromFile` 只认 BMP**：直接读 PNG 会在 InitializeWizard 抛
   `Bitmap image is not valid`；必须 `TPngImage.Create → LoadFromFile → Bitmap.Assign`（v2.9.5 已改）。
8. **PyInstaller onefile 启动有 1~1.5 秒空白**（63MB 自解压），之后才轮到 Python 层的启动屏；
   想更快只能改 onedir 或加 `splash` 原生启动图。
9. **Inno 自定义页的类型名是 `TWizardPage`**（不是 `TCustomPage`），`CreateCustomPage` 返回它；
   运行时 `WizardForm.DirBrowseButton` 即使 `DisableDirPage=yes` 仍可借用来自已弹目录选择框。

## 六、自检脚本怎么用

```powershell
cd F:\WhaleGirlPet
$env:QT_QPA_PLATFORM="offscreen"
.\.venv\Scripts\python.exe test_v294.py    # 面板结构 / 模型分区 / 音色指令（上一轮新增，ALL PASS）
.\.venv\Scripts\python.exe test_v293.py    # 托盘、静音模式、面板侧边栏、截图
.\.venv\Scripts\python.exe test_clamp.py   # 双屏边界
.\.venv\Scripts\python.exe test_flash.py   # 切换皮肤/表情时的尺寸与透明
```

其余 `test_*.py` 按版本号对应 `CHANGELOG.md` 的条目，命名规则一致。

## 七、下一步待办

- [x] 真实桌面开一次面板目检（中文渲染、两段分区的视觉间距）
- [ ] 模型库「联网添加」跑一次真实大文件下载（目前只验证了地址解析与线程接线）
- [x] 版本号升到 `2.9.5`（`app/paths.py` + `installer/whale_pet.iss` 四处 + README；CI 自动读版本）
- [ ] 各皮肤立绘的脸部一致性继续统一（`docs\CHARACTER.md` 是母版）
- [ ] 果冻过渡动画（形态/换装/动作切换的插值回弹）仍未实现
- [x] C 盘旧副本已删：`whale-girl-pet`（17.03 GB）与旧 `.venv`（839 MB）内容已核对一致后删除，
      C 盘释放约 17.5 GB（`C:` 剩余 798.5 → 816.0 GB）。目录壳因句柄占用暂留，重启后可 `rmdir` 掉

## 八、迁移记录（2026-11-24 → 25）

| 项 | 数据 |
|---|---|
| 源 → 目标 | `C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet` → `F:\WhaleGirlPet` |
| 文件数 / 体积 | 源 1224 个 / 17.03 GB；目标 1304 个 / 32.60 GB |
| 逐目录核对 | runtime 78/78、assets 598/598、app 40/40、tools 140/140、build 14/14 全部一致 |
| 多出的 78 个 | 全在 `dist\runtime`（F 盘原有的打包副本，15.57 GB） |
| 运行环境 | 旧 `.venv` 在 C 盘 chats 下（839 MB），已改为项目内 `.venv`（Python 3.14.7） |
| 旧副本清理 | 2026-11-25 删除 C 盘 `whale-girl-pet` + 旧 `.venv`，删除前核对「C 盘独有文件 = 0」；C 盘释放约 17.5 GB |
