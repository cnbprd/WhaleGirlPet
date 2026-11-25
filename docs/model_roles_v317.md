# v3.0.17 三档模型分工落地说明

本机 `runtime\models` 里 4 份 gguf 的**实测体积**（`os.path.getsize`，v3.0.17 现场测）：

| 文件 | 体积 | 角色定位 | 是否默认启用 |
| :-- | --: | :-- | :-- |
| `qwen35-4b-Q4_K_M.gguf` | 2525.9 MB | 大脑 / 中枢：意图理解、结构化输出、兜底 | ✅ `brain` |
| `deepseek-coder-6.7b-instruct.gguf` | 3650.5 MB | 专属工具人：代码、语法、工程词 | ✅ `tool` |
| `gemma4-e2b-it.gguf` | 3269.1 MB | 名义上的多模态快反 | ❌ `fast` 留空（原因见 §4） |
| `Qwen3-4B-Q4_K_M.gguf` | 2381.6 MB | 备胎（大脑起不来时的候选） | 候选降级 |

## 1 分工怎么落地

改在引擎层，不改业务流程：

| 位置 | 改动 |
| :-- | :-- |
`app/local_llm.py` `ServerManager` | 新增 `role_model(role)`：从 `config["model_roles"]` 取文件名 → `resolve_model` 解析成真实路径；新增 `ensure_role(role)`：当前已加载的就是目标模型且 `health()` 正常 → 直接返回；否则加锁停掉再起
`app/local_llm.py` `ensure_role` 的内存闸 | 可用内存 < 目标模型体积 × 1.15 → **不切**，写 `fallback_note`，照常用当前模型回答（宁慢不死）
`app/local_llm.py` `LocalChatWorker` | 新增 `role=""` 参数，`run()` 里先 `ensure_role`，切不动就继续用现有模型
`app/main.py` `Controller._chat_plain` | 按 `_looks_like_code(text)` 选 `tool` / `brain`；走 `tool` 前先出气泡提示（见 §2）
`app/main.py` 技能路由 | 固定 `role="tool"`（路由器本来就是结构化 JSON 输出）
`app/main.py` `DEFAULTS` | 新增 `model_roles` 默认值，老 `config.json` 读不到时 `role_model` 内部还有一层兜底

配置项（`F:\WhaleGirlPetApp\config.json`）：

```json
"model_roles": {
  "brain": "qwen35-4b-Q4_K_M.gguf",
  "tool":  "deepseek-coder-6.7b-instruct.gguf",
  "fast":  ""
}
```

留空 = 该档不参与调度，绝不强行换模型（`tools/test_model_roles.py` 里专门测了这条）。

## 2 实测代价（真机，`tools/live_roles.py`）

引擎 `runtime\dafeiyu\dafeiyu-server.exe`，ctx 4096，串行 dispatch，同一句话"只回复两个字：在的"：

| 动作 | 切换耗时 | 该模型单轮响应 |
| :-- | --: | --: |
| 起 `brain`（4B） | 5.8 s | 1.3 s |
| `brain` → `tool`（6.7B） | **23.6 s** | 6.5 s |
| `tool` → `brain` | 6.9 s | 1.6 s |

单进程单模型（`-np 1`），换角色 = 重启引擎，所以"三个模型同时常驻"不存在可行性（三份权重合计 9.2 GB，加 ctx 与 KV 只会更高）。

因此 `_looks_like_code` **按这组数字收紧过一次**：去掉「异常」「bug」「脚本」这类日常也常说的词，只留「报错 / traceback / 这段代码 / 代码 / 函数 / 编译 / 正则 / 写个脚本 / 重构 / 单元测试 / pandas / numpy / SQL」。误判一次要付 23.6 s + 6.5 s。

不想要这个代价，把 `tool` 改成 `""` 即可，全部走 4B。

## 3 气泡提示

走 `tool` 档时先出气泡："我要把专写代码的那个脑子叫醒，得等十几二十秒…"（6000 ms）。
不这么做，用户会以为程序卡死 —— 23.6 s 的静默不可接受。

