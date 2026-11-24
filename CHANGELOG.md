# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

## v2.9.6（2026-11-25）

本轮是用户 16 条改造清单 + 3 个补充项的落地。

| 项 | 改动 | 实测 |
|---|---|---|
| 托盘图标换成大肥鱼 | 新增 `assets/ui/pet_flat.ico`（透明底 Q 版，16–256 七种尺寸）；`main.py:_build_tray` 图标优先取它，托盘菜单「打开控制面板」也用同一张；窗口图标同步 | 启动后托盘正常显示、菜单项带图；图标文件 140,034 字节 |
| 养成页名字锁定 | 名字输入框平时 `setReadOnly(True)`，后面加「修改」「保存」两个按钮；点修改才解锁、保存才写库并锁回去；`refresh()` 加了编辑态守卫，不会把正在输的字冲掉 | 面板实拍 `assets\_matting\v296-panel-00-养成.png`：输入框可用、修改亮、保存灰 |
| 设置→自定义模型 + 新建设置页 | 原「设置」页改名「自定义模型」（留联网后端管理、自主行动、本地大模型）；另建真正的「设置」页，放关于与更新、储存位置、语音唤醒、天气资讯模块、聊天入口 | 面板实拍 `v296-panel-04-设置.png` / `v296-panel-06-自定义模型.png`，五块内容一屏放得下 |
| 定时→定时任务 | 侧栏文案与页标题统一成「定时任务」 | 实拍 `v296-panel-09-定时任务.png` |
| 语音人格→音频库 | 页名改「音频库」，顶部说明写明「换音色只换语气和口音，不动她的性格」；原「设置」页的「音频设置（本地导入）」整组迁入 | 实拍 `v296-panel-05-音频库.png`，音量/跟随系统/动作音效/导入按钮都在 |
| 性格只从聊天长 | `emotion.apply_text()`：按夸奖、凶人、撒娇想念、示弱倾诉四类线索，极小幅改情绪与性格（示弱会让她温柔 +0.7）；面板养成页只读展示「只从你们的聊天里慢慢长出来，不能手动改」 | 面板实拍首行「性格：黏人（只从你们的聊天里…）」；`py_compile` 通过 |
| 储存位置可改并整体迁移 | `paths.default_data_dir()` / `data_dir()`：数据根目录由 `%APPDATA%\WhaleGirlPet\data_root.txt` 指向，用户可迁到任意盘；设置页提供「浏览…」「迁移到这里」「打开数据目录」「迁回默认位置」，迁移做整目录复制（`shutil.copytree`），确认后重启生效 | 设置页实拍显示当前目录；迁移与改回只走文件复制，未在用户数据上实际执行 |
| 语音唤醒（改唤醒词） | 「语音说一句」按钮迁到新设置页；新增唤醒词输入框，逗号分隔最多 6 个，存 `config["wake_words_extra"]`；`wake_words()` 把它并入候选（仍自动带「你好，X」） | 设置页实拍显示「现在的叫法：大肥鱼（可再加自己的）」 |
| 天气资讯模块 | 天气开关、城市（「保存」→ `set_weather_city` 重置坐标缓存）、科技新闻开关、「现在试一条」全部收进设置页 | 实拍里城市读到当前配置「郑州」 |
| 聊天入口合并 | 右键「陪我聊聊天」与设置页「打开聊天」都落到同一个聊天页；`_goto_chat()` 同时聚焦输入框 | 实拍设置页底部一行说明 + 按钮 |
| 剪贴板先授权 | 托盘去掉「用 Tabbit 搜索剪贴板」，改为「搜索剪贴板内容（读取前先问你）」→ `ask_search_clipboard()` 弹授权框，选「同意，去搜」才读剪贴板，读完不留存 | 实拍 `assets\_matting\v296-clip-ask.png`：弹框「读取剪贴板 / 要用我剪贴板里的内容去搜一下吗？」+「同意，去搜」「不用了」；点「不用了」后校验 `search_in_browser` 调用次数 = **0**（没读剪贴板） |
| 答不上来先联网学 | `_finish_reply` 命中「不知道/查不到/没联网…」时触发 `_web_relearn`：后台线程抓 Bing 结果 → 拼进 system 提示 → 让模型用自己话重答；prompt 明确「不许整段照抄、不许列链接和来源清单」；查不到就老实说查不到 | 静态链路完整；**未联网跑真实问答验证** |
| 启动屏原生图 | `WhaleGirlPet.spec` 用 `Splash` 对象（`splash_native.png` 360×500 深色渐变卡），并把 `splash_obj.binaries` 一起塞进 EXE——Tcl 9 的 `tcl90.dll`/`tcl9tk90.dll` 不显式带上，bootloader 会报 `SPLASH: could not find requirement tcl90.dll` 并弹错 | 首版就踩了这个错（`boot_0.png` 拍到 Error 框）；补 dll 后实拍 `boot_1.png`：解压期显示深色启动卡，程序起来后自动让位给透明自绘屏 |
| 启动屏间距微调 | `splash.py` 的脚底线 402→380、点环 +26→+22、文字基线 +52→+80，人物/点环/文字不再挤在一起 | 代码改动；未重新实拍自绘屏 |
| 安装向导加第四问 | 新增「要不要顺手装个本地模型？」页（要，装一个 / 先不装）；选「要」时在 `ssPostInstall` 写 `{app}\want_local_model.flag`，程序首次启动读到标记就自动下 Qwen3-4B（下完删标记） | 实拍四页全过：`w296_p1.png`…`w296_p4c.png`；第四页副标题两次压缩才在单行放得下 |
| 安装向导右上角图彻底去掉 | `WizardSmallImageFile` 改用全透明 `art\small_blank.png` | 实拍第一页右上角既无大肥鱼也无白方块 |
| 选盘自动建目录 | 「浏览…选盘」只选到盘根（`D:\`）时自动拼 `WhaleGirlPetApp` 并 `ForceDirectories` 建好 | 代码沿用上一轮实现，本轮未改 |
| 安装 30 分钟无操作自动关 | `art\idle_close.ps1` 看门狗：系统空闲 ≥1800 秒就结束安装窗口；开始装文件后靠 `installing.flag` 立即退出，绝不杀正在安装的进程 | 编译通过；**未等满 30 分钟实测** |
| 更新每小时提醒 | 手动点「检查更新」发现新版本后开 `QTimer` 60 分钟提醒一次（托盘 + 气泡），下载完成即停；更新对话框 30 分钟无人处理自动关闭 | 代码路径完整；**未实跑一小时** |
| 清掉 dist 历史包 | 删除 2.6.0–2.9.3 全部历史安装包/portable/source/sha256 与 `dist\runtime` 副本（根目录 `runtime` 原样保留） | dist 16,934.1 MB → 143 MB；剩 `WhaleGirlPet.exe` + `WhaleGirlPet-Setup-2.9.5.exe`，之后又产出 2.9.6 安装包 |
| 版本号 2.9.6 | `paths.APP_VERSION`、iss 的 AppVersion/AppVerName/UninstallDisplayName/OutputBaseFilename/标题同步 | 面板右上角显示 `v2.9.6`；产物 `dist\WhaleGirlPet-Setup-2.9.6.exe`（86,800,952 字节） |

## v2.9.5（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 启动加载动画 | 新增 `app/splash.py`：无边框浮层画圆角卡片——鲸鱼娘立绘轻微上下浮动、标题「鲸鱼娘加载中」+ 三个呼吸点、细进度条、右下角版本号；`main()` 改为先显示它，Controller 分三步初始化（读取配置 → 加载形象与语音 → 露出桌宠），最短驻留 2 秒再淡出 | 真实桌面连拍：约 0.6 秒出现「鲸鱼娘加载中 v2.9.5 / 正在叫醒鲸鱼娘…」，约 1.3 秒开始淡出时桌宠已就位；截图 `assets\_matting\boot_1.png`、`boot_4.png` |
| 启动不再弹更新框 | 自动检查更新从 6 秒延到 20 秒，避开启动屏；`silent` 检查发现新版本时**不再弹 QMessageBox**，改发一条托盘通知，并把 `pending_update` 记进配置，装不装由用户在面板里决定 | `_on_update_result` 的 silent 分支只调 `tray.showMessage`；手动点「检查更新」仍保留对话框 |
| 对话气泡式安装向导 | 重写 `installer/whale_pet.iss`：禁用欢迎/选择目录/任务/准备四页，改成三张自定页——左侧白色气泡提问、右侧大肥鱼立绘、气泡内两个选项按钮。位置页选「就用默认位置」或「我自己挑一个」（复用被隐藏的浏览按钮，取消则原地不动）；桌面快捷方式由 `WantDesktopIcon` 控制；装完是否立刻启动由 `WantWake` 在 `ssPostInstall` 决定 | 真实运行安装包逐页点击：612×471 窗口，三页按钮都能推进到安装进度；日志 `runtime\setup_log3.txt` 记录 Installing 与用户取消回滚 |
| 右上角图标去掉圆底 | 新增 `installer/art/small.png`（Q 版鲸鱼娘、透明底），并设 `WizardSmallImageFile`，替换 Inno 由 `SetupIconFile` 派生出的圆形徽章 | 实拍：右上角只剩 Q 版角色，无圆形背景 |
| 安装页图片加载修正 | `TBitmapImage.Bitmap.LoadFromFile` 只认 BMP，直接读 PNG 会抛 `Bitmap image is not valid`；改用 `TPngImage` 加载后 `Bitmap.Assign` | 首版运行即在 `InitializeWizard` 报错（`runtime\setup_log.txt`）；改后三页立绘/气泡正常渲染 |
| 版本号 2.9.5 | `app/paths.py` 与 `installer/whale_pet.iss`（AppVersion / AppVerName / UninstallDisplayName / OutputBaseFilename）同步到 2.9.5，README 当前版本同步 | 编译产物 `dist\WhaleGirlPet-Setup-2.9.5.exe`；窗口标题 `Setup: 鲸鱼娘桌宠 2.9.5` |

## v2.9.4（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 项目迁到 F 盘 | 全部资料（含 15.57GB `runtime` 与模型库）从 `C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet` 搬到 `F:\WhaleGirlPet`，用 robocopy 先复制不删源 | 源 1224 文件 17.03GB；目标 1302 文件 32.60GB（多出的 78 个全在 `dist\runtime`，是 F 盘原有的打包副本）。按目录核对：runtime 78/78、assets 598/598、app 40/40、tools 140/140、build 14/14 一致；`paths.runtime_dir()` 解析为 `F:\WhaleGirlPet\runtime` |
| 面板去掉「音频库」页 | 侧栏不再挂 `panel_v2.tab_audio`（动作音效/音量设置仍在「设置」页） | 侧栏 12→10 项，列表里没有「音频库」（`test_v294.py`） |
| 面板去掉「记忆知识」页 | 记忆与知识库不在面板展示；托盘新增「打开数据目录（记忆 / 知识库 / 音色缓存）」，直接打开 `accounts\default` 本地查看 | 托盘菜单出现该项；`refresh()` 里记忆段加了 `hasattr` 守卫，不再每次刷新抛异常 |
| 模型库分「已安装 / 内置」两段 | 原先只按内置目录罗列、已下载的只在行尾追加「已下载 X MB」。改为列表顶部独立「■ 已安装模型（N 个，可直接用）」分区，扫 `runtime/models/*.gguf`，非内置的自定义 gguf 也列出来；下面才是「■ 内置模型（一键下载）」 | 已安装 4 条 = 本地 4 个 gguf；分区标题顺序断言通过（`test_v294.py`） |
| 模型联网添加 | 模型库页新增输入框：贴 `.gguf` 直链或 hf-mirror 仓库页 → `model_dl.resolve_gguf_url` 解析（仓库页走 `/api/models` 挑 Q4 非 mmproj 的 gguf）→ 下载到 `runtime/models`，下完自动进「已安装」 | `hf-mirror.com/Qwen/Qwen3-4B-GGUF` → 解析出 `Qwen3-4B-Q4_K_M.gguf`；`…/x.gguf?download=true` 也能取对文件名；只接受 http(s) 与 `.gguf`，已存在不重复下 |
| 音色联网添加 + 试听 | 「语音人格」页新增音色实验台：后台线程拉微软音色库（中文排最前）→ 选音色 → 「试听选中」按当前音高/语速/音量合成播放 → 满意点「存为我的音色」写进 `config["custom_voices"]`，并与 8 个内置人格并列在人格下拉里 | 存库、下拉出现、切换生效、参数（pitch 5 / rate 3）随人格带走，5 条断言全过（`test_v294.py`） |
| 音色优化指令 | 新增 `voice_tweak.parse`：把「尖一点 / 沉一点 / 慢一点 / 快 20% / 音高 20 / 音量 60 / 默认」解析成 音高/语速/音量 三个值，逐条给出数值解释；听不懂时不动参数并提示怎么写指令 | 8 条指令逐条断言命中；「尖一点，慢 10%，音量 70」→ 滑块 (8,-10,70) |
| 修：Edge TTS 的 volume 不生效 | 同一句分别用 100% / 70% / 40% 合成，返回 mp3 字节数完全一致（23616 三次相同），确认 Edge 端音量参数对这档输出无可见影响；改为**播放端**控制：`audio_manager.play_file(path, priority, volume)` 用 `QAudioOutput.setVolume`，并延续「跟系统音量」开关 | `play_file(vol=40)` → `output.volume()==0.400`；不传 volume → 0.800（按全局音频设置 80%）；47kHz 音频正常出声 |
| 自定义音色能真的用起来 | `persona` 增加 `register_custom()` / `has()`，`get()`/`persona_index()` 合并自定义音色；`set_persona` 与 `voice_profile` 取值改走 `pers.get()`（原先写死查 `PERSONAS`，自定义音色会被拒） | `pers.get("mine_zh_CN_XiaoyiNeural")` 能读到 voice/rate/pitch |
| 项目自包含（环境进项目） | 新建项目内 `.venv`（Python 3.14.7），按 `requirements.txt` 装 PySide6 6.12.0 / edge-tts 7.3.1 / psutil 7.2.2 / pycaw 20260927，不再依赖 C 盘 chats 下的旧环境；`.gitignore` 补 `.venv/` | `.venv` 665 MB；用它跑 `test_v294.py` → ALL PASS；项目总计 33.25 GB |
| 一键启动 | 新增 `启动鲸鱼娘.bat`（pythonw 静默启动）与 `启动-查看日志.bat`（带控制台看报错） | 两个脚本按相对路径定位 `.venv`，找不到时打印建环境命令 |
| 交接文档 | 新增 `PROJECT.md`：目录地图、启动方式、面板 10 页现状、音色/模型添加步骤、数据目录、6 条已踩过的坑、测试索引、待办与迁移核对记录 | 供项目内新会话直接读，解决"新窗口看不到上次对话"的问题 |
| 版本号 2.9.4 + CI 自适配 | `app/paths.py` 的 `APP_VERSION` 与 `installer/whale_pet.iss` 四处同步到 2.9.4；CI 改为从 `paths.py` 读版本号、文件名不再写死，Release 不存在时自动 `gh release create` | 推送后 run `45435329913` 成功；Release `v2.9.4` 自动创建，6 个资产（Setup 67.29MB / portable 65.47MB / source 5.41MB + 3 个 sha256） |
| 旧副本清理 | 删除 C 盘 `whale-girl-pet`（17.03 GB）与旧 `.venv`（839 MB），删前核对「C 盘独有文件 = 0」；同时结束了占用 C 盘 dafeiyu DLL 的残留探测进程 | `C:` 剩余 798.5 → 816.0 GB（释放约 17.5 GB）；空目录壳被句柄占用暂留，重启后可 `rmdir` |
| 真实桌面目检 | 真实（非离屏）打开面板核对两页，发现音色实验台滑块右侧说明文字贴边；把提示缩短为「低 ← → 高」等三则 | 截图中文渲染正常、右上角显示 `v2.9.4`；改后滑块宽度变大、不再贴边（`assets\_matting\real-model.png` / `real-voice2.png`） |

## v2.9.3（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 修：右键托盘图标把桌宠藏了 | `tray.activated` 原先不分按键原因一律 `toggle_visibility`，右键弹菜单前先触发了一次隐藏；改为只有左键 `Trigger` 才切换 | 直接调用 `_on_tray_activated(Context)` 后 `pet.isVisible()==True`；`Trigger` 则变 False |
| 静音模式 | `_speak()` 增加 `mute_idle`：`priority=0`（闲聊、天气、新闻、自主台词）只出气泡不出声，对话回复与投喂/拍拍照常发声 | priority0 调用 TTS 次数 0；priority2 为 1；关掉静音后 priority0 恢复发声 |
| 切换类动作静默 | `SILENT_ACTIONS={"change"}`，换装动作不再播「等我换件衣服……」 | `on_action("change")` 触发 TTS 次数 0 |
| 面板改 macOS 风格 | 顶部横排标签换成左侧 `QListWidget` 侧边栏（138px）+ 右侧 `QStackedWidget`；侧栏胶囊选中态、顶部标题栏与版本号 | 侧栏 12 项、宽 138px、点选能切页；浅色与深色两套截图生成 |
| 面板数值条重做 | 原先写死 `#333` + `█░` 字符，深色主题下糊成一片；改为按主题取色的富文本色块条，低值数字标红，深色轨道提亮 | 浅色/深色放大截图各一张，文字与轨道均可辨 |
| 修：摔一跤把立绘转成横躺 | `tumble` 的 `rot` 原先是 `62 + 298*u`（一路到 360°），整张立绘在屏幕上横着躺（录屏 f_052）；限到 22° 以内的失衡摆动，保留腾空与落地压扁 | 逐帧采样 rot 峰值 22.0°、sy 最低 0.71、结束回到 idle（`test_tumble.py` ALL PASS） |
| 立绘统一（第一批） | 新增 `docs/CHARACTER.md` 作为身份母版规范；`default` / `longmaid` / `hanfu` / `sleep` 按母版重绘并替换，旧图备份在 `assets/_raw/backup_20261124` | 四张均 512 高、`alpha_min=0`，脸与母版一致 |
| 去底工具修正 | PIL 13 的 `ImageDraw.floodfill` 实测不生效（`thresh` 与种子值不匹配时静默不改像素），改为「逐行游程 + 并查集」自实现，并自动识别黑底/白底 | 黑底图透明占比 50.9%，被裙摆包围的白围裙未误伤 |
| 接外部浏览器 | 托盘新增「用 Tabbit 搜索剪贴板」：取剪贴板文本 → `QProcess.startDetached` 拉起本机 Tabbit 打开 Bing 搜索；没装则退回默认浏览器 | 探测到 `D:\Tabbit Browser\Application\Tabbit Browser.exe`；拦截调用核对 exe 路径与 URL 编码；空剪贴板不启动并给提示（`test_v293b.py` ALL PASS） |
| 开源文档 | 重写 README、新增 LICENSE（MIT + 角色二创声明）、本日志、`docs/ARCHITECTURE.md`、`docs/FEATURES.md`、`requirements.txt` | — |
| 版本号 | `paths.py`、`installer/whale_pet.iss` 四处升到 2.9.3 | — |
| 修：睡眠表情脸不一致 + 尺寸跳大 | 录屏 f_07 暴露出 `sleep.png` 是另一张圆脸、且坐姿图按图高缩放后比站姿大一整圈（窗口 466→339）。用母版脸重绘（尖耳/额前蓝宝石/闭眼眼线一致），去底后把人物重排为画布高度的 62% | 新图 303×512、`alpha_min=0`、透明 63.4%；窗口 `339×485`，与 default `314×485`、longmaid `329×485` 同量级（`test_flash.py` 无异常采样） |
| 修：双屏下桌宠"凭空消失" | `_clamp_to_screen` 原先把 `_pad` 加到右边界（上限 `scr.right()+pad`），双屏时窗口能被推到副屏；`follow` 分支也完全没有边界。改为「至少 65% 窗口留在主屏」，follow 每帧也走一次 clamp | 主屏 1920×1032 + 副屏 1440×900；推到屏外后回收，主屏内保留 65.0%；左/下边界与正常位置均不动（`test_clamp.py` ALL PASS） |
| 发布通道 | github.com 网页上传始终塞不进文件（`input#releases-upload` 是 1×1 的 `sr-only`，注入与拖放均无效），改为 GitHub Actions 在 runner 上打包并 `gh release upload` | 首次运行 9 步全绿，Release 挂上 6 个资产；CI 产物不含 `runtime/dafeiyu`，故 Setup 67.47MB < 本地 89.55MB |

### 做到一半 / 待办

- 各皮肤立绘的「脸不一致」需要统一重绘（生成批次不同），本轮未动素材。
- 果冻过渡动画（形态/换装/动作切换的插值回弹）仍未实现。
- Release v2.9.3 资产已改由 GitHub Actions 构建并上传（Setup 67.47MB / portable 65.64MB / source 5.58MB + 三个 sha256）；本地浏览器上传通道仍不通，不要再试网页拖放。

## v2.9.2（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 真人音色提炼 | `app/voice_profile.py`：B 站两段真人配音做 40ms 帧基频统计，用 Edge TTS 实测曲线反查 pitch，得 `jingjing` 363.6Hz / `linluo` 285.7Hz | 反查四组偏差 −3.3/−1.3/−0.3/+4.1 Hz；端到端 372.1Hz 对 363.6Hz 差 8.5Hz |
| 主题三档 | `app/theme.py` + `assets/ui/theme_light.qss`；托盘「主题」子菜单 | 系统浅色 → auto 解析 light；浅色下数值条清晰可读 |
| 语音唤醒词 | `wake_words()` / `_match_wake_word()`：`大肥鱼`、`你好，大肥鱼`、`你好，<角色名>` | 「今天天气怎么样」不误拦 |
| 托盘菜单合并 | 右键菜单的面板/隐藏/退出移入托盘 | 菜单项实测顺序正确 |
| 形态切换静默 | `on_form_change` 去掉语音 | 源码无 `_speak` |
| 去蒙版 + 活动余量 | 默认 `alpha_mask=False` 走真透明；`PAD_RATIO=0.18` 外扩窗口并做 pad 补偿 | 窗口 606×931 / 立绘 360×685，起跳与翻滚不裁头 |
| 发布 | Release v2.9.2 上线 4 个资产（安装包 89.56MB / portable 74.12MB / 源码 27.73MB / sha256） | `_pick_assets()` 正确挑到 Setup 与校验文件 |

## v2.9.1

- 去方形边界（`setMask` 方案，后因锯齿与裁边在 2.9.2 弃用）
- 联网更新重写：`api.github.com` latest + 分块下载 + SHA256
- 开机静默检查更新

## v2.9.0

- 天气播报（三源级联）、科技新闻、全屏自动躲避（DWM 可见边框判定）、拔电省电、右键入口

## v2.8.0

- 语音优先级抢断、自主行动权重池、夜间休息池、频繁戳抗议、脚底对齐

## v2.7.0

- 动作音效跟随语音人格（8 人格 × 20 动作共 160 条）、绿茶人格按参考视频重做

## v2.6.0 及更早

- 养成 / 打工 / 番茄钟 / 记忆知识 / 安全体检 / 多账号 / 素材与立绘多轮重做
