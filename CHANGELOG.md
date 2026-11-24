# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

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

### 做到一半 / 待办

- 各皮肤立绘的「脸不一致」需要统一重绘（生成批次不同），本轮未动素材。
- 果冻过渡动画（形态/换装/动作切换的插值回弹）仍未实现。
- Release v2.9.3 的四个产物已在本地 `dist/` 生成，但资产上传受 github.com 域名间歇阻断影响，尚未挂到 Release 页。

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