## 4 关于"Gemma 4 E2B = 多模态快反部队"这件事，有个硬事实

- `runtime\models` 下 **`*mmproj*` 文件数 = 0**。多模态（看图 / 听音频）依赖 mmproj 视觉投影权重，本机没有 → 这份 `gemma4-e2b-it.gguf` 只能跑纯文本。
- 它的体积 3269.1 MB，比大脑 `qwen35-4b` 的 2525.9 MB **还大 743 MB**；同样是 4B 量级，起得不会更快。
- 结论：本机没有"能看图的本地模型"这一档。`fast` 因此默认留空。真要"看截图"，只能走云端多模态（v3.0.15 的 API 接入已经支持 OpenAI/Anthropic/Gemini 三协议，其中两家有多模态输入，但当前 `ChatWorker` 只发文本 messages，没做图片编码）。
- 如果有人拿 `gemma4-e2b-it.gguf` + 对应的 `mmproj-*.gguf` 补齐，把 `fast` 填上即可，引擎侧 `ensure_role` 不用再改。

## 5 包体与启动（同一版实测，`tools/measure_boot.py`）

| 指标 | v3.0.16 基线（安装目录 exe） | v3.0.17 新构建 | 变化 |
| :-- | --: | --: | --: |
| exe 体积（onefile） | 69.4 MB | **64.0 MB** | −5.4 MB（−7.8%） |
| 引导进程首现 | 1.08 s | 1.01 s | ≈持平 |
| 解包 + 主进程起来 | 4.26 s | **2.10 s** | **−2.16 s** |
| 常驻 RSS（双进程合计） | 171 MB | 175 MB | +4 MB（噪声范围内） |

瘦身动作（`WhaleGirlPet.spec` / `build.ps1`）：

1. `hiddenimports` 删掉 `tkinter`（v3.0.1 已删除原生 Tk Splash，app 下 0 次 import；留着会把 tcl90/tk90 整套数据拖进包）
2. 删掉 `collect_all('tabulate')`（app 下 0 次 import，纯把测试与 metadata 塞进包）
3. `excludes` 加 `tkinter / numpy / pandas / scipy / matplotlib / PIL / pytest / IPython / notebook`（venv 里装了但代码 0 次使用）
4. `optimize=2`（去 docstring；全项目 0 处引用 `__doc__`）

启动仍有 2.1 s 花在 onefile 解包上（先把 64 MB 解到 `%TEMP%` 再执行）。改成 onedir 可以省掉这一段，并把常驻 RSS 再降十几 MB（少一个引导进程），但要同步改 `installer\whale_pet.iss` 的文件清单、portable zip 和更新器逻辑 —— 属于发布形态变更，本版没有擅自动，留给下一版决定。

## 6 关于"引擎/渲染分离、headless"那条外部建议

`vlln/whale-girl` 确实存在（npm `whale-girl` 0.2.4 / `whale-girl-desktop` 0.1.0，MIT，Node 引擎 + Tauri 壳，`--headless` 只跑心跳与 SSE，默认连本地 DSH 3080）。但它是 **DSH Web GUI 的插件/桌面壳**，与本项目（Python + PySide6 独立进程）不是同一家族，"WhaleGirlPet 项目家族"的说法不成立。

真正可借的是架构思想，而我们的结构其实已经是那个形状：

| 对方 | 我们 |
| :-- | :-- |
Node 引擎（状态轮询 / 事件消费） | `app/main.py` 的 `Controller` + QTimer 心跳 + `scheduler` |
Tauri 渲染壳 | `app/pet_window.py`（`QWidget` 透明窗口，只负责画和动画） |
SSE 事件 | Qt Signal / `do_action` / `anim_engine` 事件点 |
`--headless` | 对桌宠无意义（它本身就是给眼睛看的） |

所以本版没有再照搬其技术栈，只在"引擎不依赖渲染层"这一条上继续保持（`local_llm` / `memory_tiers` / `skeletal` 都不 import `pet_window`）。
