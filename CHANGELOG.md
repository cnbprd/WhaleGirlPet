# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

## v2.9.10（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 关于与更新页改版 | 按用户给的参考布局重排：顶部 64×64 头像 + 「鲸鱼娘桌宠」+ 版本 + 一句话；下面两组分区 | 离屏实拍 `assets\_matting\v299-about.png`（706×914） |
| 2 「源码与下载」组 | GitHub 仓库、版本发布页、问题反馈三行，每行带说明与「打开」按钮，走系统浏览器 | 三个链接指向 `github.com/cnbprd/WhaleGirlPet` 及其 `/releases`、`/issues` |
| 3 下载二维码 | 新增 `assets\ui\repo_qr.png`（398×398，白底圆角、深码），指向 releases 页；页内 132×132 展示 + 手机扫一扫说明 | 由 `tools\_make_about_assets.py` 用 qrcode 生成，实拍清晰可扫 |
| 4 顶部头像素材 | 从 `pet_flat.ico` 取最大帧、裁掉透明边、补成正方形再缩到 256，存 `assets\ui\about_logo.png` | 248×248 → 256×256，96,226 字节 |
| 5 去掉群与教程 | 不做 QQ 群、使用教程、加入社区、已满员群折叠；只留仓库、发布页、反馈与二维码 | 页面元素清点无群/教程/社区字样 |
| 6 「帮助与维护」组 | 检查更新 + 清单地址 + 看诊断日志（优先 `dafeiyu-server.log`，没有就开数据目录）+ 打开数据目录 + 软件信息（程序目录/数据目录/本地引擎） | 按钮信号已接；日志路径按运行目录解析 |
| 7 依赖 | `.venv` 新增 `qrcode`（仅生成素材用，运行时不依赖，二维码是静态 png） | `import qrcode` 通过 |
| 版本 2.9.10 | `paths.APP_VERSION`、iss 五处同步 | — |

## v2.9.9（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 设置拆成左侧独立页 | 设置页内部的五个子标签取消，关于与更新 / 储存位置 / 语音唤醒 / 天气资讯 / 桌宠行为直接成为侧栏页；`_tab_prefs` 拆成 `_tab_about`、`_tab_store`、`_tab_wake`、`_tab_ambient`、`_tab_pet_behavior`，删掉 `QTabWidget` 与子页包装 | 侧栏 9 页 → 13 页，安装版实拍 `assets\_matting\v299-installed-panel.png`（722×953） |
| 2 面板与托盘改名 | 窗口标题「控制面板」→「设置」；托盘 QAction 同步改「设置」 | 实拍窗口标题栏显示「设置」 |
| 3 图标统一大肥鱼 | `assets\ui\pet_flat.ico` 恢复为透明 Q 版七档 ico（16/24/32/48/64/128/256），面板标题栏加 22×22 `pet_head_256.png` 小头像 | 头像单元格像素检测 149 种颜色、最亮 (245,213,197) |
| 4 启动即崩的括号 | `panel.py:50` `setWindowIcon` 调用少了右括号（压缩前遗留），补齐并加 `icon.isNull()` 守卫 | 源码可正常 import、打包后正常启动 |
| 5 睡觉蹲坐 | `sleep` 分支改为蹲坐打盹：`sy=0.72`、`sx=1.06`、头顶下沉、慢呼吸、头 18 秒歪一次 | 四帧对比 `assets\_matting\v299-sleep-sheet.png` |
| 6 动作不再换衣 | 非默认皮肤不套动作帧，靠程序化动作表演 | 汉服下立绘不变、默认皮肤仍用帧 |
| 7 右键菜单精简 | 托盘/右键删掉「语音说一句（Ctrl+Alt+V）」「今天天气」「说条科技新闻」「换天气城市…」，功能迁进「语音唤醒」「天气资讯」页 | 菜单项清点只剩常用项 |
| 8 硬件探测缓存 | `hwinfo.snapshot()` 打开面板被调 9 次、每次起 `nvidia-smi` 子进程 60~70ms；加 `_CREATE_NO_WINDOW` 与 90 秒缓存 | open_panel 3.9s → 1.84s |
| 9 子进程禁窗 | `hwinfo`、`secscan._run_ps()`、`suspect_processes()` 三处 `subprocess.run` 补 `creationflags=0x08000000` | 点安全体检不再闪黑框 |
| 10 麦克风检测缓存 | `voice_cmd.has_microphone()` 每次 0.4~0.5s、一次刷新查两次；加 `_MIC_TTL=300` 缓存 | 刷新耗时 0.84s → 0.12s |
| 11 Ollama 请求去重 | `local_llm._http_json` 一次打开被调 12 次；加 `_HTTP_CACHE` + `_HTTP_TTL=4.0` | 累计 0.68s 降到 2~3 次请求 |
| 12 主题不重复套 | `apply_theme()` 每次全量 `setStyleSheet`（130 控件、0.29s）；记住 `_theme_mode`，同主题直接返回 | 二次打开不再花这 0.29s |
| 13 性能实测 | 源码 open_panel 3.9s → 1.84s → 1.54s；`refresh()` 0.84s → 0.01s | 安装版冷启首开 1.89s、热开 0.31s；10 秒 CPU 0.36s（单核 3.6%）、内存 119MB |
| 版本 2.9.9 | `paths.APP_VERSION`、iss 五处、面板右上角同步 | `dist\WhaleGirlPet-Setup-2.9.9.exe`（86,684,968 字节） |

