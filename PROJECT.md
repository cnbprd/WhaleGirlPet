# 鲸鱼娘桌宠 · 项目交接

> 这是给「新窗口」看的入口文件。豆包会话之间的上下文不互通，所以上一轮对话的结论、改了什么、
> 怎么跑、坑在哪，全部写在这里。项目自带 Python 环境，整个目录可以整体搬走或复制。

- 版本号：`2.9.8`（`app/paths.py` 的 `APP_VERSION`，安装脚本 `installer/whale_pet.iss` 同步）
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
| `app\` | 全部源码（45 个 py）：`main.py` 主控、`panel.py` 面板、`panel_v2.py` 分页、`pet_window.py` 窗口与动作、`tts.py` 语音、`persona.py` 人格、`audio_manager.py` 播放、`model_dl.py` 模型下载、`voice_tweak.py` 音色指令解析；v2.9.7 新增 `care_ui.py`（背包/商城/状态栏/选项气泡）、`companion.py`（撒娇与动作台词）、`snacks.py`（零食目录与定价）、`hardware.py`（硬件检测与推荐）、`maker.py`（做小软件） | 数百 KB |
| `assets\` | 皮肤 `skins/`、表情 `expressions/`、动作帧 `actions/`、萝莉形态 `loli/`、图标 `ui/`；`_raw` 是历史原图备份，`_matting` 是抠图/对比/录屏抽帧的工作区 | 0.43 GB |
| `runtime\models\` | 4 个 gguf：Qwen3-4B-Q4_K_M、qwen35-4b-Q4_K_M、gemma4-e2b-it、deepseek-coder-6.7b-instruct | 11.8 GB |
| `runtime\dafeiyu\` | 本地 dafeiyu.cpp 服务端（`dafeiyu-server.exe` + DLL） | 3.7 GB |
| `dist\` | 当前版本安装包与 portable（约 150~250 MB；2.6.0–2.9.3 的历史包已清掉） | ~150 MB+ |
| `docs\` | `ARCHITECTURE.md` / `FEATURES.md` / `CHARACTER.md`（角色母版规范）/ `github-桌宠参考.md` | 26 KB |
| `tools\` | 抠图、批量派生、录屏分析、去底等一次性工具脚本 | 40+ 个 |
| 根目录 `test_*.py` | 59 个历史自检脚本，按版本命名（`test_v293.py`、`test_v294.py` 等） | 几十 KB |
| `.venv\` | 项目自带 Python 环境 | ~840 MB |

## 三、面板现状（9 页）

`养成` / `打工` / `定时任务` / `聊天` / `设置` / `音频库` / `自定义模型` / `安全体检` / `账号形态`

- 「定时任务」是 v2.9.8 合并页：专注计时 + 日常提醒 + 定时任务 + 昨天使用情况。
- 「设置」页内是 5 个子标签：关于与更新（含软件信息/版本/检查更新）、储存位置、语音唤醒、天气资讯（天气 + 要闻/体育/娱乐/科技/金融/时政 六类资讯）、桌宠行为。

### v2.9.8（2026-11-25）的改造（8 条）

1. **合并页**：专注计时/提醒 + 定时任务 → 一页「定时任务」。
2. **模型仓库**：本地大模型组补列表（★推荐、体积、已装/可下），双击下载。
3. **迁移删旧**：复制完删旧目录；占用项进 `pending_cleanup.json`，下次启动 `paths.cleanup_pending()` 再清。
4. **金币不再自动发**：删 `coin_timer`，只从打工结算来（也去掉了那句到账语音）。
5. **动作不换衣**：仅默认女仆装套动作帧；换装/萝莉形态保留当前立绘，用程序化动作。
6. **睡觉有姿态**：透明度 0.70 + 慢呼吸 + 歪头打盹。
7. **设置拆四模块**：子标签页；关于页补程序/数据/引擎/仓库信息；天气资讯加六类资讯。
8. **设置名字**：页内「设置」标题 + 右键/托盘入口统一叫「设置…」。

### v2.9.7（2026-11-25）的改造（14 条）

1. **一键发版**：`tools\release.ps1`（打包 + 安装包 + `git add/commit/push`），`-Bump` 自动升末位。
2. **换装白眼修复**：`blackgown` / `blackgreen` / `blackred` 三套原图无瞳孔，已重绘；备份 `assets\_matting\v297\backup_*.png`。
3. **旧引擎名清理**：可执行入口全部 `dafeiyu-*`；日志/下载缓存/测试脚本/文档已改名。**10 个 `llama-*.dll` 不能改**
   （实测改名后 `0xC0000135 STATUS_DLL_NOT_FOUND`，Windows 导入表写死）。
4. **「设置 → 桌宠行为」**：碎碎念、点击音效、始终置顶、跟随鼠标、换装、大小、形态、主题 八项集中；主题从托盘迁入。
5. **动作与投喂撤出面板**：养成页只留 背包 / 零食商城 / 去打工；动作每 60 秒自判，12~20 分钟偶发两选项气泡（12 秒自随机）。
6. **背包**：`state.bag`；饿了吃、投喂不饿就存包、背包窗口点一下即吃。
7. **零食商城**：`app\snacks.py` 七类、4~45 金币；联网补货；语音「零食商城」呼出；入口在打工页底部。
8. **打工语音指令**：3 个活、10 秒不选自随机开工；状态栏带「去打工」。
9. **状态栏大气泡**：饥饿/口渴/心情差/金币<20% 触发；打工/投喂/喝水；40 秒自收、10 分钟冷却。
10. **硬件推荐**：`app\hardware.py` 读显卡/显存/内存/线程，`best()` 给推荐与理由。
11. **换硬件提醒**：启动 30 秒 + 每小时 `check_and_update`，比对显存/内存/线程。
12. **换硬件自动适配**：写 `llm_model_recommend` / `llm_model_file`，未下载则提示去下载。
13. **做小软件**：`app\maker.py`；语音/聊天「做个小软件」→ 模型出码 → 10 类风险拦截 → 存 `数据目录\scripts` → 用户点头才跑（20 秒超时）。
14. **主题迁入设置**：`_tab_prefs` 内下拉，切换即重刷 QSS。

### v2.9.6（2026-11-25）的改造

1. **「设置」是新的**（`panel._tab_prefs`）：关于与更新、储存位置（含「打开数据目录」）、语音唤醒
   （可加唤醒词，存 `config["wake_words_extra"]`）、天气资讯模块（天气开关/城市/科技新闻/试一条）、
   聊天入口（一行说明 + 「打开聊天」，与左侧聊天页是同一份记录）。
2. **原「设置」改名「自定义模型」**：留联网后端管理、自主行动，并接收从「语音人格」迁来的本地大模型组
   （`panel._build_llm_box`）。
3. **「语音人格」改名「音频库」**：原「设置」页的「音频设置（本地导入）」整组迁入（`panel._build_audio_box`），
   页面写明「换音色只换语气和口音，不动性格」。
4. **「定时」改名「定时任务」**。
5. **养成页名字锁定**：默认只读，点「修改」解锁、点「保存」写库并锁回去（`_on_name_edit` / `_on_name_save`）。
6. **性格只从聊天长**：`emotion.apply_text()` 按夸奖/凶人/撒娇/示弱四类线索微调性格，面板只读展示，
   没有任何手动改性格的入口。
7. **储存位置可迁**：`paths.data_dir()` 读 `%APPDATA%\WhaleGirlPet\data_root.txt` 指向新根；设置页整目录复制后重启生效。
8. **剪贴板先授权**：托盘「搜索剪贴板内容（读取前先问你）」→ `ask_search_clipboard()` 弹框，同意才读。
9. **答不上来先联网学**：`_finish_reply` 命中「不知道/查不到/没联网」→ `_web_relearn()` 抓搜索结果，
   让模型用自己的话重答，prompt 禁止照搬与列链接。

### v2.9.5（2026-11-25）的三项（仍在）

1. **启动屏**：`app/splash.py` 的 `LoadingSplash` —— v2.9.6 已改成**透明纯人物**：三帧动作轮播
   （default/wave/dance，每 1.6 秒）、换帧小跳、持续浮动与走动、脚下五点绕圈代替进度条；
   没有卡片、没有进度条、没有版本号。脚底线 380、点环 +22、文字基线 +80。
   `main()` 先关掉 PyInstaller 原生启动图，再显示它；`Controller(defer_show=True)` 分三步初始化。
2. **启动不再弹更新框**：自动检查 20 秒后跑，`silent` 分支只发托盘通知 + 写 `pending_update`。
   v2.9.6 起：手动点「检查更新」发现新版本后，每小时托盘提醒一次，下载完成即停；对话框 30 分钟自动关。
3. **对话气泡式安装向导**：`installer/whale_pet.iss` 四张自定义页（装哪 / 桌面图标 / 装完叫醒 / 选装本地模型），
   左侧白气泡 + 右侧立绘 + 两个选项；右上角小图换成全透明 `art\small_blank.png`；
   选盘只选到盘根会自动补 `WhaleGirlPetApp` 并建目录；30 分钟系统空闲由 `art\idle_close.ps1` 关掉窗口。

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
8. **PyInstaller onefile 启动有 1~1.5 秒空白**（70MB 自解压）。v2.9.6 已加原生 `Splash`：
   `WhaleGirlPet.spec` 里传 `Splash` 对象，并**必须把 `splash_obj.binaries` 一起塞进 EXE 参数**——
   Python 3.14 用的是 Tcl 9（`tcl90.dll` / `tcl9tk90.dll`），不显式带上 bootloader 会报
   `SPLASH: could not find requirement tcl90.dll in archive` 并弹 Error 框（`assets\_matting\boot_0.png` 拍到了）。
   程序起来后 `main()` 里 `pyi_splash.close()` 让位给透明自绘屏。
9. **Inno 自定义页的类型名是 `TWizardPage`**（不是 `TCustomPage`），`CreateCustomPage` 返回它；
   运行时 `WizardForm.DirBrowseButton` 即使 `DisableDirPage=yes` 仍可借用来自已弹目录选择框。
10. **Inno 6 没有 `TTimer`**（编译报 `Unknown type 'TTimer'`），"30 分钟无人操作自动关"只能外挂
    `installer/art/idle_close.ps1`（`GetLastInputInfo` + `GetTickCount`，20 秒轮询，见 `installing.flag` 立即退出）。
11. **面板内容变多别直接套 `QScrollArea`**：v2.9.6 试过把每页包一层滚动区，结果主题 QSS 的透明背景失效、
   分组标题被视口裁掉（截图可见灰块压在字上）。最后改成压缩页面本身（合并成两行、去掉长说明），
    设置页五块仍能一屏放完。

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
- [x] 版本号升到 `2.9.6`（`app/paths.py` + `installer/whale_pet.iss` 四处；CI 自动读版本）
- [x] dist 旧包清理：16,934 MB → 143 MB（历史安装包/portable/source/sha256 + `dist\runtime` 副本）
- [ ] 托盘右键实际点一次「搜索剪贴板内容」，确认授权框出现、拒绝时不读剪贴板
- [ ] 「答不上来先联网学」跑一次真实问答（现在只验证了代码链路）
- [ ] 安装向导 30 分钟空闲关窗与更新每小时提醒，各跑一次真机计时（本轮都没等满）
- [ ] 模型库「联网添加」跑一次真实大文件下载（目前只验证了地址解析与线程接线）
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
