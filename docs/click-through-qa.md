# 卡面点击穿透验收

日期：2026-11-28  
状态：**通过**

## 结果

- 测试对象：`3.2.0-sprite` 安装器静默安装到临时目录后的 `whale3d.exe`（SHA256 `74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893`）
- 卡面：`expression/happy`
- `card_hit_test`：`-1`（主窗口在卡面位置返回 `HTTRANSPARENT`）
- `model_hit_test`：`1`（模型位置仍是 `HTCLIENT`）
- `target.received`：`true`
- 脚本退出码：`0`
- 机器结果：`docs/click-through-result.json`

## 实现说明

卡面不再并入主 3D 窗口 region。它由单独的透明置顶 overlay 窗口绘制，overlay 的 Win32 region 裁成卡面矩形；overlay 收到卡面鼠标事件后，向 z-order 下方第一个可命中窗口转发左/右/中键按下与抬起。

测试目标窗口临时置顶，然后把 3D 主窗口和卡面 overlay 重新提到目标上方，确保目标直接位于 3D 下方，排除截图工具、浏览器等第三方窗口抢点击。

## 边界

- 本测试验证真实鼠标点击能到达目标窗口，不验证 hover/拖拽/滚轮逐像素转发。
- 回退路径（overlay 创建失败）仍使用旧的主窗口 region + `WM_NCHITTEST`，不保证跨进程点击穿透。