## v2.9.8（2026-11-25）

用户 8 条反馈，逐条落地：

| 项 | 改动 | 实测 |
|---|---|---|
| 1 番茄钟/提醒并入定时任务 | 侧栏 10 页 → 9 页：`_tab_remind` 改成合并页（番茄钟 + 日常提醒 + 定时任务 + 昨天使用情况），页名统一「定时任务」；`panel_v2.build_schedule` 供合并页复用，旧 `tab_schedule` 保留兼容 | 实拍 `assets\_matting\v297-panel-02-定时任务.png`，四块内容一屏放得下 |
| 2 本地大模型补模型仓库与建议 | 「本地大模型」组新增「模型仓库」列表：★ = 按本机配置推荐，列出名称、体积、已装/可下/仅仓库；双击或「下载选中的」直接走 `ctl.download_model` | 实拍 `v297-panel-06-自定义模型.png`：Qwen3-4B 已装、DeepSeek-1.5B 可下、★DeepSeek-7B 可下，推荐理由在下方 |
| 3 迁移后自动删旧文件 | `_migrate_store` 复制完逐项删旧；被数据库/缓存占用的写 `%APPDATA%\WhaleGirlPet\pending_cleanup.json`，`paths.cleanup_pending()` 在下次启动（数据库打开前）再清一次，清完删标记 | 代码路径完整；**没在用户真实数据上执行迁移**（避免动 11.8GB 模型目录与记忆库） |
| 4 去掉金币到账语音 | 删掉每分钟自动 +2 金币的 `coin_timer` 与「叮——又攒了一点金币」气泡/音效；金币只从打工结算来 | 自检 `has_coin_timer=False`；顺带堵住一小时白送 120 金币的通胀口子 |
| 5 做动作不再换衣服 | 动作帧只有默认女仆那一套：换装/萝莉形态下 `do_action` 不再套帧，保留当前立绘，靠 `_tick` 的摆臂/跳/转表演；默认皮肤仍用帧 | 自检：汉服下 `hanfu_base_unchanged=True`、默认装 `default_uses_sprite=True` |
| 6 睡觉要有变化 | `sleep` 分支从「透明度 0.85 站着不动」改成压暗到 0.70 + 慢呼吸（0.9Hz）+ 缓慢歪头打盹（±7°）；睡觉前先收掉正在播的动作 | 自检：`sleep_state=sleep`、`sleep_alpha=0.7`、`sleep_rot=2.9` |
| 7 设置拆成四个模块 | 「设置」页内改子标签：关于与更新 / 储存位置 / 语音唤醒 / 天气资讯 / 桌宠行为（v2.9.7 的桌宠行为保留成第五页）。关于页补「软件信息」：程序目录、数据目录、本地引擎、源码仓库；天气资讯加六类资讯按钮 + 文本框 | 五个子页实拍 `v298-prefs-0..4`；点「体育」实抓 6 条标题（田秉毅任国羽主教练 / 林丹谈羽毛球…） |
| 8 空的设置面板补上名字 | 设置页顶部加「设置」大标题；右键与托盘入口文案统一改成「设置…」（原「桌宠行为设置…」「主题（在设置里改）」） | 实拍 `v298-prefs-0-关于与更新.png`：顶部「设置」两字与五个子标签 |
| 版本 2.9.8 | `paths.APP_VERSION`、面板右上角、安装包文件名同步 | `dist\WhaleGirlPet-Setup-2.9.8.exe` |

## v2.9.7（2026-11-25）

