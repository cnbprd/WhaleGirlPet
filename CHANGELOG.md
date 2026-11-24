# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

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
