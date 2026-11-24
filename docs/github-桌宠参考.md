# GitHub 桌宠项目参考（学习笔记）

检索时间：2026-11-24｜数据来源：GitHub API（登录账号 cnbprd），star / license / 更新日期均为接口返回
本文件只做**设计与工程思路**的参考，不搬运代码。抄代码前先看下面「许可证」一栏。

## 一、候选清单（按 star 排序，只留有参考价值的）

| 仓库 | 语言 | Star | License | 最后更新 | 能学什么 |
|---|---|---|---|---|---|
| ChaozhongLiu/DyberPet | Python/PySide6 | 1030 | GPL-3.0 | 2026-10-16 | **同技术栈**：动作配置化、动作组概率、昼夜系统、气泡、语音优先级、附件组件 |
| liupig/xiaokeai | Python | 466 | Apache-2.0 | 2026-11-23 | 3D VRM/MMD 桌宠 + lip-sync（Electron + three.js，非 PySide6） |
| mille-okws/pestinha | Python | 462 | GPL-3.0 | 2026-11-10 | 情感/性格演化（脉冲神经网络），全本地 |
| Hanzoe/Pet-GPT | Python/PyQt | 434 | GPL-3.0 | 2025-03-21 | 主动找聊天的调度策略（老牌，代码旧） |
| Wunsch2048/codex-bailong-desktop-pet | Python/PySide6 | 376 | 未标注 | 2026-11-20 | 同栈 + token 用量面板 |
| jihe520/Agentic-Desktop-Pet | Python/Godot4 | 342 | 未标注 | 2026-01-10 | 3D 走 Godot 的现实路线 |
| DD-MASTERT/AI-Girlfriend-Desktop-Pet | Python | 243 | MIT | 2024-08-17 | **音色克隆接入**：GPT-SoVITS / CosyVoice + edge-tts 三路并存 |
| pixelomer/Shijima-Qt | C++/Qt6 | 202 | GPL-3.0 | 2026-04-29 | Shimeji 行为引擎（窗口坐标、攀爬、投掷、落地） |
| kiyotakali/Miru | Python | 205 | Apache-2.0 | 2026-10-13 | Live2D + 长期记忆 |
| CluelessCatBurger/wl_shimeji | C | 215 | GPL-2.0 | 2026-08-13 | Wayland 层壳透明窗口实现（Linux） |
| 11ehu/DesktopPetGenerator-win | — | 18 | 未标注 | 2026-09-19 | 照片转透明桌宠的扣图链路 |

结论：**真正能直接对着抄结构的是 DyberPet**，其它多为 Electron/Live2D/Godot 路线。

## 二、DyberPet 的动作系统（已读 docs/art_dev.md 原文，非猜测）

### 1. 帧的组织方式
- 一个动作 = 一组同前缀 PNG：`stand_0.png, stand_1.png, ...` 放 `action/` 下
- 动作在 `act_conf.json` 里声明：

| 字段 | 含义 |
|---|---|
| `images` | 帧文件前缀 |
| `act_num` | 循环播放次数（**省内存**，只载入一个循环却播 N 次） |
| `need_move` / `direction` / `frame_move` | 该动作是否驱动窗口移动、方向、每帧位移 |
| `frame_refresh` | 单帧时长（秒），文档强烈建议所有动作用同一值 |
| `anchor` | 相对画布底边中心的偏移，用来对齐"底部中心"，避免切动作时整体闪现 |

### 2. 动作组（random_act）
```json
{"name": "睡觉", "act_list": ["fall_asleep", "sleep"], "act_prob": 0.05, "act_type": [0, 0]}
```
`act_type` 是 `[饱食度等级, 好感度解锁等级]`，再按矩阵放大/缩小概率：

| 动作定义状态 \ 当前饱食度 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|
| 3（hp>80） | a | a/4 | a/16 | 0 |
| 2（hp>50） | a/4 | a | a/4 | 0 |
| 1（hp>0） | 0 | 0 | a | 0 |
| 0（饿昏） | 0 | 0 | 0 | a |

这就是"越饿越不想动、饿昏只睡觉"的实现方式，等比缩放而不是写死。

### 3. 昼夜作息（day_night）
1. 给夜间动画打 `"phase": "night"` → 白天池权重强制 0
2. `pet_conf.json` 里加 `day_night { sleep, night_random_act, to_night, to_day, disturbed, night_random_prob }`
3. 缺过渡动画就硬切，零额外素材可接入；时间边界是用户全局设置（默认 08:00 醒 / 23:00 睡）

### 4. 语音优先级
`note.json` 每类通知带 `sound_priority`（系统 0 / 专注 1 / 喂食 2，数字越大越高）。
规则：高优先级语音可以**打断**正在播的低优先级语音。随机语音 `random_1..N` 优先级 0。

