# 2D→3D 素材/协议层 v1

日期：2026-11-27
实现提交：`12e1cb4`（资产图集）、本次提交（协议字段与两侧实现）

## 设计原则

- **旧 3D 不崩**：新增 `card` / `card_ttl_ms` 只是附加字段；不认识这两个字段的旧渲染器照常只读 `emotion`。
- **新 3D 可渐进**：渲染器先接收、记录；等 sprite 层接入后再真正画卡面。
- **协议不带文件路径**：`card` 必须是 `assets/2d_bridge` 目录里 `manifest.json` 的 id，渲染器按白名单取 rect，避免任意文件读取。
- **仲裁仍在 Python**：优先级、TTL、用户/LLM/自动状态仍由 `emotion_bridge.py` 决定；3D 只做本地消费。

## 传输

- UDP，`127.0.0.1:47832`（可用 `WHALE3D_EMOTION_PORT` 覆盖）。
- 单包上限 `512 B`；当前典型卡面包约 `96 B`。
- 发送端：`app/asset_bridge.py` 或 `app/emotion_bridge.py`。
- 接收端：`3d/emotion_bus.cpp` 的 `EmotionBus::poll`。

## v1 字段

| 字段 | 类型 | 必填 | 说明 |
| :--- | :--- | :---: | :--- |
| `emotion` | string | 是 | 兼容旧渲染器：`happy` / `angry` / `curious` / `shy` / `tired` / `neutral` 等 |
| `intensity` | 0..1 | 否 | 默认 1；卡面动作可给 0.7 |
| `source` | string | 否 | `P_USER` / `P_LLM` / `P_AUTO` / `P_2D` |
| `curve` | object | 否 | `{"attack_ms":180,"release_ms":420}`；3D 也接受顶层 `attack_ms` / `release_ms` |
| `gaze` | object | 否 | `{"x":..,"y":..,"weight":..}`，沿用 v3.2 |
| `lean` | object | 否 | `{"x":..,"y":..,"weight":..}`，沿用 v3.2 |
| `card` | string | 否 | 白名单 id，例如 `expression/happy`、`action/wave` |
| `card_ttl_ms` | int | 否 | `200..10000`，缺省 0（表示仅本次包，不常驻） |

示例：

```json
{"emotion":"happy","intensity":0.7,"source":"P_2D",
 "card":"expression/happy","card_ttl_ms":1800}
```

动作卡示例：

```json
{"emotion":"neutral","intensity":0.7,"source":"P_2D",
 "card":"action/wave","card_ttl_ms":2600}
```

## 卡面 id

来自 `assets/2d_bridge` 目录的 `manifest.json`，共 **17** 个：

- `expression/`：`idle`、`happy`、`eat`、`walk`、`sleep`、`sleepy`、`shy`、`angry`、`curious`、`pat`
- `action/`：`wave`、`dance`、`type`、`balloon`、`fireworks`、`lion`、`change`

渲染器只接受这些 id；未知 id 直接忽略，不打开文件。

## 仲裁与显示

- Python 的 `EmotionBridge` 在情绪变化时自动带上对应卡面：
  `happy→expression/happy`、`angry→expression/angry`、`curious→expression/curious`、`shy→expression/shy`、`tired→expression/sleepy`、`neutral→expression/idle`。
- 动作卡由 `AssetBridge.action(name)` 单独发送，默认 `ttl_ms=2600`，情绪字段用 `neutral`，避免旧渲染器误判成强烈表情。
- 3D 侧 v1 只保存 `card` / `cardTtlMs` 并写日志；等 sprite 层接入后，按 `cardTtlMs` 过期隐藏，最新包覆盖旧包。
- 卡面绘制应放在 `glReadPixels` 命中区采样之后，装饰卡面不参与点击；若以后要点击卡面，再单独做命中 mask。

## 性能影响

- 发送：每次卡面变化一个 UDP 小包，约 96 B；不读盘、不生成图像。
- 接收：`EmotionBus::poll` 已有非阻塞循环；新增两次字符串/数字解析，量级为微秒。
- 渲染：图集 1024×512 RGBA = **2,097,152 B**；一次上传，一次 draw call；不逐帧解码 PNG。
- 当前 3D 私有字节 **97,849,344 B**；加图集约 **99.9 MB**，需在 sprite 层接入后实测。

## 已实现/已验证

- `app/asset_bridge.py`：manifest 白名单、`send_card`、`expression`、`action`、TTL 钳制。
- `app/emotion_bridge.py`：`Signal` 增加 `card` / `card_ttl_ms`；`payload_for` 附带卡面；情绪自动映射。
- `3d/emotion_bus.h` / `cpp`：`Frame` 增加 `card` / `cardTtlMs`，解析并钳制 `0..10000`。
- `3d/main.cpp`：日志追加 `card=... card_ttl=...`。
- `tools/test_asset_bridge.py`：5 项通过；`tools/test_emotion_bridge.py`：9 项通过。
- `3d/emotion_bus.cpp` 单独编译通过；`3d/main.cpp` `-fsyntax-only` 通过。
- 端到端探针：`emotion_bus` 测试程序监听 `47833`，Python 发送 `action/wave`，接收端打印
  `emotion=neutral intensity=0.70 card=action/wave ttl=2600 source=P_2D`；未占用浸泡用的 `47832`。

## 尚未做

- **sprite 层还没画卡**：3D 只接收/记录，视觉卡面要等浸泡结束后接。
- 没有把 `AssetBridge.action()` 接到 2D 的每个动作调用点；目前只提供协议入口，避免大面积改 `main.py`。
- 没有做卡面点击/拖拽；先保证装饰层不抢命中区。
- 没有把 2D skins 搬成 3D 服装；那需要 3D 建模，不属于本协议层。
