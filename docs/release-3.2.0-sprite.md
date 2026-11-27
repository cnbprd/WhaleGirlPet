# Release 草稿：鲸鱼娘桌宠 3.2.0-sprite

状态：**本地草稿，未发布。** 对应现有 GitHub Release `v3.2.0-dev` 之后的 sprite 接线版本；不要覆盖旧 Release。

## 一句话

3D 渲染循环接入 2D 卡面层：`expression/*` 与 `action/*` 共 17 张卡通过 UDP `card` / `card_ttl_ms` 显示，卡面只扩窗口 region，不进入点击命中区；便携包和安装器都已包含 `assets/2d_bridge`。

## 本地资产

| 资产 | 路径 | 大小 | SHA256 |
|---|---|---:|---|
| 3D exe | `3d/whale3d.exe` | 1,377,792 B | `3B2BE72FE1823FF2BBDA2884A218EE538F19871A2641BC06FBFF056910E3635C` |
| 便携 ZIP | `3d/whale3d-whale-girl-v3.2-sprite.zip` | 3,187,948 B | `BF310AB7D82342463FAEA2CEB7408F64024FB7C9A51B7654F0F440666F5928BE` |
| 安装器 | `dist/3d/WhaleGirlPet-Setup-3.2.0-sprite.exe` | 4,791,434 B | `510D182B7358E6A1601B085244D70F23724A236C6857D4FEF28AA4AD803E6C96` |

旧 pre-sprite 资产（不要当成本次候选）：

- `WhaleGirlPet-Setup-3.2.0-dev.exe`：4,424,684 B，SHA256 `7E859016691F0816AAD5A605C4035C37E9CF9D05653EF30C183F575874A8E5FF`，不含 `assets/2d_bridge`。
- GitHub Release `v3.2.0-dev` 仍是旧便携包 `whale3d-whale-girl-v3.2-dev.zip`，2,814,755 B。

## 已验证

- 图集 QA：17/17 卡通过，`max_alpha_mae=0.0`、`max_rgb_mae=0.005`、`max_coverage_delta=0.0`；见 `docs/2d-atlas-card-qa.md`。
- 3D 可见验收：`expression/happy`、`action/wave` 均可见；真实 `AssetBridge.action('wave', 2600)` 返回 True，3D 日志有 `source=P_2D card=action/wave`。
- 便携 ZIP：解压到干净目录后可启动，日志 `Sprite layer: ready (...\assets\2d_bridge)`，FPS 约 27.9–29.7。
- 安装器：静默安装到临时目录 exit 0，安装后包含 `assets\2d_bridge`，启动/卸载 exit 0。
- CI：代码提交 `5f49dcb` 对应 run `45946695091` success；后续 docs 提交对应 run `45947183087` success。
- 当前本地 HEAD `bf88e74` 还未 push；远程 `main` 的 CI 结论对应 `7db57f5`，不是这个本地 docs 提交。

## 发布前必须补的 gate

1. 24 小时浸泡结束：`status=done`、`alive_after_soak=true`、样本完整；当前任务计划程序轮预计 2026-11-28 13:51:03 结束。
2. 17 张卡在 3D 可见窗口逐张目检；现在只有 2 张做过可见验收。
3. 卡面坐标的真实 `WM_NCHITTEST` / 点击穿透采样。
4. 2D PyInstaller 冻结包打包后启动回归，确认 `WhaleGirlPet.spec` 里的 `assets/2d_bridge` 生效。
5. 上传 Release 前重算 ZIP/安装器 SHA256，并决定 tag（建议 `v3.2.0-sprite`，不要复用 `v3.2.0-dev`）。

## 已知限制

- 卡面是屏幕空间装饰，不参与点击、拖拽、骨骼或服装替换。
- 只支持 Windows + OpenGL 3.3 core；缺 GL 入口点时 sprite init 会失败，但不影响 3D 主体。
- 只画一张卡，最新卡覆盖旧卡；没有队列/动画。
- 卡面高度上限 220 px，宽度按 manifest 宽高比；极端窗口尺寸下位置和大小仍需看。
- 24h 未完成前，本版本不能标为“长稳通过”。

## 发布文案草稿

```
鲸鱼娘桌宠 3.2.0-sprite

这一版把 2D 表情/动作卡面真正接进 3D 渲染循环：
- 17 张卡面通过 UDP card / card_ttl_ms 触发，支持 TTL 淡入淡出
- 卡面只扩展窗口 region，不抢点击，不改变 3D 命中区
- 便携包与安装器均内置 assets/2d_bridge，安装后即可显示卡面
- 修复 UV 子矩形、culling、纹理方向三个接线问题

注意：24 小时长稳和 17 卡逐张可见验收仍在进行，完成前请按测试版看待。
```