### 5. 气泡触发类型（9 类）
`fv_lvlup`（好感升级）、`fv_drop`、`hp_low`（hp<80 随机）、`hp_zero`、`feed_done`、`feed_required`、`pat_focus`（专注时点它）、`pat_frequent`（**1 秒内点 ≥7 次**）、`pat_random_N`（点击 40% 概率）。
文字里 `USERTAG` / `ITEMNAME` 会被替换成用户昵称与物品名。

### 6. 组件（accessory_act）与可穿戴
- 组件是独立图层：`follow_mouse`（跟随鼠标）、`anchor`（相对底边中心或指针的偏移）、`above_main`（在主图上下）
- `acc_type: "equip"` + 与物品同名 → 可穿戴装饰（翅膀/披风），下次启动自动恢复

## 三、对照我们 WhaleGirlPet 的差距

| 我们现在 | DyberPet 的做法 | 我们的短板 |
|---|---|---|
| 程序化动画：1 张 PNG + 分肢位移/缩放，19 状态硬编码在 `_tick` | 配置化动作帧 + JSON 声明 | 加动作要改代码，不能靠改 JSON 扩展 |
| 表情 10 张、动作 7 张，切换靠 `set_expression` + 2600ms 回弹 | 动作组带权重与状态门槛 | 随机动作没有"饿了少动"的权重逻辑 |
| TTS 队列（v2.5 修过断流） | 语音优先级抢断 | 没有优先级，随机语音可能盖掉喂食反馈 |
| 22 点休息提醒 | 完整昼夜动画池 + 入睡/起床过渡 | 到点只是提醒，没有夜间动画切换 |
| 有气泡聊天 UI | 9 类触发（含"点太快"、40% 随机台词） | 触发类型少 |
| 无 | anchor 底边中心对齐 | 换皮肤/换形态时脚下基准可能漂 |

## 四、优先级建议（按性价比）

1. **语音优先级抢断**（半小时）：给 `tts.py` 队列加 `priority` 字段，喂食/拍拍 > 闲聊。
2. **动作组权重表**（1 小时）：把 `_tick` 里挑状态的逻辑换成 JSON 权重表，实现"饿昏只睡"。
3. **昼夜动画池**（1.5 小时）：已有 22 点提醒，顺势加 `phase=night` 与入睡过渡。
4. **气泡触发补全**（1.5 小时）：加 `pat_frequent`（1 秒 7 次）、`pat_random`（40%）、`hp_low`。
5. **anchor 对齐**（半小时）：给每套 skin 定一个底边中心，切皮肤时按 anchor 校正。
6. 附件/可穿戴（跟随鼠标的特效、翅膀）：2–3 天，收益最低，最后做。

## 五、许可证（教训：别直接拷代码）

| 类型 | 仓库 | 能做什么 |
|---|---|---|
| GPL-3.0 | DyberPet、Shijima-Qt、Pet-GPT、pestinha、shimeji、wl_shimeji(GPL-2.0) | **可以学思路、写自己的实现；直接拷代码并分发，整个程序必须开源** |
| Apache-2.0 | xiaokeai、Miru | 可用，需保留 NOTICE 与专利条款 |
| MIT | AI-Girlfriend-Desktop-Pet、bongo-cat-next | 最宽松，保留版权声明即可 |
| 未标注 | codex-bailong、Agentic-Desktop-Pet、DesktopPetGenerator-win | 默认保留所有权利，只能读不能抄 |

我们的 exe 是自用/分发到手就走的形态，**只用 DyberPet 的设计思路，不复制其源码**，避免 GPL 传染。

---

# 附：大肥鱼/鲸鱼娘专题（2026-11-24 第二轮检索）

搜索词：`大肥鱼`、`deepseek desktop pet`、`whale desktop pet`、`鲸鱼娘`。以下都是接口真实返回。