本轮是用户 14 条改造清单的落地。基准来自用户原话，逐条对账见下表。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 每次更新及时进 git | 新增 `tools\release.ps1`：一条命令完成「版本号校验 → PyInstaller 打包 → Inno 编译安装包 → `git add -A`/commit/push origin main → 打印 CI 地址」；`-Bump` 可自动末位 +1，`-SkipBuild` 只推代码 | 本轮用它发布 v2.9.7（提交与 CI 结果见仓库 Releases） |
| 2 换装后「白眼」 | 逐张目检 8 套皮肤：`blackgown` / `blackgreen` / `blackred` 三套原图眼睛只有眼白、没有瞳孔；已重绘黑瞳（黑红款保留红瞳），原图备份在 `assets\_matting\v297\backup_*.png` | 对比图 `assets\_matting\v297\skins_all.png`（修后）与 `backup_blackred.png`（修前）；其余五套为闭眼设计，不是缺陷 |
| 3 llama → dafeiyu | 运行目录 20 个可执行入口早已是 `dafeiyu-*`；本轮续改：`runtime\llama-server.log`→`dafeiyu-server.log`、`runtime\_dl\llama-cpu.zip`→`dafeiyu-cpu.zip`、`test_offline_llama.py`→`test_offline_dafeiyu.py`（内部改为 `dafeiyu_cpp`）、`build.ps1` 注释、`README.md`/`PROJECT.md` 的引擎名 | **10 个 `llama-*.dll` 保留**：临时副本里改成 `dafeiyu-*.dll` 后 `dafeiyu-server.exe --version` 返回 `0xC0000135`（STATUS_DLL_NOT_FOUND），Windows 导入表写死名字，改了本地模型就起不来。`bench_ollama.py` 测的是 Ollama（另一款软件），未改名 |
| 4 桌宠行为集中到设置 | 设置页新增「桌宠行为」组：碎碎念、点击音效、始终置顶、跟随鼠标、换装、大小、形态、主题 八项一屏；音色仍在「音频库」 | 实拍 `assets\_matting\v297-panel-04-设置.png`：八项全在，无裁切 |
| 5 动作/投喂撤出面板 | 养成页删掉动作按钮与四格零食，只留「背包 / 零食商城 / 去打工」三个入口；动作由 `care_timer` 每 60 秒判断，12~20 分钟偶发一次「现在想做哪个？」两选项气泡（12 秒不选自己随机来一个），也能语音下指令 | 实拍 `v297-panel-00-养成.png`、`v297-win-ask.png`（挥挥手 / 跳个舞 + 「不理我过一会儿自己随便来一个」） |
| 6 背包 | `state.bag` + `buy()`/`eat()`/`add_to_bag()`；饿了吃、从背包拿、投喂时不饿就存进背包；背包实体窗口点一下即吃 | 逻辑自检 5 项全 PASS：买一份进背包、扣钱、从背包吃、空包不再凭空吃、旧 `feed` 接口兼容 |
| 7 零食商城 | 新增 `app\snacks.py`：主食/肉鱼/甜点/饮品/水果/高档/新品 七类，价格硬约束 4~45 金币；「联网补货」抓新零食并记 `shop_refreshed_at`；语音「零食商城/买零食」直接呼出；入口挂在打工页底部 | 实拍 `v297-win-shop.png`（金币 120、白米饭 12、面包 7、饭团 12、泡面 15）；自检 20 项物品价格全部落在 4~45。定价基准：打工单次 5~15 金币（学习听课 15、清理 14、家务 12），最贵零食约三四次打工 |
| 8 打工语音 + 10 秒 | 「去打工/打工」→ 随机 3 个活，气泡给选项，`timeout_ms=10_000`，不点就自己随机开工；状态栏里也有「去打工」 | 代码路径 + 状态栏实拍；10 秒超时未实跑（逻辑与动作气泡同一套） |
| 9 可显现状态栏 | 饥饿/口渴/心情差/金币低于 20% 任一命中 → 大气泡状态栏：四项数值 + 打工 / 投喂 / 喝水；40 秒不理自动收起，同一需求 10 分钟冷却 | 实拍 `v297-win-status.png`（饱食 30 触发，三按钮齐全） |
| 10 按本机配置装最搭模型 | `app\hardware.py`：读显卡/显存/内存/CPU 线程，`best()` 给出推荐与理由；面板「按本机配置重新推荐」 | 实拍 `v297-panel-06-自定义模型.png`：GTX 1060 6GB / 31.9GB / 8 线程 → 推荐 DeepSeek-R1-Distill-7B（Q4） |
| 11 换硬件提醒换模型 | 启动 30 秒查一次、之后每小时一次；`diff()` 比对显存/内存/线程，有变化就在气泡里说「硬件变了：显存 6.0→12.0，我重新配成 X」 | 自检：6→12GB 被识别为「显存(GB)：6.0 → 12.0」；无变化不报 |
| 12 换硬件自动适配 | 检测到变化即写 `llm_model_recommend`、更新 `llm_model_file`，没下载就提示去「自定义模型」下载 | 同上；未在真实换卡场景验证 |
| 13 做小软件 | 新增 `app\maker.py`：语音或聊天说「做个小软件/小工具/写个脚本」→ 本地模型出代码 → 抽 ```python 块 → 静态风险检查（shell=True、os.system、格式化、删注册表、关机、反弹连接等 10 类）→ 存到 数据目录\scripts → 用户点「运行」才执行，20 秒超时、输出截断 | 自检 PASS：`os.system('del /f C:\\*')` 被判「直接调 shell」；普通 `os.path.expanduser` 脚本放行；代码块抽取正常 |
| 14 主题迁进设置 | 主题下拉并入「设置 → 桌宠行为」，切换即 `set_theme` + `apply_theme`，托盘主题子菜单保留 | 设置页实拍可见「主题 深色」下拉 |
| 版本 2.9.7 | `paths.APP_VERSION`、面板右上角、安装包文件名同步 | `dist\WhaleGirlPet.exe` 与 `dist\WhaleGirlPet-Setup-2.9.7.exe` |

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
