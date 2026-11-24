# 架构说明

## 一句话

单进程 PySide6 应用：一个 `Controller` 管全局状态与定时器，一个 `PetWindow` 负责透明窗口与绘制，一个 `ControlPanel` 负责配置界面，重活（联网、TTS、下载、清理）都丢进 QThread，主线程只跑 UI 与 60ms 的动画循环。

## 分层

```
界面层  PetWindow（透明置顶窗口 / 气泡 / 右键菜单）
        ControlPanel（12 页侧边栏面板）· panel_v2（细分页面）
   ▲ Qt 信号 / 直接调用
控制层  Controller (app/main.py)
        托盘 · 快捷键 · 语音唤醒 · 自主行动 · 定时器 · 情绪 · 养成
   ▲
能力层（可独立替换，全部无 UI 依赖）
  ai / local_llm / websearch / knowledge / memory
  ambient（天气新闻）/ awareness（全屏）/ secscan（体检）
  cleanup / desktop_icons / sysvol / hwinfo
  tts / voice_profile / voice_cmd / audio_manager
  state（养成数值）/ tasks / scheduler / accounts
  updater（GitHub Release）/ theme / paths
```

约束：能力层不 import `main.py`，只吃参数；需要回调的地方用返回值或信号。这样任何能力都能在无 UI 环境下被测试脚本直接调用（`test_v29_voice.py`、`test_v292.py`、`test_v293.py` 就是这么跑的）。

## 桌宠绘制管线

1. `_update_pix()` 把「立绘 + 表情 + 缩放」合成到一张 `QPixmap`，窗口尺寸 = 立绘 + 2×`pad`。
2. `paintEvent()` 以底边为锚点绘制，再做 `translate`（bob/位移）+ `rotate`（摔倒翻滚）+ `scale`（弹跳挤压）。
3. 60ms 定时器推进动作状态机（idle → walk/run/tumble/sleep…），每次只重绘窗口矩形。

三个关键决策与代价：

| 决策 | 为什么 | 代价 |
|---|---|---|
| 不用 `setMask` 做窗口蒙版 | 蒙版是 1-bit 硬边，alpha 边缘会出现台阶状锯齿；而且按静态图算一次，人物翻译/旋转后超出部分直接被裁剪 | 窗口整块都是可点击区，透明处也能拖动 |
| 窗口外扩 `PAD_RATIO=0.18` | 给起跳（-64px）、旋转（宽 207→406）、弹跳留余量 | 窗口 606×931 比立绘 360×685 大一圈；过大的 pad（0.30）会让透明区变成误拖区 |
| 底边锚定而不是中心锚定 | 换皮肤高度不同时，脚底始终贴地，不会上下漂 | 旋转时支点在脚底，摔倒动作看起来是「以脚为轴倒下」 |

## 线程模型

| 线程 | 用途 | 注意 |
|---|---|---|
| 主线程 | UI、动画、配置读写 | 任何 `sleep` 或同步网络请求都会卡住动画 |
| `AIChatWorker` | 流式对话 | 逐句 `chunk` 信号回主线程 |
| `TTS` | 合成与播放（内部队列 + 优先级） | 喂食/拍拍=2 > 对话=1 > 闲聊=0，高优先级可抢断 |
| `UpdateWorker` / `DownloadWorker` | 版本检查 / 分块下载 | 下载带 Content-Length 进度与 SHA256 校验 |
| `SecScanWorker` | 安全体检 | 逐项 `item` 信号，可中途取消 |
| `CleanWorker` | 垃圾扫描与清理 | 只动临时目录 |

退出时 `quit_app()` 逐个 `stop()` 并 `wait(2000)`，仍阻塞的线程 `terminate()` 兜底——网络请求卡在 socket 时程序必须能退掉。

## 语音链路

```
文本 → persona.dialectize（方言改写）→ tts.say()
      → voice_profile.pitch_for()（基频反查 pitch，覆盖人设 pitch）
      → Edge TTS（edge-tts 包）→ mp3 缓存 → QMediaPlayer 播放（音频优先级队列）
```

音色提炼的实测结论（为什么要反查而不是直填 Hz）：

- Edge TTS 的 `pitch` 只接受 `+NHz` 写法，`+7st`、`+52%` 会直接抛 `ValueError: Invalid pitch`。
- 名义值与实际基频不是线性等号：Xiaoxiao 基准 238.8Hz，名义 0/20/40/60/90 → 实测 238.8/271.2/301.9/333.3/355.6，≥90 饱和；Xiaoyi 基准 296.3Hz，名义 90 反而回落到 405.1。
- 所以 `voice_profile` 里存的是「实测曲线」，`pitch_for()` 用分段反查得到名义值，误差控制在 ±5Hz。

## 联网更新

```
GET https://api.github.com/repos/{repo}/releases/latest
→ 挑资产：*Setup*.exe 优先，其次 *.exe；*.sha256 作为校验源
→ DownloadWorker 分块写入 .part，校验通过才 os.replace
→ 调安装器静默安装并退出
```

同版本 `newer=False` 不打扰；失败状态区分 `offline / http_4xx / parse`，只记日志不弹窗（开机检查是静默的）。

## 数据位置

```
%APPDATA%\WhaleGirlPet\
├── accounts\<档案>\config.json     # 所有可调参数
├── accounts\<档案>\voices\         # 音效与 TTS 缓存
├── memory\  kb\                    # 记忆与知识
└── downloads\                      # 更新包与 .part
```

配置读取一律 `config.get(key, DEFAULT)`，缺失键自动回落，不因旧配置崩溃。

## 测试

仓库根目录的自检脚本都是「真跑一遍」而不是断言源码字符串：

| 脚本 | 覆盖 |
|---|---|
| `test_v29_voice.py` | 音色映射、Controller 配置、真合成回采、关档恢复 |
| `test_v292.py` | 主题三档、托盘菜单、唤醒词、活动余量、形态静默 |
| `test_v293.py` | 托盘右键不再隐藏、静音模式、切换动作静默、面板侧边栏 |

```powershell
.\.venv\Scripts\python.exe test_v293.py
```
