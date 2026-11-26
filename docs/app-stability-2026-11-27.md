# 2D 客户端链路稳定性修复（2026-11-27）

本轮针对“聊天卡 thinking / 面板越用越卡 / 音频异常卡死”做了三处链路修复，均在 `app/` 内，未改 UI 结构。

## 1. 联网学习回调线程错位

`main.py` 原先在 `threading.Thread` 工作线程里调用 `QTimer.singleShot(0, ...)`。裸线程没有 Qt 事件循环，定时器回调可能永远不执行，表现为：

1. 本地模型答不上 → 进入联网学习
2. 一直显示 thinking，没有回复
3. 用户再发消息也像被卡住

修复：新增 `_WebRelearnBridge(QObject)`，工作线程只发 `done = Signal(str, str, str)`，由 Qt 自动排队回主线程，再调用 `_after_web_relearn`。不再从裸线程碰定时器。

验证：`py_compile` 通过；联网分支由信号回主线程。

## 2. 音频解码无效缓冲死循环

`audio_manager._read_decode_buffer()` 原先：

```python
while dec.bufferAvailable():
    buf = dec.read()
    if not buf.isValid():
        continue
```

坏音频或异常解码器可以持续 `bufferAvailable() == True`，但每次 `read()` 都返回 invalid buffer，GUI 线程会在 `while` 里空转，整个桌宠卡死。

修复：

- 单次最多消费 64 块，防止无上限循环
- 遇到 invalid buffer 立即 `break`，不再 `continue`
- 后续 `bufferReady` 信号再触发，不阻塞 GUI

验证：用 FakeDecoder 构造“永远 bufferAvailable + 每次 invalid”，调用 1 次即退出，计数 `decode guard calls=1`。

## 3. 面板隐藏时重复建气泡 / 重复刷新

`panel.append_chat()` 原先无论面板是否可见，每条消息都创建完整气泡控件；后台自主闲聊持续写入时，隐藏面板也会不断堆 QLabel。`main.refresh_panel()` 也会在每次状态变化时直接重排整个面板。

修复：

- `append_chat`：日志和 `chat_log.jsonl` 始终写；面板隐藏时只进 `_pending_chat`（最多 120 条），下次 `showEvent` 一次性补气泡
- `refresh_panel`：面板隐藏直接跳过；可见时用 `_panel_refresh_pending` + `QTimer.singleShot(0)` 合并同一轮多次刷新
- `clear_chat` 同步清 pending

验证：

- `build/test_panel_pending.py`：隐藏时 `chat_lay` 61 条不增加，`show` 后 63 条、pending 清空；`refresh_panel` 隐藏时 0 次、可见时连续 3 次合并为 1 次
- `tools/_perf_panel.py`：`open_panel 0.74s`，`refresh() 0.01s`，12 页切换正常
- `tools/test_emotion_bridge.py` 7/7

## 边界

`app/render_check.py` / `app/smoke_test.py` 在 Qt 退出阶段仍以 `0xC0000409` 退出；`render_check` 已打印 `saved` 后才崩，属于进程 teardown 问题，不是本轮面板/音频改动引入的明确证据。后续单独排查 Qt 退出清理顺序。
