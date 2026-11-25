# 模型三档分工方案（v3.0.14 评估稿）

按你说的「一个大脑中枢、一个多模态快速反应、一个专属工具人」拆，先把**手上有什么牌**摊清楚，再给分工和调度规则。本文是评估稿，未改代码。

## 一、牌面（本机实测，2026-11-25）

| 资源 | 实测 | 对分工的意义 |
|---|---|---|
| `runtime\models` 4 个 gguf | deepseek-coder-6.7b-instruct 3650.5MB / gemma4-e2b-it 3269.1MB / qwen35-4b-Q4_K_M 2525.9MB / Qwen3-4B-Q4_K_M 2381.6MB | 都是**纯文本**权重，没有 vision 权重 |
| `F:\WhaleGirlPetApp\models` | gemma4-e2b-latest 3269.1MB、qwen3.5-4b 2525.9MB（与上表同权重，双份约 5.7GB） | 与分工无关，是磁盘冗余 |
| 推理引擎 | `dafeiyu-server.exe` 单进程，**一次只加载一个模型**；换模型 = 重启服务（秒级到十秒级） | 「三个模型同时常驻」在这套引擎上做不到 |
| Ollama | 本机 `llama-server.exe` 缺失，`ollama_runtime_ok()` 为 False | 走 Ollama 的多模态/模型热切换当前不可用 |
| 云端 | `ai_profiles` 只有 1 个空「默认」档，`api_key` 走 `read_zhipu_key()` 兜底 | 多模态只能先接云端一档 |

**结论 1**：所谓"三档"，在本机只能是**一个常驻模型 + 三套调用参数档位 + 一次按需热切换**，不是三个模型常驻。三个 4B 同时常驻约 7–9GB 内存 + 三份 KV cache，一台同时跑桌宠渲染的机器扛不住。

## 二、三档职责

| 档位 | 职责 | 选型（本机） | 参数 | 常驻 |
|---|---|---|---|---|
| 大脑中枢 Brain | 人格对话、记忆/知识库注入、情绪反应、长上下文闲聊 | Qwen3-4B-Q4_K_M（2381.6MB，四者最小、中文对话稳、内存压力最低） | temp 0.8 / max_tokens 260 / 最近 6 轮 / `/no_think` | 是 |
| 多模态快反 Fast | 看图、截图、短问快答，首要指标是首字延迟 | 本地无 vision 权重 → **走云端**（新增一个 vision 档 profile）；本地退化为"文字快反" | temp 0.5 / max_tokens 160 / 单轮 | 否 |
| 专属工具人 Tool | 只做指令解析，只输出 JSON（`set_reminder/check_weather/open_file/chat`） | qwen35-4b-Q4_K_M（2525.9MB，比 Brain 略大但指令遵循更稳）或直接复用 Brain | temp 0.1 / max_tokens 180 / `fmt="json"` | 否，按需 |

**为什么 Tool 要单独一个模型而不是纯靠 prompt**：JSON 合法性对 4B 模型是硬门槛，`_router_messages` 已用强约束 prompt + `fmt="json"`，但同一个模型既写长文又出 JSON，温度冲突（0.8 vs 0.1）只能靠每次改参数解决；独立小档位把"说人话"和"出结构"彻底分开，非法 JSON 率能明显压低。

## 三、输入分流（沿用现有代码，不新增入口）

| 输入特征 | 走向 | 现有实现 |
|---|---|---|
| `skills.looks_like_command()` 命中 | Tool 档 | `main.send_chat` → `LocalChatWorker(fmt="json")` → `_on_skill_route` |
| 带图片/截图附件 | Fast 档（云端 vision） | 目前 `send_chat` 只把附件路径注入文字，**没有真正传图**，这是缺口 |
| 其余 | Brain 档 | `_chat_plain` → `_build_messages` |

## 四、调度规则（建议落地形态）

1. **一个服务，三套参数**：Brain / Tool 共用同一个 `ServerManager`，用 temperature、max_tokens、system prompt 区分档位；只有 Tool 指定模型与 Brain 不同时才触发重启。
2. **热切换只在空闲时做**：连续 30s 无聊天请求才换模型，避免用户正聊着突然卡 10s；切换期间状态栏写"正在换装模型"。
3. **LRU 只留一份**：`ServerManager` 记 `active_model`，来回切超过 2 次就固定用 Brain 的模型跑 Tool 档（牺牲一点 JSON 率换不掉线）。
4. **降级链**：Brain 本地失败 → 云端默认档（`_on_local_failed` 已有）；Tool JSON 非法 → 立刻退回 `_chat_plain`（`_on_skill_route` 已有）；Fast 无 vision → 老实说"这张图我看不了"而不是瞎编。
5. **资源闸**：可用物理内存 < 800MB 时只允许 Brain，Tool 直接用 Brain 模型跑低温度参数。

## 五、下一版落地的三步

1. `config` 增 `model_roles = {"brain": "Qwen3-4B-Q4_K_M.gguf", "tool": "qwen35-4b-Q4_K_M.gguf", "fast_profile": "快反"}`；`ServerManager` 支持按角色取模型并写 `active_model`。
2. 控制面板「模型」页加三个下拉（大脑 / 快反 / 工具人）+ 一句"空闲 30 秒才换模型"的说明；改完写配置。
3. `ai_profiles` 增一个 vision 档，`_chat_cloud` 支持传档名而不是只能读 `active_profile`；`send_chat` 的图片附件真正以 base64 传上去。

## 六、怎么验证（下一版动手时的验收口径）

| 指标 | 口径 |
|---|---|
| Tool JSON 合法率 | 20 条指令用例（设提醒/查天气/开文件/闲聊各 5 条）统计 `sk.handle` 一次解析成功率 |
| Brain 口语度 | 20 轮闲聊里"2–4 句、不分点"的占比 |
| Fast 首字延迟 | 图片问答从发送到首字上屏 < 1.2s（云端） |
| 内存峰值 | 三档轮转 5 分钟后进程 RSS 峰值，需 < 4GB |
