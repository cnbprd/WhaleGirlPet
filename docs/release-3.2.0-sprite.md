# Release 草稿：鲸鱼娘桌宠 3.2.0-sprite

状态：**发布候选已推送并创建 draft Release，尚未公开发布。** 对应现有 `v3.2.0-dev` 之后的 sprite 版本；tag `v3.2.0-sprite` 指向 `a2ef92c`，draft 资产已上传并核对；不要覆盖旧 Release。

## 一句话

3D 渲染循环接入 2D 卡面层：`expression/*` 与 `action/*` 共 17 张卡通过 UDP `card` / `card_ttl_ms` 显示；卡面由独立透明 overlay 绘制，主窗口 region 只保留模型，卡面点击会被转发到下层窗口。

## 本地资产

| 资产 | 路径 | 大小 | SHA256 |
|---|---|---:|---|
| 3D exe | `3d/whale3d.exe` | 1,370,112 B | `74E685696E6CC398FD9F8AC0420578FD16512921F1654157C7F81B632EF1F893` |
| 便携 ZIP | `3d/whale3d-whale-girl-v3.2-sprite.zip` | 3,076,613 B | `B6D777D98FAA043C8215430FE7FB9809C43E321EF8F3A9A7C6BF5132A6E09AFF` |
| 安装器 | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe` | 4,791,958 B | `CA6C2525FCB50D21699F512AECFCB18CFEBDA37337C9DE07EC5554E5A6974A45` |

旧 `v3.2.0-dev` 安装器和便携包是不含 `assets/2d_bridge` 的旧资产，不要混用。

## 已验证

- **24h 浸泡**：`exit 0`、`valid=True`、`issues=[]`、`alive_after_soak=True`；墙钟 86,553.0s，样本 2880/2881；见 `docs/soak-final-2026-11-28.md`。
- **P1**：17/17 夹具通过。
- **17 卡可见**：17/17 通过，见 `docs/2d-card-visible-qa.md`、`docs/_3d_visible_17_cards.png`。
- **点击穿透**：`card_hit_test=-1`、`model_hit_test=1`、`target.received=true`，exit 0；见 `docs/click-through-result.json`。
- **安装器**：静默安装到临时目录 exit 0，安装后 `whale3d.exe` 与 `assets/2d_bridge` 哈希匹配；卸载 exit 0。
- **资产校验**：38 checks、0 error / 0 warning PASS；见 `docs/release-asset-verify.md`。

## 发布前剩余

1. 创建 `v3.2.0-sprite` GitHub Release，上传 exe / ZIP / 安装器 / `.sha256`。
2. 代码签名：当前 `NotSigned`，SignPath Foundation 审核状态未知；不使用付费 OV。
3. 2D PyInstaller 冻结包未在本轮重新打包，不作为本版 3D sprite 发布门禁。

## 已知限制

- overlay 输入转发主要覆盖左/右/中键按下与抬起，不保证 hover / 拖拽 / 滚轮逐像素转发。
- 点击验收在受控 z 序下完成，普通桌面窗口 z 序仍需现场复核。
- 卡面是屏幕空间装饰，不参与骨骼或服装替换；只支持 Windows + OpenGL 3.3 core。
- 安装包未签名。

## 发布文案短版

```
鲸鱼娘桌宠 3.2.0-sprite

这一版把 2D 表情/动作卡面真正接进 3D 渲染循环：
- 17 张卡面通过 UDP card / card_ttl_ms 触发，支持 TTL 淡入淡出
- 卡面由独立透明 overlay 绘制，主窗口 region 只保留模型；卡面点击转发到下层窗口
- 24h 浸泡、17 卡可见、真实点击、安装器安装/卸载和资产校验均通过
- 便携包与安装器均内置 assets/2d_bridge

注意：安装包当前未签名，SignPath 审核状态未知。
```
