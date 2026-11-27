# 2D 资料搬进 3D：能力边界、资产桥和性能预算

日期：2026-11-27
适用版本：3D 主线 v3.2.0-dev / 2D 主线 3.1.x

## 结论

- **能搬，但不能整体搬。** 2D 的表情、动作、图标、音效能进 3D；2D 的“全身立绘皮肤”和“2D 骨骼动画”不能直接变成 3D 服装/骨骼。
- **最稳的路线是“资产桥 + 3D 原生内容”**：2D 素材做卡面/缩略图/UI，3D 模型继续用 VRM；皮肤要另做 3D 服装网格或材质变体。
- **流畅的前提是预打包、一次上传、一次 draw call**，不在渲染循环里逐帧解码 PNG，也不把 PySide6 面板塞进 3D 进程。
- 当前完成了**资产侧**：17 张表情/动作卡已打成 1024×512 图集；接渲染前的 sprite 骨架、图集 QA、协议 fuzz 也已完成（见 `docs/sprite-layer.md`、`docs/2d-atlas-qa.md`、`docs/2d-3d-protocol.md`）。渲染层还没接，避免干扰当时正在跑的 3D 浸泡。

## 现状盘点

| 组 | 文件数 | 压缩体积 | 逻辑内容 |
| :--- | ---: | ---: | :--- |
| `assets/skins` | 32 | 10,041,937 B | 9 套皮肤 × 常规/睡眠 × 1x/@2x |
| `assets/expressions` | 20 | 5,783,279 B | 10 个表情 × 1x/@2x |
| `assets/actions` | 7 | 1,113,126 B | 挥手/跳舞/敲电脑/气球/烟花/舞狮/换衣 |
| `assets/loli` | 4 | 1,497,700 B | 萝莉形态常规/睡眠 × 1x/@2x |
| `assets/ui` | 7 | 681,129 B | 头像、图标、二维码、主题 |
| 合计 | 70 | **19,117,171 B（18.23 MB）** | 全部 PNG |

这些是 **2D 平面立绘**，不是 3D 贴图源：没有 VRM 的 UV、材质分区和骨骼权重，直接贴到 3D 模型上会错位、拉伸，不能当作“换装”。

## 三类资产，三种处理

### A. 可以直接搬的

- 托盘图标、头像、UI 图标、二维码、BGM/SFX、配置语义。
- 这些不增加渲染负担，只需要复制到 3D 包并改路径。
- 当前 3D 已用 `3d/assets/ui/pet.ico`；2D 的 `assets/ui/pet_flat.ico` / `pet_head_256.png` 可以作为备选图标。

### B. 可搬，但要加一层 2D 卡面

- `expressions/*.png` 和 `actions/*.png` 是透明底全身图，适合做**屏幕空间卡面/浮层**，不适合替换 3D 脸或身体。
- 做法：离线打图集 → 启动时一次性上传 GPU → 每帧只画一个 quad。
- 已完成：`assets/2d_bridge/atlas.png` + `manifest.json`，17 张 1x 卡面，1024×512，压缩 **357,857 B**，RGBA 显存 **2,097,152 B（2 MB）**。
- 生成工具：`3d/tools/build_2d_atlas.py`。

### C. 不能直接搬的

- **皮肤**：2D 全身立绘不能直接“穿”到 3D 模型。要 3D 服装，需要：
  1. 在 Blender/建模工具里做对应服装网格；
  2. 绑到现有 28 骨骼；
  3. 做材质/贴图；
  4. 走现有 in-place 模型切换，而不是运行时叠 PNG。
- 如果只是想要“换皮肤”的视觉反馈，可先做**3D 材质色调变体**（同网格、不同贴图/颜色），但这不是 2D 立绘原样搬运。
- **2D 骨骼/Spine 动画**：`app/skeletal.py`、`spine_import.py` 那套是 2D 骨骼，不能驱动 VRM 的 3D 骨骼；要把动作语义映射到 3D clip，或重做 3D 动画。

### D. 面板/养成/聊天

- 2D 的 PySide6 控制面板约 115.5 MB（见 `docs/3d-transition.md`），不能塞进 7 MB 的 3D 核心包。
- 正确做法是保留 Python 服务，通过本地 IPC（现有 emotion bus 的 UDP 模式或 HTTP）驱动 3D；3D 壳只负责渲染、托盘、命中区和少量设置。
- 这不是“搬文件”，是“搬协议”。

## 性能预算（当前实测）

| 项 | 数值 | 说明 |
| :--- | ---: | :--- |
| 3D 当前私有字节 | 97,849,344 B（约 93.3 MiB） | `whale3d` PID 15080，2026-11-27 实测 |
| 3D 当前工作集 | 71,962,624 B（约 68.6 MB） | 24h 离屏浸泡中 |
| 2D 卡面图集显存 | 2,097,152 B（2 MB） | 1024×512 RGBA |
| 加图集后私有字节估算 | 约 99.9 MB | 接近 100 MB 线，需实测确认 |
| 当前帧率 | 约 28 FPS / 33 ms 目标 | 离屏浸泡平均 28.34 |
| 2D 层开销目标 | 1 次 draw call，<0.3 ms/帧 | 前提是不逐帧解码、不逐帧上传 |

关键约束：

- 图集必须在启动时上传一次；不能每帧 `stbi_load`。
- 卡面绘制放在 `glReadPixels` 命中区采样**之后**，这样装饰卡面不会被当成可点击区域；如果以后要点击卡面，再单独做一份命中 mask。
- 不要一次加载 32 张 skins 原图：1x 全量 RGBA 会到十几 MB，直接把私有字节推过 100 MB。
- 3D 主循环仍是 33 ms 节拍；2D 层只做 quad，不引入 Qt 事件循环。

## 建议的落地顺序

1. **资产侧（已完成）**：图集 + manifest + 生成脚本。
2. **渲染侧（下一步）**：在 `main.cpp` 加一个最小 sprite 层，先支持 `WHALE3D_CARD=expression/happy` 指定一张卡；用单独测试 exe，不改正在跑的 `whale3d.exe`。
3. **接线**：emotion bus 收到 `happy/angry/shy` 时切卡；动作事件走单独字段，不抢占 3D 表情。
4. **压测**：对比开/关 2D 层的 FPS、私有字节、CPU；若私有字节超 100 MB，退到 6 卡 1024×512 或 128px 槽位。
5. **皮肤阶段**：如果确实要“穿 2D 皮肤”，转 3D 服装建模；不要走 PNG 贴图硬套。

## 明确不做

- 不把 `assets/skins/*.png` 直接复制进 `3d/assets/models` 就宣称“皮肤已迁移”。
- 不把 2D 全身图当 UV 贴图贴到 VRM。
- 不在 3D 进程里加载 PySide6 面板。
- 不在 24 小时浸泡期间重建/覆盖 `3d/whale3d.exe`，也不启动新的 3D 测试窗口抢 GPU；等浸泡结束后再做渲染侧实测。

## 证据与路径

- 2D 素材：`assets/skins`、`assets/expressions`、`assets/actions`、`assets/loli`、`assets/ui`
- 2D 注册表：`app/paths.py` 的 `SKINS` / `EXPRESSIONS` / `ACTIONS`
- 3D 架构与“为什么不能只把 2D 贴图换成 3D 模型”：`docs/3d-transition.md`
- 图集：`assets/2d_bridge/atlas.png`、`assets/2d_bridge/manifest.json`
- 生成脚本：`3d/tools/build_2d_atlas.py`