| 仓库 | Star | 语言/框架 | License | 定位 |
|---|---|---|---|---|
| whyever77/dafeiyu-astrbot | 930 | Python | MIT | 大肥鱼 QQ 机器人全家桶（AstrBot+NapCat+DeepSeek），会看会听会说话、有记忆、主动找你 |
| TreapGoGo/deepseek-whale-girl | 868 | HTML | MIT | **社区鲸鱼娘二创资源库**：角色参考图、生成提示词、社区作品 |
| qianyiai/kurocat | 523 | Tauri+Rust | MIT | 打字猫桌宠 + OBS 透明源，内置 6 款猫含"鲸鱼娘大肥鱼"，带输密码防偷窥 |
| Bai-Cute/big-blue-fish-desktop-pet | 392 | C#/WPF | Apache-2.0 | **蓝色大肥鱼 Windows 桌宠**：4B 本地模型 + OCR 读屏 + 天气/新闻 + 106 段动画 |
| Sutera-Diffusus/dsh-whale-musume | 224 | JS | MIT | 元气鲸鱼娘：45 项成就、3 个小游戏、跨端存档、按工具类型切工作姿态 |
| louke6572/dsh-Dfy | 104 | JS | 未标注 | 余额挂件 + 106 段透明桌宠 + QQ 消息卡 + B站 + 脱敏记忆 |
| Andersen216/dsh-whale-girl-live2d | 96 | JS | MIT | Live2D 鲸鱼娘，跟随 agent 真实状态换表情动作 |
| linggan121/lingling-desktop-pet | 96 | Python/tkinter | MIT | 桌宠干真实文件活：拖文件进来转图片/拆 PDF/提文本/打包 |
| Jestions-dev/BlueFatFish | 506 | JS | MIT | 蓝色大肥鱼浏览器新标签页（纯本地） |

## 值得抄的四个点（big-blue-fish README 原文核实）

1. **动作素材金矿**：它的 106 段透明 WebM 动画来自 `PC2005-cloud/dsh-pet`（MIT，1280×720/60fps，含 720p 兼容素材）。我们现在只有 10 张表情 + 7 张动作图靠程序化变形，这是最大的差距来源。
2. **读屏陪伴**：Windows 用系统自带 `Windows.Media.Ocr` 识别前台窗口文字（按标题栏/侧边栏/正文分区整理），交给本地 4B 模型说一句话；**读屏内容只在本机、不上传不落盘**，且能一键关。
3. **生活化权重**：动作"每种都有出现权重，结合当前时间、日期、季节、饭点、操作实时计算"；23 点犯困、8 点醒，三餐前后一小时多上美食动作，春节写福字、中秋赏月；`_act_prob` 按节日临近递增。
4. **体贴的边界行为**：笔记本拔电自动暂停 AI 并卸载模型、插回恢复；外部程序全屏时自动躲起来；启动行礼、关闭道别。

## 我们的对照结论

| 维度 | 我们 WhaleGirlPet | big-blue-fish |
|---|---|---|
| 动画 | 10 表情 + 7 动作图，程序化 19 状态 | 106 段 60fps 透明动画 |
| 理解屏幕 | 无 | OCR 读前台窗口 |
| 联网内容 | 有知识库/搜索 | 天气(Open-Meteo) + IT之家 RSS |
| 本地模型 | 5 个 gguf + dafeiyu/ollama 双引擎 | Qwen3.5-4B + llama.cpp Vulkan |
| 语音 | 8 方言人格 + 160 条人格音效 + 优先级 | 无 TTS（只有气泡） |
| 桌面行为 | 满屏跑/撞图标/多皮肤/玻璃边界 | 离电暂停/全屏躲/礼节动作 |

我们**明显强于它**的是语音人格体系与桌面互动玩法；**明显弱于它**的是动画素材量、屏幕感知、生活化日程。

许可提醒：big-blue-fish 是 Apache-2.0（设计可借鉴、需保留 NOTICE）；`dsh-pet` 是 MIT（素材可用但要署名）；`dsh-Dfy` 未标注许可（只能读）。

## 落地实测（2026-11-24，v2.9.0）

| 结论 | 证据 |
|---|---|
| Open-Meteo 在本机**完全不可用** | `api.open-meteo.com` SSL 握手超时（`_ssl.c:1064: The handshake operation timed out`），而 `geocoding-api.open-meteo.com` 正常 → 同厂不同域名，网络策略不一致 |
| 可用天气源 | `t.weather.itboy.net`（中国天气网数据中转，需 city code，返回实况+今日高低温+空气质量）、`wttr.in`（城市名直查，境外，偶发读超时）、`d1.weather.com.cn/sk_2d/{code}.html`（国内 CDN，只有实况） |
| 最终级联顺序 | itboy → wttr → open-meteo。郑州实测 `12.4℃ 晴 4~15℃ 空气优`（wttr 同刻报 8℃，两源差 4℃ 以上，国内场景以中国天气网为准） |
| 全屏判定必须用 DWM 可见边框 | `GetWindowRect` 含不可见阴影，Chrome 最大化为 1936×1048；`DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS=9)` 后才是真实可见区域 |
| 覆盖率阈值 | 0.995：1910×1074 不计入、1911×1075 计入；1920×1032（最大化含任务栏）不计入 |
| 前台焦点抢不过来 | 测试机被一个置顶 Flutter 窗口长期占用前台，`SetForegroundWindow` 无效，所以"真实全屏"只能靠比较函数单测 + 最大化窗口反例来覆盖 |

