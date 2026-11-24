# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

## v2.9.3（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 修：右键托盘图标把桌宠藏了 | `tray.activated` 原先不分按键原因一律 `toggle_visibility`，右键弹菜单前先触发了一次隐藏；改为只有左键 `Trigger` 才切换 | 直接调用 `_on_tray_activated(Context)` 后 `pet.isVisible()==True`；`Trigger` 则变 False |
| 静音模式 | `_speak()` 增加 `mute_idle`：`priority=0`（闲聊、天气、新闻、自主台词）只出气泡不出声，对话回复与投喂/拍拍照常发声 | priority0 调用 TTS 次数 0；priority2 为 1；关掉静音后 priority0 恢复发声 |
| 切换类动作静默 | `SILENT_ACTIONS={"change"}`，换装动作不再播「等我换件衣服……」 | `on_action("change")` 触发 TTS 次数 0 |
| 面板改 macOS 风格 | 顶部横排标签换成左侧 `QListWidget` 侧边栏（138px）+ 右侧 `QStackedWidget`；侧栏胶囊选中态、顶部标题栏与版本号 | 侧栏 12 项、宽 138px、点选能切页；浅色与深色两套截图生成 |
| 开源文档 | 重写 README、新增 LICENSE（MIT + 角色二创声明）、本日志、`docs/ARCHITECTURE.md`、`docs/FEATURES.md`、`requirements.txt` | — |
| 版本号 | `paths.py`、`installer/whale_pet.iss` 四处升到 2.9.3 | — |

### 做到一半 / 待办

- 各皮肤立绘的「脸不一致」需要统一重绘（生成批次不同），本轮未动素材。
- 果冻过渡动画（形态/换装/动作切换的插值回弹）仍未实现。

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
