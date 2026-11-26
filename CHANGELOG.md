# 更新日志

只记录「用户能感知的变化」与对应的实测结果；内部重构不单独列。

## v3.2.0-dev（2026-11-26，未发布）

3D 路线进入 v3.2.x 的第一小步：本机情绪参数总线打通 `emotion → face`，认知层仍未进入渲染进程。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 情绪总线 | 新增 `3d/emotion_bus.h/.cpp`，UDP 仅绑 `127.0.0.1:47832`；`WHALE3D_EMOTION_PORT` 可改端口 | `Emotion bus: udp://127.0.0.1:47832`；`{"emotion":"happy","intensity":0.8}` → `face=smile` |
| 2 注入与验收 | 新增 `3d/tools/send_emotion.py` 和 `3d/tools/emotion_accept.py`；后者启动、注入、截图 | 日志 `Emotion: happy intensity=0.80 source=acceptance face=smile`；`docs/_3d_emotion_neutral.png` 与 `_happy.png` 多次运行全窗 RGB 平均差 0.626–0.674 |
| 3 文案 | README / docs / 2D 可见字符串把“番茄钟”统一为“定时任务”；旧语音别名暂时保留 | README 中“番茄钟”计数 0；`app` 仅剩两条兼容别名；`py_compile` exit 0 |
| 4 体积与元数据 | 只新增系统 `ws2_32.dll` 依赖，不新增运行时 DLL；新增 `3d/whale3d.rc` 版本资源，产品名/版本与安装器一致 | step 1 exe 1,315,840 → 1,321,472 B（+5,632 B，其中 1,024 B 为版本资源）；`ProductName=WhaleGirlPet`、`ProductVersion=3.1.0.0`；未重打 3.1.0 ZIP/安装器 |
| 5 脸部交叉淡化 | shader 同时采 A/B 两帧并 `mix`；`setFace`/`toggleSmile` 走 0.16 s 过渡，自动眨眼仍瞬时；GL 增加 `glUniform1f` | dev exe **1,322,496 B**，SHA256 `5139593C63050D63572B4663763290274422975176923204B26D285C0C1EF769`；neutral→60 ms **0.121**、60 ms→happy **0.407**、neutral→happy **0.516**；截图 `_3d_emotion_crossfade.png` |
| 6 Python 侧标签与仲裁 | 新增 `app/emotion_bridge.py`：`P_USER(3) / P_LLM(2) / P_AUTO(1)` 固定优先级 + TTL；用户显式情绪、回复隐藏标签/词表、`EmotionState` 自动提示三路；`main.py` 在聊天发送/回复/情绪衰减处接入，`_polish_reply` 移除隐藏标签 | `tools/test_emotion_bridge.py` 6/6 通过；3.1.1 exe 实测 `Emotion: happy intensity=0.90 source=P_USER face=smile`、`Emotion: sad intensity=0.65 source=P_LLM face=open`；只改 Python，不改 3D exe |

边界：三帧图集已能平滑交叉淡化，但 `intensity` 还没有幅度/时间曲线，gaze/body lean、`P_USER/P_LLM/P_AUTO` 仲裁和 Python 侧 LLM 情绪标签生产仍未接入；这一步不能称为“情绪闭环完成”。细节见 `docs/3d-emotion-bus.md`。

## v3.1.1（2026-11-26）

3D 发布链路修复：GUI subsystem、安装位置选择、旧版 2D 迁移、最小 3D CI。这个版本不改变渲染/动画功能，只把已能跑的 3D 壳变成可安装、可升级、可复现构建的包。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 终端框 | `3d/build.ps1` 明确加 `-mwindows`，把 PE subsystem 从 3 改为 2；`3d/main.cpp` 把运行日志写到 exe 同目录 `whale3d.log`，可用 `WHALE3D_LOG` 覆盖 | exe 1,323,520 B，SHA256 `CCCA98BB05BB40332DF80A3BFD0E11AEF71D926DFB60C0432C5C210218C832E0`；subsystem **2**；ProductVersion/FileVersion `3.1.1.0`；验收日志 `fps=26.5 update_us=8.23`，无额外控制台窗口 |
| 2 安装位置 | `installer/whale3d.iss` 恢复 `DisableDirPage=no`；`DefaultDirName={code:GetPreferredDir}`；检测到旧版 2D 时默认旧版目录，否则 `%LOCALAPPDATA%\WhaleGirlPet3D`；新增 `UsePreviousAppDir=no`，避免被上一次 3.1.0 的目录覆盖 | GUI 目检通过：安装向导显示 “Select Destination Location”，路径框默认 `F:\WhaleGirlPetApp`，Browse 可用；首屏显示旧版 2D 迁移提示 |
| 3 旧版 2D 升级 | 3.0.27 的卸载器 `InitializeUninstall()` 调用 `ExtractTemporaryFile()`，Inno 直接报 `Internal error: Cannot call ExtractTemporaryFile function during Uninstall.`，退出码 1；因此不再调用旧卸载器，改由 `installer/art/migrate_legacy.ps1` 迁移：先把 `config.json / accounts.json / memory.db / knowledge.db / accounts / voices / tts_cache / workspace / reports / quarantine / scripts / models / runtime / updates / ollama_library.json` 移到临时备份，删除 `_internal`、`WhaleGirlPet.exe`、`unins000.*`、旧快捷方式和旧卸载登记，再把数据移回原目录 | 在 `F:\WhaleGirlPetApp_migration_test` 的等价副本上实测：exit 0，data 全部保留，`_internal` / `WhaleGirlPet.exe` / 旧卸载键全部移除；真实 `F:\WhaleGirlPetApp` 未执行迁移，仍保留原数据 |
| 4 3D CI | 新增 `.github/workflows/3d-build.yml`：windows-latest，下载 w64devkit 2.11.0 + SDL3 3.4.20，调用 `3d/build.ps1`，校验 PE subsystem=2 和版本 `3.1.1.0`，打包 `whale3d-whale-girl-v3-ci.zip` 并上传 artifact | GitHub Actions 首次运行 `45854256592` 通过（53 秒），artifact exe 1,323,520 B、subsystem 2、ProductVersion `3.1.1.0`；release 使用的 exe 就来自这个 artifact |
| 5 包 | `3d/whale3d-whale-girl-v3.zip` 只保留 exe、SDL3.dll、README、第三方声明、VRM/GLB/atlas、placeholder 和 pet.ico | ZIP 2,809,167 B，SHA256 `4DB8C1D5884C069363C4F7F0B8BCE8DDA73D44D3D85242B18F687D6A6CA9794E` |
| 6 安装包 | 用 v3 ZIP 重打 `WhaleGirlPet-3D-Setup-3.1.1.exe`；安装器内含迁移脚本与新版向导美术 | 4,419,862 B，SHA256 `96FD16551759B8E493FABCBBE638ACA4F8B3292B40DCDE2B6F181C8EB078897C`；未签名；未做真实 2D 数据的完整升级实跑 |

边界：旧版 2D 的卸载器是**已安装产物**，无法在不重装老版本的情况下修好；v3.1.1 选择“迁移”而不是“调用旧卸载器”。如果安装器在迁移过程中被强制结束，备份目录 `WhaleGirlPetApp_userdata_<timestamp>` 会留在旧目录，脚本下次运行时可人工恢复。正式发布前仍建议先备份 `F:\WhaleGirlPetApp`。

## v3.1.0（2026-11-26）

3D 第一层“身体”落地：默认角色从 GLB 切到最小 VRM 1.0，加入 4 条两骨 SpringBone；ASR/LLM/TTS 尚未接入。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 VRM 角色格式 | `3d/tools/make_whale_girl_vrm.py` 从 `whale_girl.glb` 生成 `whale_girl.vrm`；`menu/model` 默认为 `.vrm`，失败回退 `.glb` 再回退 placeholder | `whale_girl.vrm` 351,708 B；`Model loaded: whale_girl.vrm`；19 humanoid bones + 4 条 spring 链 |
| 2 SpringBone 求解 | `model.cpp` 解析 VRM 1.0 / VRM 0.x / 命名链；每帧半隐式角弹簧；root 旋转 + tip 相对跟随；窗口位移 `setMotionInput` 作为惯性输入 | `Model springs: 4 chains, vrm=1`；`update_us` 稳态 8–9 µs；`WHALE3D_SPRING=0` 可 A/B 关闭 |
| 3 视觉验收 | `3d/spring_accept.py` 冻结基础 clip，分别跑 spring on/off 各抓 3 帧并逐像素对比 | 平均 RGB 差 0.797 / 0.765 / 1.523；第 2 帧头发区差 14.3、尾巴区差 96.7；截图 `docs/_3d_spring_on_*.png` / `_off_*.png` |
| 4 设置与默认路径 | 设置页模型项改为 `鲸鱼娘 v1 (VRM)`；默认加载 `.vrm`；in-place cache 对新路径仍生效 | 切 placeholder 首次 4–8 ms；切回 `.vrm` 0 ms；同一 PID、无子进程、exit 0 |
| 5 包与体积 | 新包 `whale3d-whale-girl-v2.zip`；exe 增加 13,312 B | exe 1,315,840 B；运行负载 7,052,651 B；ZIP 2,803,800 B，SHA256 `C76621D1856F092F859D9A97BE0DE64E70C56D3988E0DD6BD4F721D3422B871E` |
| 6 回归 | 真实鼠标点击穿透、托盘、in-place 换模沿用 v3.0.28 路径 | 透明角 underlay `BN_CLICKED id=1 count=1`；中心拖拽 `(1200,300)-(1620,920)` → `(1235,325)-(1655,945)`；私有字节 97,837,056 → 98,078,720 四轮不增长 |
| 7 Windows 安装器 | 新增 `installer/whale3d.iss` 与 `build_3d_installers.ps1`，从 v2 包构建 Inno Setup 安装包；默认装到 `%LOCALAPPDATA%\WhaleGirlPet3D`，无需管理员 | `WhaleGirlPet-3D-Setup-3.1.0.exe` 3,951,977 B，SHA256 `33A49BFD1335F105F7BF2B674EE74C6E29FBA1D29C660AFC7984F45500A2A88E`；静默安装/启动/卸载 exit 0，启动日志 4 chains / vrm=1 |

> 2026-11-27 修复重发：v3.1.0 Release 资产已替换为 GUI subsystem 的 `3.1.0.0` exe、2,805,751 B 便携包和 4,417,521 B 安装器；上面第 7 行是原包历史值，不再对应当前下载。修复包详情见 [`docs/release-v3.1.0-repaired.md`](docs/release-v3.1.0-repaired.md)。

## v3.0.28（2026-11-26）

3D 核心壳三项可用性收口；本次 Release 附 `whale3d-whale-girl-v1.zip`，2D 安装包不重建。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 真实鼠标点击穿透 | `3d/real_mouse_accept.py` 用 `SetCursorPos` + `mouse_event`，修正旧 ctypes WndProc 的 `LPARAM` 截断和 `FillRect` 调错库 | 透明角落 underlay `BN_CLICKED id=1 count=1`；角色中心拖拽 `(1200,300)-(1620,920)` → `(1235,325)-(1655,945)`；pet exit 0 |
| 2 Win11 托盘固定 | `ShellUi::promoteTrayIcon` 按 `ExecutablePath` 匹配 `NotifyIconSettings` 并写 `IsPromoted=1` | 实际路径 key `674768749172540869`；Explorer 重启后 `(1611,0)-(1643,48)` 精确裁剪为蓝发鲸鱼娘图标 |
| 3 真正 in-place 换模 | `Model` 内部 `Impl` cache；切换只改 active 指针，不隐藏窗口、不重启进程、不启 helper | 首次 placeholder 4ms、缓存命中 0ms；四轮后私有字节 98,201,600 B 不增长；同一 PID、无子进程、exit 0 |
| 4 包与文档 | 新包 `whale3d-whale-girl-v1.zip`；README 和 `docs/3d-transition.md` 同步 | ZIP 2,727,089 B，SHA256 `9EB9CCAAA1B42D5CFA440E77FFB4E331A0746F6EF35A07D0843B47CE712BE461`；包内 exe 1,302,528 B，SHA256 `53F6113B...B6D0478` |
| 5 路线声明 | 放弃 2D 主线，主线转向 3D；2D 源码/素材/历史 Release 保留归档 | `DECLARATION.md` 随版本生效 |
| 6 Windows 安装器 | 同一脚本改用 v1 包构建 3.0.28 安装包；与 3.1.0 共用 AppId/目录，后装覆盖升级 | `WhaleGirlPet-3D-Setup-3.0.28.exe` 3,946,164 B，SHA256 `C8A5ED41030A3037AACC88CF3E22E0260762F958D5ECCA8C44211A72067FDB9B`；静默安装/启动/卸载 exit 0，加载 `whale_girl.glb` |

## v3.0.27（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 本地模型状态 | 抽出 `panel.local_llm_status_text()`，未加载但有文件统一显示「可启动（没有加载）」；没装仍提示不影响使用 | 三档文案检查通过 |
| 2 完工富江脸 | `_finish_task()` 不再调 `set_expression("happy")`，完工只出 L2 气泡/音效，底脸保持 `finish_state()` 的 idle 富江脸 | 完工调用 finish_state 1 次、0 次 happy |
| 3 反馈分级 | 新增 `app/feedback.py`：L0 静默 / L1 只表情 / L2 表情+气泡+音效 / L3 高优先级强反馈；聊天回复、完工、连接失败接入 | verify_v327 19/19 |
| 4 泊松节流 | `PoissonGate` 按事件 key 做 `1-exp(-rate*dt/60)` 抽样 + min_gap；自主表情 8/min、45s，讨要 1.2/min、180s，用户/物理可 force | force/rate=0/min_gap/放行四路径通过 |
| 5 thinking 占位 | 聊天发出后 700ms 才进占位；P_LLM 好奇脸 + 1.2° 侧倾 + 「让我想一下…」；回复/失败/用户接管收回 | 进入/收回/不抢用户动作通过 |
| 6 回归 | v3.0.26 / v3.0.25 / v3.0.24 验收脚本 | 26/26、24/24、26/26 |

## v3.0.26（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 背包自动取食 | 新增独立 `_auto_use_bag()`：启动后 2.2s 和每次 care tick 都查背包；饥饿/口渴 <55 时按缺口挑食物，150s 冷却，打工中不打断；自动吃给 priority 1，静音也出声 | 饿选米饭、渴选柠檬水；安装版连吃冰淇淋/布丁直到背包 0，`auto_eat.log` 有记录 |
| 2 裙摆/尾巴分层 | 新增 `tools/make_secondary_layers.py`，按颜色门+多边形抠出 default/JK 的裙摆、尾巴 alpha 层，生成 1x/2x 与 `layers.json` | 两套皮肤 1x/2x 层尺寸与原图一致 |
| 3 Verlet spring | 新增 `app/secondary.py`：半隐式欧拉 + 子步长；裙摆用「腰固定、下摆剪切」、尾巴绕根旋转；窗口位移/镜像当惯性输入，步态回退整图 | 横向位移 12px 驱动裙摆 5.63°、尾巴 9.28°；角度有限幅 |
| 4 运行接线 | `PetWindow` 换肤/表情/睡眠/动作/缩放同步重载层；1.2 倍以上自动切 2x 层；静止保留完整底图，层只叠可动区，不挖洞露白缝 | offscreen JK 465×690 出帧；1.4x 层 566×1024 |
| 5 配置持久化 | `_save_timer` 改为单次 600ms 合并写盘，另加独立 60s 周期自动保存；修掉“运行中只改内存、退出才落盘”的旧问题 | config.json 600ms 后落盘；养成/情绪字段正确 |
| 6 回归 | v3.0.25 与 v3.0.24 验收脚本全过 | v3.0.26 26/26；v3.0.25 24/24；v3.0.24 26/26 |

## v3.0.25（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 API/本地路由 | 新增 `llm_prefer_local`（默认 False）；`llm_on` 只表示允许本地兜底；有 API 默认 API、无 API 本地兜底；API 失败单向切一次本地 | 5 种路由组合通过；当前配置 `has_api=True` 路由为 cloud |
| 2 打工二级页 | 养成主页只留三个入口；打工任务收进 `QStackedWidget` 二级页，带「← 返回养成」；`open_task_page()` 直达二级页 | stack 2 页；默认 0、去打工 1、返回 0 |
| 3 养成衰减 | 饱食 0.30→0.12/分钟（100→0 约 14h）；水分比例 0.60→0.55；离线仍最多补 6h | 连续 8h：饱食 42.4、水分 68.3；离线 8h 只结算 6h（56.8） |
| 4 归零讨要 | `critical_need(8)` 独立触发；渴了优先饮品/水果、饿了优先管饱的；背包按需求挑；面板开着只冒泡；冷却 180s | both/hungry/thirsty 识别；口渴背包选柠檬水，水分 0→30 |
| 5 表情脸补丁 | 新增 6 张羽化脸补丁（angry/happy/idle/pat/shy/walk），只换脸不换身体；默认女仆 + JK 皮肤生效；sleep/eat/curious/sleepy 保留整图姿势 | happy 267×512 身体不变、有嘴块；JK 283×512 只换脸；sleep 303×512 整图 |
| 6 伪口型 | TTS 播放用 `QAudioDecoder` 解 24ms RMS 包络并缓存 `.env.json`；嘴部小块纵向 1.0→1.32 缩放 | 真实播放 153 个包络点，最大口型强度 1.00 |

## v3.0.24（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 动作导演 | 新增 `app/director.py`：15 张 Action 卡 + `Director.submit` 五档仲裁（物理 100 / 用户 90 / LLM 70 / 自主 50 / 待机 30） | 26/26 全过 |
| 2 最短占用 | min_hold 默认 120ms，hop 180ms、tumble 300ms；同级不抢 | 26ms 时用户动作被拒，170ms 后接管 |
| 3 冷却去重 | 自主来源同动作 6–8s 冷却；用户直点绕过 | 自主重播被拒、用户连点成功 |
| 4 物理锁 | tumble 100 级不可打断；拖拽期间一切动作被拒，松手释放 | 摔跤中 hop 被拒；拖拽锁/释放通过 |
| 5 then 接力 | 播完 A 自动接 B，不再走 Timeline 队列，统一按 50 级再仲裁 | brawl 2.6s 后自动接 look |
| 6 调用收口 | 用户菜单/托盘/喂食 90，随机表演 50；打工持续态 70；自主调度在用户/LLM 动作期间跳过 | 真实窗口接线通过 |

## v3.0.23（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 安装/卸载重做 | 安装页左立绘右提问 + 路径；安装中只留立绘和「安装中…」；卸载加带立绘确认与「是否保留数据」，两帧眼泪动画 | ISCC 编译通过；向导日志检查点全过 |
| 2 启动屏缩半 | 380×580 → **190×290** | 41.8fps、p95 24.8ms、单帧 0.16ms |
| 3 模型页配色 | API 卡片改跟随主题调色板 | 深色截图与面板一致 |
| 4 API 草稿保护 | 输入即存 `api_draft`，refresh/自动更新不覆盖，保存后才清 | 改值→refresh 原值仍在 |
| 5 打工并入养成 | 删独立打工页，任务列表嵌进养成页 | 12 页 |
| 6 面板不置顶 | 去 `WindowStaysOnTopHint` | 标志检查为 0 |
| 7 聊天贴底 | 切页/载入历史后多次贴底 | 4526/4526 |
| 8 聊天出声 | `tts_on` 默认 True、阈值 60→180、回复 `priority=1` | 调用链验证；未做听感验收 |
| 9 天气资讯 | 天气字改主题色；分类按钮 92×32；加「国际」；条数 6→12 铺满 | 截图 7 分类、文字清晰 |
| 10 侧栏顺序 | 按 12 项指定顺序重排 | 顺序断言通过 |
| 11 走路腿变形 | 小角度屈膝 + 左右脚交替上提 + 起伏同步步态 | 4 相位出帧对照 |
| 12 长裙黑洞 | 腿部近黑像素透明化 + alpha 1px 模糊 | 放大裁图无黑洞 |

## v3.0.22（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 立绘统一 | 以默认皮肤为基准重绘 6 套脸，服装姿势不变；9 套皮肤各加闭眼睡颜差分（含萝莉），睡觉换图、醒来还原 | 前后对照 `docs/faces_before_after.png`；睡颜切换 27/27；@2x 28 张 |
| 2 果冻回弹 | `jelly_scale()` 阻尼正弦，换装/换形态以脚底为轴缩放回弹 | 峰值 5.2%，体积偏差 0.00267；9/9 |
| 3 面板启动 | 真凶是同步健康检查 + fsync（不是页面构建）；健康检查加缓存并延后、保存合并 600ms、去掉重复 refresh | 构造 3906→**519ms**，refresh 2056→**537ms**，二次 9–12ms |
| 4 迁移续传 | 新增 `app/migrate.py`：逐文件原子写、已复制即跳过、后台线程 + 进度 + 停止 | 120MB 40% 中断后续传只补 70MB，哈希一致；7/7 |
| 5 更新下载修复 | 同名 sha 匹配 + `api.github.com` 资产通道 + Range 断点续传 + 失败保留断点 + 安装器没起来不退 app | 38MB→62.2MB 续传完成，sha 通过 |
| 6 实时监控/自动隔离 | 实时监控默认开；命中 ≥40 分自动进隔离区（可恢复） | 隔离 24/24；真机端到端 |
| 7 EICAR 20 轮 | 稳定性默认轮次 10→20 | 20/20 |
| 8 启动屏 | 精确计时器，重拍 | 32.0→41.7fps，p95 24.7ms，单帧 0.23ms |
| 9 关于页滚动 | 关于页包滚动区；安全页加 Defender 授权提示 | 430×700 滚动 bar 可见，range 42 |
| 10 CI 引擎断言 | 构建前后都卡 `runtime\dafeiyu\dafeiyu-server.exe`，缺了直接失败 | 两处断言 |

未做项（多 Windows 版本、真实换卡、真实 11.8GB 迁移、30 分钟整段、1 小时整段）在 `docs/releases/v3.0.22.md` 里单独列明，不冒充完成。

## v3.0.21（2026-11-26）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 代码审计 | 新增 `tools/security_audit.py` 静态扫 57 个模块；修 4 个真问题：更新器没校验就装 exe、`pending_cleanup.json` 可借桌宠权限删任意目录、账号 slug 可穿越、配置写入非原子；maker 的代码黑名单补 AST 拦截 | 修复回归 29/29；`__import__("o"+"s").system("calc")` 这类拼装写法实测被拦 |
| 2 流畅度 | 新增 `tools/perf_bench.py`（idle/walk/run/tumble 多轮，出 p50/p95） | high p50 **12.23ms** / p95 19.16；mid 10.11/16.64；low 6.30/10.68 |
| 3 无独显优化 | 骨骼渲染三档 `high/mid/low`（网格 8×20 / 8×16 / 6×12），`app/perf.py` 自动判定（远程桌面或无独显→low，有独显→high），帧间隔 low 40ms / 其余 33ms | low 比 high 省 **48%**；本机（GTX1060）自动判 high、帧间隔 33ms |
| 4 规则引擎升级 | 规则 JSON 支持 `all_of` 多条件、`size_gt/lt`、`ext`，非法条件丢弃不崩；内置规则 16→**18**（加 AV-DROPPER、AV-RANSOM-SCRIPT） | 回归 13/13 |
| 5 进入速度匹配 | 动作切换用三次 Hermite 混合：起点速度=旧动作速度、终点速度=新动作速度；默认 `mix` 0.15→**0.30**，队列衔接 0.12→0.25 | crab→hop 速度突变 **15.20→1.14 px/帧（−92%）**，切换位移 16.46→0.71px |
| 6 隔离区 + 实时监控 | 新增 `app/quarantine.py`（复制→核哈希→再删原文件，可恢复，永不自动删）与 `app/realtime.py`（下载/临时/启动目录 2 秒轮询）；面板加「隔离选中 / 打开隔离区」，托盘加「实时监控新落地文件」 | 单元 24/24；单次快照 0.2ms；真机点击端到端通过（文件真的进了隔离区并可恢复） |
| 7 EICAR 稳定化 | 判定抽成 `eicar_verdict()`：自家命中、系统锁内容、系统直接删除，三种都算检出；其它错误不算通过 | **10 轮 10/10** + 分支覆盖 6/6；p50 9.0ms；本轮 10 轮都没被 Defender 拦，此前「被拦」路径由分支测试兜住 |
| 8 真机目检 | 真实窗口 + QTest 真实点击（不是离屏） | 15/15；顺手修三处 UI 缺陷：侧栏与当前页不同步、对象列长路径被压成「C...」、深色标题糊在分割线里 |

## v3.0.20（2026-11-25）

- 安全管家补上 SHA256 黑白名单查杀：黑名单命中直判高危 45 分，白名单直接放过且优先于黑名单；名单放 `<数据目录>/hashes/`，改完即生效（按 mtime 缓存）。面板加「哈希名单」按钮。
- 新增 EICAR 双层自测（面板「自测扫描能力」）：规则层纯内存认出标准串 + 端到端落盘扫描 + 无害对照零误报；被 Defender 锁住读不了时记 `blocked=system`，同样算检出。实测 18/18，自测 47.8ms。
- 扫描遇到「文件在但读不开」不再静默跳过，报告标 READ-BLOCK（内容被安全软件拦截）。
- 动画引擎补 Spine 三件机制：`play(clip, mix=0.15)` 交叉淡入（smoothstep 权重）、`queue()` 排队、`time_scale` 变速；`pose_now()` 改回本帧已混合姿态。实测 crab→hop 切换位移 16.46→2.94px（−82%），速度突变只降 27%（0.15s 窗口压不住爆发动作的速度，已记录局限）。
- 修 bug：单次动作排队的收尾帧事件会被切换重置吞掉（hop 最后一次 `land` 丢失）。
- `do_action(key, duration_ms, then="", mix=0.15)` 支持链式动作。

## v3.0.19（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 真实首帧探针 | 新增 `tools/first_frame.py`：Win32 `EnumWindows` 找可见窗口（onefile 连父/子进程一起查）+ `ImageGrab` 算灰度 std（>8 算画出来了） | onedir 三次 0.64/0.59/0.78（中位 **0.64s**） vs onefile 3.82/3.72/3.72（中位 **3.72s**），省约 3.1s |
| 2 音频（做不通） | 新增 `tools/probe_audio.py` 试三种写法 | `input_audio` 对象 200 但模型答「无法处理音频」；`audio_url` 400；字符串 500。引擎日志：`init_audio: experimental stage` → 音频没被编码 |
| 3 图片上限澄清 | 新增 `tools/probe_image_limit.py`（默认 / max-tokens 8192 / 16384 三组参数 × 5 尺寸） | `--image-max-tokens` 不影响成败；512~1280px 全过（data url 28~99KB）；卡的是**请求体 ~100KB**（156KB 那次失败） |
| 4 读字能力边界 | 同图 5 档分辨率都读不出 `EdgeOne Makers` | 回答是「0 0 0…」「方块符号」→ 4B 视觉不是 OCR，读字应走专门 OCR |
| 5 清晰度可调 | `vision.py` 的 `capture_screen/to_data_url/vision_message` 加 `max_side`；新增 `config["vision_max_side"]`（默认 512） | 512 看图 4~5s；本次实验 768→21.8s（长输出条件下） |
| 6 版本 3.0.19 | `paths.APP_VERSION` + iss 六处 + 标题「首帧实测 + 视觉可调」 | 六处 3.0.19 |

## v3.0.18（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 onedir 打包 | spec 改 `exclude_binaries=True` + `COLLECT`；iss `[Files]` 递归整个 `dist\WhaleGirlPet\`；CI portable 铺目录；build.ps1 `--onedir` | exe 4.4MB + 目录 147.6MB |
| 2 启动 | 不再解包到 `%TEMP%` | 内存到 75%峰值 **4.55s → 0.76s**（约 6 倍） |
| 3 常驻内存 | 引导进程消失 | RSS **170MB(2+1) → 83MB(1)**，省 87MB |
| 4 本地视觉 | 新增 `app/vision.py`（截屏→缩 512→JPEG q80→data URL）+ `act_look_screen` + 托盘「看看我屏幕上是什么」 | 看图 ok，1.7~10s |
| 5 mmproj 接入 | `ServerManager.mmproj_for()` + `--mmproj ... -mmdev none`；模型同目录自动匹配 | `/v1/models` 的 input_modalities：`['text']` → **`['text','image','audio','video']`** |
| 6 权重补齐 | `mmproj-gemma4-e2b-f16.gguf` 940.0MB（985,654,080 字节，ModelScope 29.8MB/s 下完），runtime 与数据目录各一份 | 加载 4.7s |
| 7 修 4 个实测坑 | PNG 原图 400 → 全转 JPEG；960px(156KB) 400 → 上限 512px(48KB)；`image_url` 必须对象（字符串写法 500）；`vision_message` 返回整条 message 不能塞进 content | `tools/probe_vision.py` A/B/D ok、C 500 |
| 8 后端一致性 | 带图/切角色时 `_force_local` 锁定自带引擎（Ollama 的 `/api/chat` 用 images 字段）；`active_role` 让重启沿用角色 | 修掉"重启后图片发给 4B 文本模型"导致的 400 |
| 9 视觉能力边界 | 能判断场景（网页/文档/界面），读不出界面小字 | `docs/api_card_v315_on.png` 未读出标题文字 |
| 10 版本 3.0.18 | `paths.APP_VERSION` + iss 六处 + 标题「onedir + 本地视觉」 | 六处 3.0.18 |

## v3.0.17（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 三档模型分工 | `ServerManager` 新增 `role_model(role)` / `ensure_role(role)`：已在跑目标模型就不重启；否则停掉再起；可用内存 < 体积×1.15 不切、写 `fallback_note` 照常用现有模型。`LocalChatWorker(role=)`，`_chat_plain` 按代码意图选档，技能路由固定 `tool` | `tools/test_model_roles.py` 20/20 |
| 2 切换代价（真机） | brain 起 5.8s/单轮 1.3s；brain→tool 6.7B **23.6s**/单轮 6.5s；回 brain 6.9s/1.6s（ctx 4096，串行 dispatch） | `tools/live_roles.py` 三段切换+三次对话全 ok |
| 3 误触发防护 | `CODE_HINTS` 收紧：去掉「异常/bug/脚本」，留「报错/traceback/这段代码/代码/函数/编译/正则/写个脚本/重构/单元测试/pandas/numpy/SQL」；走 tool 先出气泡"要等十几二十秒" | 5 个判定用例（含"最近有点异常"→非代码） |
| 4 多模态的硬事实 | `runtime\models` 下 `*mmproj*` 数量 = 0 → `gemma4-e2b-it.gguf` 只能跑纯文本；它 3269.1MB 比 brain 的 2525.9MB 还大 743MB。`fast` 默认留空 | 目录扫描 + 体积实测 |
| 5 包体瘦身 | spec 删 `tkinter` hiddenimport、删 `collect_all('tabulate')`、`excludes` 加 numpy/pandas/scipy/matplotlib/PIL/pytest/tkinter、`optimize=2`；build.ps1 同步 | exe 69.4 → **64.0 MB**（−7.8%） |
| 6 启动与内存 | onefile 解包变快 | 解包+主进程起 4.26 → **2.10s**；常驻 RSS 171 → 175MB（噪声内） |
| 7 外部建议核实 | `vlln/whale-girl` 真实存在但属 DSH 插件/桌面壳，"WhaleGirlPet 项目家族"不成立；只借"引擎/渲染分离"思想，项目已是该形状 | `docs/model_roles_v317.md` §6 |
| 8 版本 3.0.17 | `paths.APP_VERSION` + iss 六处 + 标题「三档模型分工」 | 六处 3.0.17 |

## v3.0.16（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 三层记忆 | 新增 `app/memory_tiers.py`：Core（常驻 420 字进 system prompt）/ Recall（复用 2-gram+时间衰减检索）/ Archival（新表冷存）；组合在既有 MemoryStore 上，不迁移数据 | `tools/test_memory_tiers.py` 8/8 |
| 2 衰减与归档 | 半衰期 45 天，**按"距上次衰减的天数"增量乘**（记 `last_decay`，首次跳过）；权重<0.2 且 60 天未动 → 归档 | 200 天一次衰减 factor=0.0459，归档 1 条；紧接着再调 skipped=True |
| 3 重复压缩 | 两条事实 2-gram Jaccard ≥0.6 合并，保留权重高/内容长者，权重相加封顶 3.0 | 合并 1 条，facts 减少 1 |
| 4 议程（主动性） | `agenda()` 挑「要/想/待/记得/下次/明天/还没/欠」的条目；自主行动 chatter 分支 50% 概率先说它 | 议程返回「明天要交房租」 |
| 5 事实抽取扩面（关键修复） | 真机两个库 64 条消息 **0 条事实**。`extract_facts` 从 5 条模式补到 9 条（叫X/习惯/计划/宠物），并加过滤：含 `?？吗/要是/如果/假如/你会/你能/你想` 不记；尾部语气词与"吃/喝/玩"前缀剥除 | `tools/test_extract_facts.py` 15/15（10 该记 + 5 不该记） |
| 6 注入去重 | `core()` 负责 facts，`context_block` 改传 n_facts=0 只给相关旧对话 | facts=0 时返回空串，不重复 |
| 7 版本 3.0.16 | `paths.APP_VERSION`、iss 六处 + 标题 | 六处 3.0.16 |

## v3.0.15（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 「联网后端管理」→「模型 API 接入」 | 照参考图重做成深色卡片：标题+状态点 / 名称 / API 地址 / 格式药丸（OpenAI·Anthropic·Gemini）/ 查看填写规则 / API Key+眼睛 / 高级设置折叠 / 模型列表+添加 / 获取模型列表+测试连接+粉色保存；上半是已接入列表（状态点+名称+已连接徽标+模型名+使用·编辑·断开） | 离屏截图 `docs/settings_v315.png`、`docs/api_card_v315_on.png`；`hasattr(panel,"cb_profiles")==False` |
| 2 三协议真实接入 | 新增 `app/api_access.py`：URL 补全、认证头、body 结构、回复解析、模型列表、填写规则三家分开；`ChatWorker` 按 `api_format` 走对应协议 | 协议层 21 项通过；端到端 5/5（openai「你好呀」/ anthropic「我是 Claude」/ gemini「我是 Gemini」） |
| 3 高级设置真生效 | 代理走 `ProxyHandler`；自定义请求头 `add_header`；参数覆盖 `body.update`；JSON 不合法则忽略并提示 | 服务端收到 `X-Title`、body 含 `top_p:0.9` |
| 4 状态三态与交互 | 未连接（灰）/ 已配置未验证（黄）/ 已连接（绿）；药丸互斥、眼睛切明文、断开清 Key 保留其余字段 | 单测：互斥 {openai:F,anthropic:F,gemini:T}、echoMode Normal、保存写回 `connected=True`、断开后 key="" |
| 5 旧配置兼容 | 读取时 `setdefault` 补 `api_format=models=[]`；`save_ai_settings`/`test_ai_connection` 改读卡片 | 旧四字段档在设置页正常显示为「已配置·未验证」 |
| 6 版本 3.0.15 | `paths.APP_VERSION`、iss 六处 + iss 标题改为「模型 API 接入」 | 六处 3.0.15；`py_compile` 5 个文件通过 |

## v3.0.14（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 托盘菜单去重 | 删掉 v2.9.7 留下的「设置…」(`act_theme_goto`)，只留带图标的「设置」（直达控制面板） | `app/main.py` 2 增 4 删；桌宠右键菜单的「设置…」是另一入口，保留 |
| 2 聊天文清理 | 新增 `Controller._polish_reply()`，在 `_finish_reply` 第一道：去角色前缀/代码块/markdown/链接/整句复读，压空行、修残标点、短回复拉平换行；气泡·记录·TTS 共用一份 | `tools/test_polish.py` 六类脏文本 6/6 通过 |
| 3 资讯分类按钮归位 | 六个分类按钮从横排一行改为资讯框左侧竖排（78×26，「资讯分类」标签在顶），资讯框吃掉剩余宽高 | 离屏核对：按钮 x 全 16，资讯框 x=102 宽 642，截图 `docs/ambient_v314.png` |
| 4 天气字看清 | 温度 30→34px/700，描述 14→17px/600，明细与今日 12→14px 色 #555→#3d3d47，来源 11→12px；资讯正文 13px + 1.5 倍行距 | 样式表逐项核对；离屏截图见上 |
| 5 模型三档方案 | 新建 `docs/model_roles_v314.md`：Brain（Qwen3-4B 常驻）/ Tool（temp 0.1、180 tokens、JSON）/ Fast（本地无 vision → 云端）；指出单引擎不能三模型常驻、附件当前没真传图 | 评估稿，未改代码；下一版三步已列 |
| 6 版本 3.0.14 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.14；`py_compile` main/panel/paths 通过 |

## v3.0.13（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 骨骼引擎四件套 | 新增 `app/skeletal.py`：`Skeleton`（9 根骨树，角度相对父骨）/ `Skin`（8×20 顶点 + 1–3 骨权重，LBS 形变）/ `Clip`（每骨一条角度关键帧，复用 v3.0.11 缓动）/ `Player`（播放·循环·事件去重） | 5 条剪辑全部跑通，出帧见 `docs/skeletal_v313.png` |
| 2 骨架与蒙皮 | 骨：root→spine→head、root→thigh→shin→foot（左右各一）；权重按高度分区：腿（大腿/小腿/脚三段过渡）、头颈（head/spine 过渡）、其余归 spine | 走路腿有抬腿相屈膝与支撑相伸直；鞋保持水平 |
| 3 动作库 | `walk` 0.78s / `run` 0.52s（循环），`hop` 2.04s / `tumble` 2.2s（单次含事件），`breath` 3.6s（待机呼吸） | 采样角度与预期一致（walk 抬腿 22°、run 40°、hop 落地缓冲 40°） |
| 4 脚部补偿 | 没写 foot 轨道的剪辑自动补偿 `-0.6×(thigh+shin)`，限幅 ±25° | 修前 40° 屈膝时鞋被甩到腿侧；修后鞋基本水平 |
| 5 网格细纹修复 | 顶点位移 <0.8px 吸附不动；三角形绘制关抗锯齿（0.18px 外扩消缝） | 帧图上全身横纹消失；render 23.6ms → **10.5ms**（96fps 上限） |
| 6 接入桌宠 | `walk`/`run` 优先走骨骼引擎，可回退网格腿或条带；桌宠行为页加「骨骼引擎动画」开关（`config["skeletal"]`） | 真窗口三方案逐帧对比 `docs/rig_walk_compare.png`；面板开关开→True/关→False 写回配置 |
| 7 引用声明 | 新增 `docs/THIRD_PARTY.md` + README「第三方与参考」：Godot（MIT）、Inochi2D（BSD-2）为设计参考，代码自写未复制；Spine Runtime 因许可未采用 | 两处文档已落地 |
| 8 版本 3.0.13 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.13 |

## v3.0.12（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 拆部件方案否决 | 试按解剖比例把立绘切成矩形块再旋转：膝处必然断口、裙摆下沿被整块带出、旋转留下空洞 | 对比图 `docs/rig_proto_legs.png`；结论：没有分层素材就没法拆部件 |
| 2 网格蒙皮骨骼 | 新增 `app/rig.py`：整张立绘铺 8×20 顶点网格，髋→膝两级骨骼驱动顶点，三角形仿射贴图 + 目标裁剪 + 角度缓存；枢轴全部用相对比例，换皮肤/形态/表情无需重新量 | `Rig.frame()` 10.6ms；整帧（tick+整窗）16.0ms，30fps 有余量 |
| 3 走路真屈膝 | `walk`/`run`/`trot` 改用骨骼出帧，两腿绕髋、绕膝交替；`crab`/`hop` 仍走旧条带 | 逐帧抓 8 帧对比（`docs/rig_walk_compare.png`）：新方案腿有抬腿相屈膝、支撑相伸直，旧方案是整段横移 |
| 4 两处正确性修复 | ①仿射矩阵把"基向量系数"误当矩阵元素 → 放射状撕裂；②裁剪设在变换之前被二次变换 → 碎块。改为解矩阵元素 + 先变换后裁剪 | 修复后皮肤连续、无断口 |
| 5 开关与回退 | 桌宠行为页加「走路真屈膝」（`config["rig_mesh"]`，默认开）；关掉回退旧 warp | 面板冒烟：7 个开关、开→True/关→False 写回配置、`refresh()` 回填含新键 |
| 6 已知限制 | 只有腿；脚无 IK（抬腿会离地/轻微穿地）；>40° 屈膝有拉伸；大缩放下可见网格细纹；裙摆不随腿摆 | 写进 release 文档，不假装是完整 Live2D |
| 7 版本 3.0.12 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.12 |

## v3.0.11（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 关键帧引擎 | 新增 `app/anim_engine.py`：缓动（linear/in/out/sine/back/bounce/elastic）× 轨道关键帧 × 姿态（bob/rot/sx/sy/alpha/dx/dy/flip）× 动作片段 × 事件点，另有时间轴负责播放/推进/停播 | 8 个动作全部定义并跑通；采样曲线见 release 文档表 |
| 2 8 个动作迁移 | crab / floatstep / trot / look / eatrice / tumble / brawl / hop 从 `_tick` 的手写公式改为动作片段驱动；循环动作记 `loop`，单次动作播完交回状态机 | hop 起跳 -91.6px、落地 -2.7px、三跳 2.04s；tumble 峰值 bob -25.9 / rot 22°、落地 sy 0.755 压扁 |
| 3 落地反馈 | 动作内埋事件点（`land` / `recover`），桌宠收到 `land` 播 `step` 音效并补一帧下沉；事件用已触发集合去重，循环回卷时清空 | 首轮 bug：事件每帧重复触发（tumble/hop 各几十条）→ 修 `_fired` 后 tumble 2 条、hop 3 条 |
| 4 flip 通道 | 朝向改为独立通道；动作没写 flip 轨道时返回 None，不再强行清掉皮肤/形态的镜像状态 | look 动作 flip 右→左→右正常扫视；crab 保持原朝向交替 |
| 5 接线 | `pet_window`：`set_state`/`finish_state` 停播、`do_action` 起播、`_tick` 推进并在末尾用姿态覆盖旧公式、新增 `_on_anim_event` | 真 PetWindow 冒烟：hop 2.31s 回 idle 且停播；tumble 走完落地压扁再回正；关开关回退旧公式 bob=-14.0 |
| 6 设置开关 | 桌宠行为页新增「动作用关键帧动画引擎」（默认开，配置键 `anim_timeline`） | 关掉后 `tl.playing=False`，旧公式生效 |
| 7 验收帧图 | 新增 `tools/test_anim_engine.py`（数值采样 + 8×6 帧图）与 `tools/test_pet_timeline.py`（状态机集成），帧图落 `docs/anim_v311_preview.png` | 离屏渲染需手动装字体（否则标签方块）；无 QApplication 构造 QPixmap 会崩（exit 0xC0000409），已修 |
| 8 版本 3.0.11 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.11 |

## v3.0.10（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 天气卡片 | 「天气资讯」页新增「现在天气」：温度大字 + 城市·天气 + 体感/湿度/风/降水/空气 + 今日高低温 + 数据源与更新时间；新增 `ambient.WeatherWorker`（后台拉取） | 郑州实测 16°、晴、湿度 33%、空气优、今日 3~21°、来源「中国天气网 更新 20:18」 |
| 2 资讯框撑满 | 去掉 `txt_news` 的 86px 上限，改 `stretch=1` 顶到页面底部；`_wrap_prefs(fill=True)` 不留底部空白 | 560px 页高时资讯框 323px（原 86），底边贴到页面底部 |
| 3 安全管家核心 | 新增 `app/guard_core.py`：纯 Python PE 解析（节区熵/可写可执行段/入口点异常/签名目录/时间戳）+ 迷你规则引擎（正则/字符串/十六进制 × file/path/cmdline × 权重）+ 持久化审计（Run/RunOnce、启动文件夹、计划任务、服务、IFEO）+ 进程命令行审计 | 真机 244 文件 / 132 进程，4.8s 扫完，0 高危；样本目录 6 条线索（H001 38 分、H010 30 分…）合计 68 分「高」 |
| 4 误报收敛 | 排除 node_modules/site-packages/.git 等开发目录；`.js/.json` 豁免 base64 规则；勒索规则改为勒索信特征（不再匹配普通 `.crypt`）；进程只看主程序路径；系统/Program Files 命令豁免 | 首轮扫描误报 11 条 64 分（Firefox/pnpm 被当成勒索）→ 修正后 4 分「提示」，仅 1 条 info |
| 5 只报不杀 | 报告只给线索与理由，不删除/不隔离；`mode` 字段明写「只读研判」 | 报告 markdown 末尾固定声明处置边界 |
| 6 Defender 交接 | `defender_scan()` 调 `MpCmdRun.exe -Scan -ScanType 3 -File`，可疑文件逐个深扫；没有可疑文件时改用快速全盘扫描 | 单文件实测返回 `Scan finished. … found no threats.`（returncode 0） |
| 7 报告落盘 | 每次扫描写 `<数据目录>/reports/guard_<时间>.md` + `.json`，面板可导出、可打开目录 | 实测生成 md/json 各一份 |
| 8 面板接线 | 安全页拆两块：上只读体检、下安全管家（扫描/交 Defender/导出/开目录 + 结果表格 等级/对象/原因/规则 + 进度行） | offscreen 冒烟：表格 6 行 4 列、进度行「60% · 已解析 120/244」、Defender 回调正常 |
| 9 版本 3.0.10 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.10 |

## v3.0.9（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 请求串行调度 | `ServerManager.dispatch()` 统一入口：同一时刻只放一个推理请求（引擎只有 1 个 slot），其余排队；聊天/指令解析两路并发不再互相抢 slot 卡到超时 | 两路并发：A 1.0s 答「你好」、B 2.1s 答「再见」，总 2.1s（纯串行，无一失败） |
| 2 模型自动降级 | `candidates()` 按「用户指定 → 内置首选 → 其余按体积升序」排序，同一份权重（体积差 <5MB）不重复当候选；一个模型加载失败自动换下一个 | 故意放一个坏 gguf：`_bad.gguf 加载时进程退出` → 自动改用 `qwen35-4b-Q4_K_M.gguf`，7.2s 起来 |
| 3 端口自适应 | 启动前探测配置端口，被占用就顺延找空闲端口，`port_auto` 记状态 | 先占住 8099 再启动：自动改用 8085，health 通过 |
| 4 失败自愈 | 进程活着但 `/health` 不通（显卡上下文被回收、端口被抢）也判为不可用，重启一轮再答 | kill 引擎进程后 `health=False` → 自动重启并答「重启」，8.1s |
| 5 Ollama 预检 | `ollama_runtime_ok()` 零成本检查 `lib\ollama\llama-server.exe` 是否存在（60s 缓存）；缺失就判定 Ollama 不可用，「自动」不再每次都白打一次 500 | 本机：alive=True 但运行库缺失 → 自动直接走自带引擎，状态行提示「Ollama：运行库缺失，已自动跳过」 |
| 6 去掉「只用 Ollama」 | 模型页后端下拉只剩「自动」「只用自带引擎」两项；老配置里的 `ollama` 一律按自动处理并写回 `auto` | offscreen 冒烟：下拉停在 auto，配置已归一为 auto |
| 7 状态可视化 | 模型页新增调度状态行：当前模型、端口（是否自动换过）、是否正在推理、降级说明、上次错误、Ollama 状态 | 状态行实测输出全部字段 |
| 8 版本 3.0.9 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.9 |

## v3.0.8（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 Ollama 官方库 | 新增 `ollama_hub.library()/tags()/manifest()`：抓 ollama.com/library 名单（12h 缓存）、查 registry manifest 拿权重 blob 直链、下载即标准 GGUF（复用断点续传） | 库页抓到 272 个模型；`qwen3.5:4b` manifest 2525.9MB、blob 头 `GGUF`；0.8b tag 774.2MB；不写 tag 时列 8 个可选 tag |
| 2 本机 Ollama 导入 | `local_installs()/import_all()` 读 `OLLAMA_MODELS` 的 manifests → 复制 model blob 为 `<name>-<tag>.gguf`；`(name,tag)` 去重、已在模型目录同名则跳过；后台线程 | 本机实测：导入 gemma4-e2b-latest（3269MB）+ qwen3.5-4b（2526MB），deepseek 已存在跳过；共复制 6.08GB |
| 3 三模型落地 | 三个 Ollama 模型均可用自带引擎直接跑 | `qwen3.5-4b.gguf`：backend=dafeiyu_cpp、加载 4.6s、问「你好」答「你好」 |
| 4 后端下拉 | 模型页新增「本地推理后端」：自动 / 只用自带引擎 / 只用 Ollama，写入 `llm_backend` 并停引擎 | offscreen 冒烟：5 个新面板方法齐全 |
| 5 下载落地路径 | `_on_dl_done` 改存绝对路径，避免同名模型切错 | — |
| 6 版本 3.0.8 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.8 |

## v3.0.7（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 模型扫不到 | `local_llm.scan_models()` 改为扫多目录（程序 runtime\models、数据目录 runtime\models / models / workspace / workspace\models、用户自定义目录），递归 2 层，按 GGUF 魔数识别、排除 <1MB 占位文件、同名同体积去重 | 本机扫出 6 个（原只有 4 个且重复计 10 条）；默认 qwen35；833MB 模型加载 6.2s、health/对话均通 |
| 2 模型页 | 列表标注所在目录、悬停显示全部搜索目录、新增「添加模型文件夹」按钮、下载落地改数据目录（Program Files 可写） | offscreen 冒烟：19 条渲染正常，`_add_model_dir` 存在 |
| 3 Ollama 假活 | 实测本机 Ollama 0.40.16 的 `llama-server.exe` 缺失，`/api/tags` 正常但生成 500；`backend` 改为「ollama 坏过就退 dafeiyu_cpp」，4xx/5xx 一律记病因并回退，进程内不再重试 | 强制 ollama 的配置：500 → 自动回退 → 17.5s 后答出「你好」，backend 变为 dafeiyu_cpp |
| 4 Ollama 可见化 | 模型页新增「Ollama 里的模型」段（3 个，可一键切）+「检查 Ollama 能否真正生成」按钮 | 自检实测文案：`✘ Ollama 自己坏了：找不到 llama-server.exe（HTTP 500）…` |
| 5 联网搜索 | 从只抓 Bing 改成 Bing → 百度 → 360 链式兜底 + 标题去重 + `html.unescape` 解实体 | Bing 10 条 0.4s；百度 9 条；360 7 条；DDG 本机超时未启用；「郑州 明天 天气」Bing4+百度1=5 条 2.2s |
| 6 浏览器 | 原来硬编码 Tabbit 一条路径；改为 ①注册表默认浏览器 ②App Paths 12 个家族 ③常见安装路径，按家族给开窗参数 | 本机探测到 Edge(chromium)、Tabbit(chromium)，首选默认浏览器 |
| 7 版本 3.0.7 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.7、零残留 3.0.6 |

## v3.0.6（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 启动浮层卡住 | `splash.py` 的 `_tick` 里淡入那行每帧把 `_fade` 重置回 1.0，与淡出每帧减 0.075 互相抵消，`_fade` 恒为 0.925、永远进不了关闭分支。改为淡入加 `not self._done` 条件 | 修复前 1/3/6/9 秒 `_fade` 均 0.925；修复后 `_fade` 递减到 −0.05、`closing=True`、`IsWindowVisible=0` |
| 2 启动浮层兜底 | 15s 硬超时 `_hard_close`、Win32 `ShowWindow(SW_HIDE)` 直隐藏、`step2/step4` try/finally、`runtime\startup.log` 时间线 | 探针 tick 222 次 0 异常，关闭路径走通 |
| 3 资源管理器不定时刷新 | `begin_run` 默认不建 `IconLayout`，仅 `allow_icon_scatter=True` 才用 `LVM_SETITEMPOSITION` 挪真实图标；面板「桌宠行为」新增开关，默认关 | 机制：20s 抽签 → run 权重 10% → 撞 3 个图标 → 2.6s 复位，每次重排一次资源管理器 |
| 4 版本 3.0.6 | `paths.APP_VERSION`、iss 六处同步 | 六处 3.0.6、零残留 3.0.5 |

## v3.0.5（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 说明补全 | 正文补上引擎 4.5GB 的构成核实（`2525.9MB MEM_MAPPED qwen35-4b-Q4_K_M.gguf` + `2348MB 私有提交`），并把「怎么用这条结论」写清 | 功能同 3.0.4，无代码改动 |
| 2 版本 3.0.5 | `paths.APP_VERSION`、iss 五处同步 | 本地包打出来核对 |

## v3.0.5（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 无功能改动 | 与 3.0.4 代码一致，仅版本号 + 文档：把「引擎 4.5GB 构成」的核实结论写进 Release 正文（v3.0.4 正文发布时还没核实完） | `paths.APP_VERSION` 与 iss 六处同步 3.0.5 |
| 2 正文补齐 | 新增 `docs/releases/v3.0.5.md`：孤儿进程清理、空闲卸载、`-np 1`、映射段 2525.9MB / 私有提交 2348MB 的实证表 | — |

## v3.0.4（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 孤儿推理进程 | 实测一个残留 `dafeiyu-server` 从 02:47 活到 17:15，独占 2388.6MB。新增 `app/proc_guard.py`（Windows Job Object + KILL_ON_JOB_CLOSE），子进程随父进程一起死 | 父进程 `os._exit(1)` 后 2 秒子进程消失 |
| 2 启动清残留 | `local_llm.kill_stray_servers()` 在启动时杀掉上次留下的推理进程（tasklist 用 OEM 编码解析，中文系统不乱码） | 实测杀掉 1 个 |
| 3 空闲自动卸载 | 引擎闲置超 `llm_idle_unload_min`（默认 20 分钟）自动 stop；0 = 从不卸载 | `should_unload(20)=True` → stop 后引擎 0MB |
| 4 面板设置项 | 自定义模型页新增「空闲自动卸载 __ 分钟」QSpinBox（0–240，0 显示"从不卸载"），改动即存 | 截图 `v304-model-page.png`，值 20 分钟 |
| 5 引擎单 slot | 启动参数加 `-np 1`（4 slot 白占 KV） | RSS 4647.6 → 4492.4MB |
| 6 聊天历史 | 改为 deque 流式读，只留最近 240 条在内存 | 编译通过，面板加载正常 |
| 7 portable 带引擎 | CI 打 portable 时把 `runtime/dafeiyu` 一起打进 zip | workflow 已改，待 CI 验证 |
| 8 内存构成核实 | 用 `VirtualQueryEx` + `GetMappedFileNameW` 遍历引擎地址空间：`2525.9MB MEM_MAPPED qwen35-4b-Q4_K_M.gguf`；`EmptyWorkingSet` 后私有提交 2348MB 不变 | 见 `tools/mem_big_regions.py` |
| 版本 3.0.4 | `paths.APP_VERSION`、iss 五处同步 | — |

## v3.0.3（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 安装向导文案 | 第 4 问「要不要顺手装个本地模型」原来写「约 3–4GB」，与实际可选模型（1.0 / 2.3 / 4.4 / 5.8GB）不符；改为「装完自动下，约 1–4.5GB；先不装也行，之后在设置里补」，默认仍是先不装 | iss 编译通过 |
| 2 模型仓库只显示一行 | `lst_repo` 只设了最大高度 112，布局又把它压到一行；改为最小高度 168、最大 220，现在一次可见 3 行，双击即可下载 | 实测 `repo_h=192`，可见 Qwen3-4B 已装 / DeepSeek-1.5B 可下 / ★DeepSeek-7B 可下 |
| 3 自定义模型页可滚动 | 新增 `_scrollable()`，把该页包进 QScrollArea（透明底、无边框），内容超出窗口时滚动而不是压扁控件 | 截图 `assets\_matting\v3\v32-model-page2.png` 右侧出现滚动条，控件未被切 |
| 4 状态文案 | 没装模型时从「未找到模型或推理程序」改为「还没装本地模型（不影响使用，聊天走云端或台词）」 | 同截图 |
| 5 安装→首启下载链路确认 | 选「要，装一个」→ 写 `want_local_model.flag` → `Controller.__init__` 调 `_check_install_model_flag()` → 4 秒后 `_auto_get_local_model()` 按硬件挑模型下载 | 代码链路核对，无断点 |
| 版本 3.0.3 | `paths.APP_VERSION`、iss 五处同步 | — |

## v3.0.2（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 引擎入库 | Release 安装包比本地少 22MB 的根因是 `runtime/` 整个被忽略，CI 拿不到 `runtime/dafeiyu` 的推理引擎。改为把该目录（62.9MB / 52 个文件，最大单文件 10.9MB）纳入仓库，`runtime/models`、`runtime/_dl`、日志、配置备份继续排除 | `git status` 暂存 53 项（52 引擎文件 + .gitignore），无模型/日志混入 |
| 2 安装包补回离线能力 | CI 的 Inno 步骤能取到 `Source: "..\runtime\dafeiyu\*"`，装完自带引擎，只差 `.gguf` 模型 | 待 CI 产出后核对安装包体积应从 70.8MB 升到约 93MB |
| 3 无引擎时的降级行为已确认 | 单独放 exe 到空目录（等价线上安装结果）实测：进程存活 13 秒、桌宠正常显示；`local_llm.available()` 为 False 时跳过本地模型，聊天走云端 API 或内置台词，不崩不卡 | ALIVE_NO_RUNTIME=True |
| 版本 3.0.2 | `paths.APP_VERSION`、iss 五处同步 | — |

## v3.0.1（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 启动画面改成「纯人物在动」 | 用户明确：要学 Windows 开机动画那种「图标自己在动」，不要任何背景板。于是 ① 删掉 PyInstaller 原生启动图（Tk 窗口只能显示不透明方块图，做不出透明背景）；② 重写 `splash.py`：420→380×580 透明浮层，只画大肥鱼本人，无渐变/光晕/涟漪/气泡/文字/地面投影，靠呼吸（纵 ±3.2%、横 ∓1.8%）、浮沉（±9px）、漂移（±8px）、倾身（±1.8°）让她活着；③ 只保留 default 一套立绘，取消三帧轮播（另两帧是不同服装，切换像换装） | 四帧质心 (183,294)→(191,302)→(191,288)→(175,269)，包围盒同步变化，证明是动画不是静图；截图 `v31-splash-t03/t09/t18/t28.png` 背景全透明 |
| 2 玩具改一次性消耗 | `play_toy()` 先 `take_from_bag` 扣一个，玩完即消失；语音会报剩余数量（「这一个玩坏了，背包还剩 N 个」） | 连玩两次：2→1→空，第三次返回 False 并提示再买 |
| 3 首启新人礼包 | `state.apply_welcome_gift()`：饱食/水分/心情低于 70 抬到 70，只升不降；靠存档里的 `gift_v3` 标记只发一次，之后再饿到 0 不会偷偷复活；`main` 在 pet 建好后立刻落盘 | 0/0/14 → 70/70/70；带标记再以 0/0/5 载入仍是 0/0/5 |
| 版本 3.0.1 | `paths.APP_VERSION`、iss 五处同步 | — |

## v3.0.0（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 启动画面重做 | 两张图一起改：① `assets/ui/splash_native.png`（exe 冷启动时 PyInstaller 那张静态图，由 `tools/make_splash_native.py` 用 QPainter 重绘 420×620：中央亮蓝光团 + 右上斜光柱 + 左上冷光 + 四圈涟漪 + 28 颗上浮气泡 + 脚下水波 + 上下压暗）；② `splash.py` 的 Qt 启动窗口同风格重写（多层径向渐变、呼吸光晕、错相位涟漪、16 气泡、外缘 alpha 归 0 融进桌面）。两张都保留人物立绘，背景不再是纯色块 | 实拍 `assets\_matting\v3\v3-splash.png` 与 `assets\ui\splash_native.png`（420×620，258 KB） |
| 2 托盘去剪贴板 | 删除「搜索剪贴板内容（读取前先问你）」项，`ask_search_clipboard()` 保留但无入口 | 托盘菜单项清点 |
| 3 隐藏桌宠去重 | 删掉单独的「隐藏桌宠」，只留「显示 / 隐藏桌宠（Alt+Shift+F）」一项 | 同上 |
| 4 陪我聊聊天合并 | 右键菜单删掉「陪我聊聊天」，统一走「设置 → 聊天」页（侧栏第 4 项） | 右键菜单项清点 |
| 5 设置窗口可缩放 | `resize(660,820)` + `setMinimumSize(520,560)` + 右下角 QSizeGrip 抓手，`resizeEvent` 贴角 | 实测 `resize(520,620)` 后 size = 520×620，截图 `v3-panel-small.png` |
| 6 名字框只在编辑时出现 | 平时只显示「名字：大肥鱼」+「修改」按钮；点修改才露出输入框与保存键，保存后收起只留名字 | 截图 `v3-panel-status.png` / `v3-panel-status-edit.png` |
| 7 饱食/水分/心情重做 | 饱食 `0.30/分钟`（约 5.5 小时 100→0），睡着折算 35%；水分严格按「比饱食低 40%」= 饱食的 60%；心情只在「25 分钟无互动」后开始掉（`0.30/分钟`），睡觉暂停；取消「低饱食连带掉心情」 | 脚本验证 init 70 → 1 小时后饱食 52、水分 54.2（比值 60%）；参数取自 MiroPets（halo）、Dilder 设计文档、拓麻歌子社区实测、QQ 宠物（打工消耗高于空挂） |
| 8 动作分级消耗 | 新增 `ACTION_DRAIN` 表：走路 1.2/0.7、跑步 4.0/2.4、跳舞 2.4/1.4、蹦跳 0.6/0.35、被捏 0.3/0.2、看书 3.0/1.8、满屏跑 6.0/3.6、摸鱼 1.0/0.6、清理 5.0/3.0、擦桌面 4.0/2.4、做家务 6.0/3.6、玩耍 3.0/1.8（饱食/水分） | `do_action` 与 `start_task` 均已接入 |
| 9 亲密度系统 | 抚摸 1.0（日上限 40）、聊天 1.0（20）、喂食 1.0（6）、喜好食物 2.0（4）、玩耍 3.0（3）、买玩具 5.0（1）、喝水 0.5（4）；超上限只按两折；分级：80 挚友 / 60 亲密 / 40 朋友 / 20 熟悉 / 0 陌生 | 玩一次玩具 78 → 81；依据同第 7 条搜索（心动小镇好感度机制：抚摸少量 / 喂食中等 / 喜好食物大量 / 玩耍中等至大量） |
| 10 玩具货架 | 新增毛线球 24 金币、逗猫棒 30、泡泡机 36、小黄鸭泳圈 42，背包里点「陪她玩」触发玩耍动作+加心情亲密，玩具不消耗 | 截图 `v3-shop-toys2.png`、`v3-bag-toys.png` |
| 11 打工动作真实化 | 五个工种各自持续表演：看书（前倾点头+书）、摸鱼（慢晃+泡泡）、清理（左右大幅摆+扫帚帚头）、擦桌面（高频画圈+抹布）、做家务（抱箱前移+纸箱），道具用 QPainter 纯代码画，不再 4.2 秒后回 idle 空转 | 五张实拍 `v3-pet-work_*.png` |
| 12 定时任务合并 | 番茄钟并入「日常提醒」（专注计时 25/45/60/停止 + 喝水/久坐/音效三勾选），删除独立番茄钟分组；「定时任务」列表与「昨天使用情况」改为可伸缩，铺满整页无底部空白 | 截图 `v3-panel-remind.png` |
| 13 聊天卡顿与双发 | 双发：`panel.send_chat()` 不再自己 append，统一由 `main.send_chat(text, attach, show)` 挂气泡；卡顿：`_system_text()` 里同步联网段（urllib 15s 超时阻塞主线程）删除，改走已有异步线程 | 清屏后发一条：USER_BUBBLES = 1 |
| 14 历史重复清理 | `load_chat_history` 对相邻同角色同文本同附件去重（清掉旧版双发留下的成对记录） | 重载后无成对重复 |
| 15 气泡换行修复 | 气泡宽度上限按可用宽度算并给 QLabel 设最大宽度，行高用 `heightForWidth` 手动兜底；清屏与货架切换先 `setParent(None)` 再 `deleteLater`，不再出现两个气泡/按钮叠在一起 | 长句实拍 `v3-chat-long.png`，多行完整不裁切 |
| 版本 3.0.0 | `paths.APP_VERSION`、iss 五处同步 | — |

## v2.9.10（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 关于与更新页改版 | 按用户给的参考布局重排：顶部 64×64 头像 + 「鲸鱼娘桌宠」+ 版本 + 一句话；下面两组分区 | 离屏实拍 `assets\_matting\v299-about.png`（706×914） |
| 2 「源码与下载」组 | GitHub 仓库、版本发布页、问题反馈三行，每行带说明与「打开」按钮，走系统浏览器 | 三个链接指向 `github.com/cnbprd/WhaleGirlPet` 及其 `/releases`、`/issues` |
| 3 下载二维码 | 新增 `assets\ui\repo_qr.png`（398×398，白底圆角、深码），指向 releases 页；页内 132×132 展示 + 手机扫一扫说明 | 由 `tools\_make_about_assets.py` 用 qrcode 生成，实拍清晰可扫 |
| 4 顶部头像素材 | 从 `pet_flat.ico` 取最大帧、裁掉透明边、补成正方形再缩到 256，存 `assets\ui\about_logo.png` | 248×248 → 256×256，96,226 字节 |
| 5 去掉群与教程 | 不做 QQ 群、使用教程、加入社区、已满员群折叠；只留仓库、发布页、反馈与二维码 | 页面元素清点无群/教程/社区字样 |
| 6 「帮助与维护」组 | 检查更新 + 清单地址 + 看诊断日志（优先 `dafeiyu-server.log`，没有就开数据目录）+ 打开数据目录 + 软件信息（程序目录/数据目录/本地引擎） | 按钮信号已接；日志路径按运行目录解析 |
| 7 依赖 | `.venv` 新增 `qrcode`（仅生成素材用，运行时不依赖，二维码是静态 png） | `import qrcode` 通过 |
| 版本 2.9.10 | `paths.APP_VERSION`、iss 五处同步 | — |

## v2.9.9（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 1 设置拆成左侧独立页 | 设置页内部的五个子标签取消，关于与更新 / 储存位置 / 语音唤醒 / 天气资讯 / 桌宠行为直接成为侧栏页；`_tab_prefs` 拆成 `_tab_about`、`_tab_store`、`_tab_wake`、`_tab_ambient`、`_tab_pet_behavior`，删掉 `QTabWidget` 与子页包装 | 侧栏 9 页 → 13 页，安装版实拍 `assets\_matting\v299-installed-panel.png`（722×953） |
| 2 面板与托盘改名 | 窗口标题「控制面板」→「设置」；托盘 QAction 同步改「设置」 | 实拍窗口标题栏显示「设置」 |
| 3 图标统一大肥鱼 | `assets\ui\pet_flat.ico` 恢复为透明 Q 版七档 ico（16/24/32/48/64/128/256），面板标题栏加 22×22 `pet_head_256.png` 小头像 | 头像单元格像素检测 149 种颜色、最亮 (245,213,197) |
| 4 启动即崩的括号 | `panel.py:50` `setWindowIcon` 调用少了右括号（压缩前遗留），补齐并加 `icon.isNull()` 守卫 | 源码可正常 import、打包后正常启动 |
| 5 睡觉蹲坐 | `sleep` 分支改为蹲坐打盹：`sy=0.72`、`sx=1.06`、头顶下沉、慢呼吸、头 18 秒歪一次 | 四帧对比 `assets\_matting\v299-sleep-sheet.png` |
| 6 动作不再换衣 | 非默认皮肤不套动作帧，靠程序化动作表演 | 汉服下立绘不变、默认皮肤仍用帧 |
| 7 右键菜单精简 | 托盘/右键删掉「语音说一句（Ctrl+Alt+V）」「今天天气」「说条科技新闻」「换天气城市…」，功能迁进「语音唤醒」「天气资讯」页 | 菜单项清点只剩常用项 |
| 8 硬件探测缓存 | `hwinfo.snapshot()` 打开面板被调 9 次、每次起 `nvidia-smi` 子进程 60~70ms；加 `_CREATE_NO_WINDOW` 与 90 秒缓存 | open_panel 3.9s → 1.84s |
| 9 子进程禁窗 | `hwinfo`、`secscan._run_ps()`、`suspect_processes()` 三处 `subprocess.run` 补 `creationflags=0x08000000` | 点安全体检不再闪黑框 |
| 10 麦克风检测缓存 | `voice_cmd.has_microphone()` 每次 0.4~0.5s、一次刷新查两次；加 `_MIC_TTL=300` 缓存 | 刷新耗时 0.84s → 0.12s |
| 11 Ollama 请求去重 | `local_llm._http_json` 一次打开被调 12 次；加 `_HTTP_CACHE` + `_HTTP_TTL=4.0` | 累计 0.68s 降到 2~3 次请求 |
| 12 主题不重复套 | `apply_theme()` 每次全量 `setStyleSheet`（130 控件、0.29s）；记住 `_theme_mode`，同主题直接返回 | 二次打开不再花这 0.29s |
| 13 性能实测 | 源码 open_panel 3.9s → 1.84s → 1.54s；`refresh()` 0.84s → 0.01s | 安装版冷启首开 1.89s、热开 0.31s；10 秒 CPU 0.36s（单核 3.6%）、内存 119MB |
| 版本 2.9.9 | `paths.APP_VERSION`、iss 五处、面板右上角同步 | `dist\WhaleGirlPet-Setup-2.9.9.exe`（86,684,968 字节） |

## v2.9.8（2026-11-25）

用户 8 条反馈，逐条落地：

| 项 | 改动 | 实测 |
|---|---|---|
| 1 番茄钟/提醒并入定时任务 | 侧栏 10 页 → 9 页：`_tab_remind` 改成合并页（番茄钟 + 日常提醒 + 定时任务 + 昨天使用情况），页名统一「定时任务」；`panel_v2.build_schedule` 供合并页复用，旧 `tab_schedule` 保留兼容 | 实拍 `assets\_matting\v297-panel-02-定时任务.png`，四块内容一屏放得下 |
| 2 本地大模型补模型仓库与建议 | 「本地大模型」组新增「模型仓库」列表：★ = 按本机配置推荐，列出名称、体积、已装/可下/仅仓库；双击或「下载选中的」直接走 `ctl.download_model` | 实拍 `v297-panel-06-自定义模型.png`：Qwen3-4B 已装、DeepSeek-1.5B 可下、★DeepSeek-7B 可下，推荐理由在下方 |
| 3 迁移后自动删旧文件 | `_migrate_store` 复制完逐项删旧；被数据库/缓存占用的写 `%APPDATA%\WhaleGirlPet\pending_cleanup.json`，`paths.cleanup_pending()` 在下次启动（数据库打开前）再清一次，清完删标记 | 代码路径完整；**没在用户真实数据上执行迁移**（避免动 11.8GB 模型目录与记忆库） |
| 4 去掉金币到账语音 | 删掉每分钟自动 +2 金币的 `coin_timer` 与「叮——又攒了一点金币」气泡/音效；金币只从打工结算来 | 自检 `has_coin_timer=False`；顺带堵住一小时白送 120 金币的通胀口子 |
| 5 做动作不再换衣服 | 动作帧只有默认女仆那一套：换装/萝莉形态下 `do_action` 不再套帧，保留当前立绘，靠 `_tick` 的摆臂/跳/转表演；默认皮肤仍用帧 | 自检：汉服下 `hanfu_base_unchanged=True`、默认装 `default_uses_sprite=True` |
| 6 睡觉要有变化 | `sleep` 分支从「透明度 0.85 站着不动」改成压暗到 0.70 + 慢呼吸（0.9Hz）+ 缓慢歪头打盹（±7°）；睡觉前先收掉正在播的动作 | 自检：`sleep_state=sleep`、`sleep_alpha=0.7`、`sleep_rot=2.9` |
| 7 设置拆成四个模块 | 「设置」页内改子标签：关于与更新 / 储存位置 / 语音唤醒 / 天气资讯 / 桌宠行为（v2.9.7 的桌宠行为保留成第五页）。关于页补「软件信息」：程序目录、数据目录、本地引擎、源码仓库；天气资讯加六类资讯按钮 + 文本框 | 五个子页实拍 `v298-prefs-0..4`；点「体育」实抓 6 条标题（田秉毅任国羽主教练 / 林丹谈羽毛球…） |
| 8 空的设置面板补上名字 | 设置页顶部加「设置」大标题；右键与托盘入口文案统一改成「设置…」（原「桌宠行为设置…」「主题（在设置里改）」） | 实拍 `v298-prefs-0-关于与更新.png`：顶部「设置」两字与五个子标签 |
| 版本 2.9.8 | `paths.APP_VERSION`、面板右上角、安装包文件名同步 | `dist\WhaleGirlPet-Setup-2.9.8.exe` |

## v2.9.7（2026-11-25）

本轮是用户 14 条改造清单的落地。基准来自用户原话，逐条对账见下表。

| 项 | 改动 | 实测 |
|---|---|---|
| 1 每次更新及时进 git | 新增 `tools\release.ps1`：一条命令完成「版本号校验 → PyInstaller 打包 → Inno 编译安装包 → `git add -A`/commit/push origin main → 打印 CI 地址」；`-Bump` 可自动末位 +1，`-SkipBuild` 只推代码 | 本轮用它发布 v2.9.7（提交与 CI 结果见仓库 Releases） |
| 2 换装后「白眼」 | 逐张目检 8 套皮肤：`blackgown` / `blackgreen` / `blackred` 三套原图眼睛只有眼白、没有瞳孔；已重绘黑瞳（黑红款保留红瞳），原图备份在 `assets\_matting\v297\backup_*.png` | 对比图 `assets\_matting\v297\skins_all.png`（修后）与 `backup_blackred.png`（修前）；其余五套为闭眼设计，不是缺陷 |
| 3 llama → dafeiyu | 运行目录 20 个可执行入口早已是 `dafeiyu-*`；本轮续改：`runtime\llama-server.log`→`dafeiyu-server.log`、`runtime\_dl\llama-cpu.zip`→`dafeiyu-cpu.zip`、`test_offline_llama.py`→`test_offline_dafeiyu.py`（内部改为 `dafeiyu_cpp`）、`build.ps1` 注释、`README.md`/`PROJECT.md` 的引擎名 | **10 个 `llama-*.dll` 保留**：临时副本里改成 `dafeiyu-*.dll` 后 `dafeiyu-server.exe --version` 返回 `0xC0000135`（STATUS_DLL_NOT_FOUND），Windows 导入表写死名字，改了本地模型就起不来。`bench_ollama.py` 测的是 Ollama（另一款软件），未改名 |
| 4 桌宠行为集中到设置 | 设置页新增「桌宠行为」组：碎碎念、点击音效、始终置顶、跟随鼠标、换装、大小、形态、主题 八项一屏；音色仍在「音频库」 | 实拍 `assets\_matting\v297-panel-04-设置.png`：八项全在，无裁切 |
| 5 动作/投喂撤出面板 | 养成页删掉动作按钮与四格零食，只留「背包 / 零食商城 / 去打工」三个入口；动作由 `care_timer` 每 60 秒判断，12~20 分钟偶发一次「现在想做哪个？」两选项气泡（12 秒不选自己随机来一个），也能语音下指令 | 实拍 `v297-panel-00-养成.png`、`v297-win-ask.png`（挥挥手 / 跳个舞 + 「不理我过一会儿自己随便来一个」） |
| 6 背包 | `state.bag` + `buy()`/`eat()`/`add_to_bag()`；饿了吃、从背包拿、投喂时不饿就存进背包；背包实体窗口点一下即吃 | 逻辑自检 5 项全 PASS：买一份进背包、扣钱、从背包吃、空包不再凭空吃、旧 `feed` 接口兼容 |
| 7 零食商城 | 新增 `app\snacks.py`：主食/肉鱼/甜点/饮品/水果/高档/新品 七类，价格硬约束 4~45 金币；「联网补货」抓新零食并记 `shop_refreshed_at`；语音「零食商城/买零食」直接呼出；入口挂在打工页底部 | 实拍 `v297-win-shop.png`（金币 120、白米饭 12、面包 7、饭团 12、泡面 15）；自检 20 项物品价格全部落在 4~45。定价基准：打工单次 5~15 金币（学习听课 15、清理 14、家务 12），最贵零食约三四次打工 |
| 8 打工语音 + 10 秒 | 「去打工/打工」→ 随机 3 个活，气泡给选项，`timeout_ms=10_000`，不点就自己随机开工；状态栏里也有「去打工」 | 代码路径 + 状态栏实拍；10 秒超时未实跑（逻辑与动作气泡同一套） |
| 9 可显现状态栏 | 饥饿/口渴/心情差/金币低于 20% 任一命中 → 大气泡状态栏：四项数值 + 打工 / 投喂 / 喝水；40 秒不理自动收起，同一需求 10 分钟冷却 | 实拍 `v297-win-status.png`（饱食 30 触发，三按钮齐全） |
| 10 按本机配置装最搭模型 | `app\hardware.py`：读显卡/显存/内存/CPU 线程，`best()` 给出推荐与理由；面板「按本机配置重新推荐」 | 实拍 `v297-panel-06-自定义模型.png`：GTX 1060 6GB / 31.9GB / 8 线程 → 推荐 DeepSeek-R1-Distill-7B（Q4） |
| 11 换硬件提醒换模型 | 启动 30 秒查一次、之后每小时一次；`diff()` 比对显存/内存/线程，有变化就在气泡里说「硬件变了：显存 6.0→12.0，我重新配成 X」 | 自检：6→12GB 被识别为「显存(GB)：6.0 → 12.0」；无变化不报 |
| 12 换硬件自动适配 | 检测到变化即写 `llm_model_recommend`、更新 `llm_model_file`，没下载就提示去「自定义模型」下载 | 同上；未在真实换卡场景验证 |
| 13 做小软件 | 新增 `app\maker.py`：语音或聊天说「做个小软件/小工具/写个脚本」→ 本地模型出代码 → 抽 ```python 块 → 静态风险检查（shell=True、os.system、格式化、删注册表、关机、反弹连接等 10 类）→ 存到 数据目录\scripts → 用户点「运行」才执行，20 秒超时、输出截断 | 自检 PASS：`os.system('del /f C:\\*')` 被判「直接调 shell」；普通 `os.path.expanduser` 脚本放行；代码块抽取正常 |
| 14 主题迁进设置 | 主题下拉并入「设置 → 桌宠行为」，切换即 `set_theme` + `apply_theme`，托盘主题子菜单保留 | 设置页实拍可见「主题 深色」下拉 |
| 版本 2.9.7 | `paths.APP_VERSION`、面板右上角、安装包文件名同步 | `dist\WhaleGirlPet.exe` 与 `dist\WhaleGirlPet-Setup-2.9.7.exe` |

## v2.9.6（2026-11-25）

本轮是用户 16 条改造清单 + 3 个补充项的落地。

| 项 | 改动 | 实测 |
|---|---|---|
| 托盘图标换成大肥鱼 | 新增 `assets/ui/pet_flat.ico`（透明底 Q 版，16–256 七种尺寸）；`main.py:_build_tray` 图标优先取它，托盘菜单「打开控制面板」也用同一张；窗口图标同步 | 启动后托盘正常显示、菜单项带图；图标文件 140,034 字节 |
| 养成页名字锁定 | 名字输入框平时 `setReadOnly(True)`，后面加「修改」「保存」两个按钮；点修改才解锁、保存才写库并锁回去；`refresh()` 加了编辑态守卫，不会把正在输的字冲掉 | 面板实拍 `assets\_matting\v296-panel-00-养成.png`：输入框可用、修改亮、保存灰 |
| 设置→自定义模型 + 新建设置页 | 原「设置」页改名「自定义模型」（留联网后端管理、自主行动、本地大模型）；另建真正的「设置」页，放关于与更新、储存位置、语音唤醒、天气资讯模块、聊天入口 | 面板实拍 `v296-panel-04-设置.png` / `v296-panel-06-自定义模型.png`，五块内容一屏放得下 |
| 定时→定时任务 | 侧栏文案与页标题统一成「定时任务」 | 实拍 `v296-panel-09-定时任务.png` |
| 语音人格→音频库 | 页名改「音频库」，顶部说明写明「换音色只换语气和口音，不动她的性格」；原「设置」页的「音频设置（本地导入）」整组迁入 | 实拍 `v296-panel-05-音频库.png`，音量/跟随系统/动作音效/导入按钮都在 |
| 性格只从聊天长 | `emotion.apply_text()`：按夸奖、凶人、撒娇想念、示弱倾诉四类线索，极小幅改情绪与性格（示弱会让她温柔 +0.7）；面板养成页只读展示「只从你们的聊天里慢慢长出来，不能手动改」 | 面板实拍首行「性格：黏人（只从你们的聊天里…）」；`py_compile` 通过 |
| 储存位置可改并整体迁移 | `paths.default_data_dir()` / `data_dir()`：数据根目录由 `%APPDATA%\WhaleGirlPet\data_root.txt` 指向，用户可迁到任意盘；设置页提供「浏览…」「迁移到这里」「打开数据目录」「迁回默认位置」，迁移做整目录复制（`shutil.copytree`），确认后重启生效 | 设置页实拍显示当前目录；迁移与改回只走文件复制，未在用户数据上实际执行 |
| 语音唤醒（改唤醒词） | 「语音说一句」按钮迁到新设置页；新增唤醒词输入框，逗号分隔最多 6 个，存 `config["wake_words_extra"]`；`wake_words()` 把它并入候选（仍自动带「你好，X」） | 设置页实拍显示「现在的叫法：大肥鱼（可再加自己的）」 |
| 天气资讯模块 | 天气开关、城市（「保存」→ `set_weather_city` 重置坐标缓存）、科技新闻开关、「现在试一条」全部收进设置页 | 实拍里城市读到当前配置「郑州」 |
| 聊天入口合并 | 右键「陪我聊聊天」与设置页「打开聊天」都落到同一个聊天页；`_goto_chat()` 同时聚焦输入框 | 实拍设置页底部一行说明 + 按钮 |
| 剪贴板先授权 | 托盘去掉「用 Tabbit 搜索剪贴板」，改为「搜索剪贴板内容（读取前先问你）」→ `ask_search_clipboard()` 弹授权框，选「同意，去搜」才读剪贴板，读完不留存 | 实拍 `assets\_matting\v296-clip-ask.png`：弹框「读取剪贴板 / 要用我剪贴板里的内容去搜一下吗？」+「同意，去搜」「不用了」；点「不用了」后校验 `search_in_browser` 调用次数 = **0**（没读剪贴板） |
| 答不上来先联网学 | `_finish_reply` 命中「不知道/查不到/没联网…」时触发 `_web_relearn`：后台线程抓 Bing 结果 → 拼进 system 提示 → 让模型用自己话重答；prompt 明确「不许整段照抄、不许列链接和来源清单」；查不到就老实说查不到 | 静态链路完整；**未联网跑真实问答验证** |
| 启动屏原生图 | `WhaleGirlPet.spec` 用 `Splash` 对象（`splash_native.png` 360×500 深色渐变卡），并把 `splash_obj.binaries` 一起塞进 EXE——Tcl 9 的 `tcl90.dll`/`tcl9tk90.dll` 不显式带上，bootloader 会报 `SPLASH: could not find requirement tcl90.dll` 并弹错 | 首版就踩了这个错（`boot_0.png` 拍到 Error 框）；补 dll 后实拍 `boot_1.png`：解压期显示深色启动卡，程序起来后自动让位给透明自绘屏 |
| 启动屏间距微调 | `splash.py` 的脚底线 402→380、点环 +26→+22、文字基线 +52→+80，人物/点环/文字不再挤在一起 | 代码改动；未重新实拍自绘屏 |
| 安装向导加第四问 | 新增「要不要顺手装个本地模型？」页（要，装一个 / 先不装）；选「要」时在 `ssPostInstall` 写 `{app}\want_local_model.flag`，程序首次启动读到标记就自动下 Qwen3-4B（下完删标记） | 实拍四页全过：`w296_p1.png`…`w296_p4c.png`；第四页副标题两次压缩才在单行放得下 |
| 安装向导右上角图彻底去掉 | `WizardSmallImageFile` 改用全透明 `art\small_blank.png` | 实拍第一页右上角既无大肥鱼也无白方块 |
| 选盘自动建目录 | 「浏览…选盘」只选到盘根（`D:\`）时自动拼 `WhaleGirlPetApp` 并 `ForceDirectories` 建好 | 代码沿用上一轮实现，本轮未改 |
| 安装 30 分钟无操作自动关 | `art\idle_close.ps1` 看门狗：系统空闲 ≥1800 秒就结束安装窗口；开始装文件后靠 `installing.flag` 立即退出，绝不杀正在安装的进程 | 编译通过；**未等满 30 分钟实测** |
| 更新每小时提醒 | 手动点「检查更新」发现新版本后开 `QTimer` 60 分钟提醒一次（托盘 + 气泡），下载完成即停；更新对话框 30 分钟无人处理自动关闭 | 代码路径完整；**未实跑一小时** |
| 清掉 dist 历史包 | 删除 2.6.0–2.9.3 全部历史安装包/portable/source/sha256 与 `dist\runtime` 副本（根目录 `runtime` 原样保留） | dist 16,934.1 MB → 143 MB；剩 `WhaleGirlPet.exe` + `WhaleGirlPet-Setup-2.9.5.exe`，之后又产出 2.9.6 安装包 |
| 版本号 2.9.6 | `paths.APP_VERSION`、iss 的 AppVersion/AppVerName/UninstallDisplayName/OutputBaseFilename/标题同步 | 面板右上角显示 `v2.9.6`；产物 `dist\WhaleGirlPet-Setup-2.9.6.exe`（86,800,952 字节） |

## v2.9.5（2026-11-25）

| 项 | 改动 | 实测 |
|---|---|---|
| 启动加载动画 | 新增 `app/splash.py`：无边框浮层画圆角卡片——鲸鱼娘立绘轻微上下浮动、标题「鲸鱼娘加载中」+ 三个呼吸点、细进度条、右下角版本号；`main()` 改为先显示它，Controller 分三步初始化（读取配置 → 加载形象与语音 → 露出桌宠），最短驻留 2 秒再淡出 | 真实桌面连拍：约 0.6 秒出现「鲸鱼娘加载中 v2.9.5 / 正在叫醒鲸鱼娘…」，约 1.3 秒开始淡出时桌宠已就位；截图 `assets\_matting\boot_1.png`、`boot_4.png` |
| 启动不再弹更新框 | 自动检查更新从 6 秒延到 20 秒，避开启动屏；`silent` 检查发现新版本时**不再弹 QMessageBox**，改发一条托盘通知，并把 `pending_update` 记进配置，装不装由用户在面板里决定 | `_on_update_result` 的 silent 分支只调 `tray.showMessage`；手动点「检查更新」仍保留对话框 |
| 对话气泡式安装向导 | 重写 `installer/whale_pet.iss`：禁用欢迎/选择目录/任务/准备四页，改成三张自定页——左侧白色气泡提问、右侧大肥鱼立绘、气泡内两个选项按钮。位置页选「就用默认位置」或「我自己挑一个」（复用被隐藏的浏览按钮，取消则原地不动）；桌面快捷方式由 `WantDesktopIcon` 控制；装完是否立刻启动由 `WantWake` 在 `ssPostInstall` 决定 | 真实运行安装包逐页点击：612×471 窗口，三页按钮都能推进到安装进度；日志 `runtime\setup_log3.txt` 记录 Installing 与用户取消回滚 |
| 右上角图标去掉圆底 | 新增 `installer/art/small.png`（Q 版鲸鱼娘、透明底），并设 `WizardSmallImageFile`，替换 Inno 由 `SetupIconFile` 派生出的圆形徽章 | 实拍：右上角只剩 Q 版角色，无圆形背景 |
| 安装页图片加载修正 | `TBitmapImage.Bitmap.LoadFromFile` 只认 BMP，直接读 PNG 会抛 `Bitmap image is not valid`；改用 `TPngImage` 加载后 `Bitmap.Assign` | 首版运行即在 `InitializeWizard` 报错（`runtime\setup_log.txt`）；改后三页立绘/气泡正常渲染 |
| 版本号 2.9.5 | `app/paths.py` 与 `installer/whale_pet.iss`（AppVersion / AppVerName / UninstallDisplayName / OutputBaseFilename）同步到 2.9.5，README 当前版本同步 | 编译产物 `dist\WhaleGirlPet-Setup-2.9.5.exe`；窗口标题 `Setup: 鲸鱼娘桌宠 2.9.5` |

## v2.9.4（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 项目迁到 F 盘 | 全部资料（含 15.57GB `runtime` 与模型库）从 `C:\Users\yangmengke\Doubao\chats\2026-11-23\new-chat\whale-girl-pet` 搬到 `F:\WhaleGirlPet`，用 robocopy 先复制不删源 | 源 1224 文件 17.03GB；目标 1302 文件 32.60GB（多出的 78 个全在 `dist\runtime`，是 F 盘原有的打包副本）。按目录核对：runtime 78/78、assets 598/598、app 40/40、tools 140/140、build 14/14 一致；`paths.runtime_dir()` 解析为 `F:\WhaleGirlPet\runtime` |
| 面板去掉「音频库」页 | 侧栏不再挂 `panel_v2.tab_audio`（动作音效/音量设置仍在「设置」页） | 侧栏 12→10 项，列表里没有「音频库」（`test_v294.py`） |
| 面板去掉「记忆知识」页 | 记忆与知识库不在面板展示；托盘新增「打开数据目录（记忆 / 知识库 / 音色缓存）」，直接打开 `accounts\default` 本地查看 | 托盘菜单出现该项；`refresh()` 里记忆段加了 `hasattr` 守卫，不再每次刷新抛异常 |
| 模型库分「已安装 / 内置」两段 | 原先只按内置目录罗列、已下载的只在行尾追加「已下载 X MB」。改为列表顶部独立「■ 已安装模型（N 个，可直接用）」分区，扫 `runtime/models/*.gguf`，非内置的自定义 gguf 也列出来；下面才是「■ 内置模型（一键下载）」 | 已安装 4 条 = 本地 4 个 gguf；分区标题顺序断言通过（`test_v294.py`） |
| 模型联网添加 | 模型库页新增输入框：贴 `.gguf` 直链或 hf-mirror 仓库页 → `model_dl.resolve_gguf_url` 解析（仓库页走 `/api/models` 挑 Q4 非 mmproj 的 gguf）→ 下载到 `runtime/models`，下完自动进「已安装」 | `hf-mirror.com/Qwen/Qwen3-4B-GGUF` → 解析出 `Qwen3-4B-Q4_K_M.gguf`；`…/x.gguf?download=true` 也能取对文件名；只接受 http(s) 与 `.gguf`，已存在不重复下 |
| 音色联网添加 + 试听 | 「语音人格」页新增音色实验台：后台线程拉微软音色库（中文排最前）→ 选音色 → 「试听选中」按当前音高/语速/音量合成播放 → 满意点「存为我的音色」写进 `config["custom_voices"]`，并与 8 个内置人格并列在人格下拉里 | 存库、下拉出现、切换生效、参数（pitch 5 / rate 3）随人格带走，5 条断言全过（`test_v294.py`） |
| 音色优化指令 | 新增 `voice_tweak.parse`：把「尖一点 / 沉一点 / 慢一点 / 快 20% / 音高 20 / 音量 60 / 默认」解析成 音高/语速/音量 三个值，逐条给出数值解释；听不懂时不动参数并提示怎么写指令 | 8 条指令逐条断言命中；「尖一点，慢 10%，音量 70」→ 滑块 (8,-10,70) |
| 修：Edge TTS 的 volume 不生效 | 同一句分别用 100% / 70% / 40% 合成，返回 mp3 字节数完全一致（23616 三次相同），确认 Edge 端音量参数对这档输出无可见影响；改为**播放端**控制：`audio_manager.play_file(path, priority, volume)` 用 `QAudioOutput.setVolume`，并延续「跟系统音量」开关 | `play_file(vol=40)` → `output.volume()==0.400`；不传 volume → 0.800（按全局音频设置 80%）；47kHz 音频正常出声 |
| 自定义音色能真的用起来 | `persona` 增加 `register_custom()` / `has()`，`get()`/`persona_index()` 合并自定义音色；`set_persona` 与 `voice_profile` 取值改走 `pers.get()`（原先写死查 `PERSONAS`，自定义音色会被拒） | `pers.get("mine_zh_CN_XiaoyiNeural")` 能读到 voice/rate/pitch |
| 项目自包含（环境进项目） | 新建项目内 `.venv`（Python 3.14.7），按 `requirements.txt` 装 PySide6 6.12.0 / edge-tts 7.3.1 / psutil 7.2.2 / pycaw 20260927，不再依赖 C 盘 chats 下的旧环境；`.gitignore` 补 `.venv/` | `.venv` 665 MB；用它跑 `test_v294.py` → ALL PASS；项目总计 33.25 GB |
| 一键启动 | 新增 `启动鲸鱼娘.bat`（pythonw 静默启动）与 `启动-查看日志.bat`（带控制台看报错） | 两个脚本按相对路径定位 `.venv`，找不到时打印建环境命令 |
| 交接文档 | 新增 `PROJECT.md`：目录地图、启动方式、面板 10 页现状、音色/模型添加步骤、数据目录、6 条已踩过的坑、测试索引、待办与迁移核对记录 | 供项目内新会话直接读，解决"新窗口看不到上次对话"的问题 |
| 版本号 2.9.4 + CI 自适配 | `app/paths.py` 的 `APP_VERSION` 与 `installer/whale_pet.iss` 四处同步到 2.9.4；CI 改为从 `paths.py` 读版本号、文件名不再写死，Release 不存在时自动 `gh release create` | 推送后 run `45435329913` 成功；Release `v2.9.4` 自动创建，6 个资产（Setup 67.29MB / portable 65.47MB / source 5.41MB + 3 个 sha256） |
| 旧副本清理 | 删除 C 盘 `whale-girl-pet`（17.03 GB）与旧 `.venv`（839 MB），删前核对「C 盘独有文件 = 0」；同时结束了占用 C 盘 dafeiyu DLL 的残留探测进程 | `C:` 剩余 798.5 → 816.0 GB（释放约 17.5 GB）；空目录壳被句柄占用暂留，重启后可 `rmdir` |
| 真实桌面目检 | 真实（非离屏）打开面板核对两页，发现音色实验台滑块右侧说明文字贴边；把提示缩短为「低 ← → 高」等三则 | 截图中文渲染正常、右上角显示 `v2.9.4`；改后滑块宽度变大、不再贴边（`assets\_matting\real-model.png` / `real-voice2.png`） |

## v2.9.3（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 修：右键托盘图标把桌宠藏了 | `tray.activated` 原先不分按键原因一律 `toggle_visibility`，右键弹菜单前先触发了一次隐藏；改为只有左键 `Trigger` 才切换 | 直接调用 `_on_tray_activated(Context)` 后 `pet.isVisible()==True`；`Trigger` 则变 False |
| 静音模式 | `_speak()` 增加 `mute_idle`：`priority=0`（闲聊、天气、新闻、自主台词）只出气泡不出声，对话回复与投喂/拍拍照常发声 | priority0 调用 TTS 次数 0；priority2 为 1；关掉静音后 priority0 恢复发声 |
| 切换类动作静默 | `SILENT_ACTIONS={"change"}`，换装动作不再播「等我换件衣服……」 | `on_action("change")` 触发 TTS 次数 0 |
| 面板改 macOS 风格 | 顶部横排标签换成左侧 `QListWidget` 侧边栏（138px）+ 右侧 `QStackedWidget`；侧栏胶囊选中态、顶部标题栏与版本号 | 侧栏 12 项、宽 138px、点选能切页；浅色与深色两套截图生成 |
| 面板数值条重做 | 原先写死 `#333` + `█░` 字符，深色主题下糊成一片；改为按主题取色的富文本色块条，低值数字标红，深色轨道提亮 | 浅色/深色放大截图各一张，文字与轨道均可辨 |
| 修：摔一跤把立绘转成横躺 | `tumble` 的 `rot` 原先是 `62 + 298*u`（一路到 360°），整张立绘在屏幕上横着躺（录屏 f_052）；限到 22° 以内的失衡摆动，保留腾空与落地压扁 | 逐帧采样 rot 峰值 22.0°、sy 最低 0.71、结束回到 idle（`test_tumble.py` ALL PASS） |
| 立绘统一（第一批） | 新增 `docs/CHARACTER.md` 作为身份母版规范；`default` / `longmaid` / `hanfu` / `sleep` 按母版重绘并替换，旧图备份在 `assets/_raw/backup_20261124` | 四张均 512 高、`alpha_min=0`，脸与母版一致 |
| 去底工具修正 | PIL 13 的 `ImageDraw.floodfill` 实测不生效（`thresh` 与种子值不匹配时静默不改像素），改为「逐行游程 + 并查集」自实现，并自动识别黑底/白底 | 黑底图透明占比 50.9%，被裙摆包围的白围裙未误伤 |
| 接外部浏览器 | 托盘新增「用 Tabbit 搜索剪贴板」：取剪贴板文本 → `QProcess.startDetached` 拉起本机 Tabbit 打开 Bing 搜索；没装则退回默认浏览器 | 探测到 `D:\Tabbit Browser\Application\Tabbit Browser.exe`；拦截调用核对 exe 路径与 URL 编码；空剪贴板不启动并给提示（`test_v293b.py` ALL PASS） |
| 开源文档 | 重写 README、新增 LICENSE（MIT + 角色二创声明）、本日志、`docs/ARCHITECTURE.md`、`docs/FEATURES.md`、`requirements.txt` | — |
| 版本号 | `paths.py`、`installer/whale_pet.iss` 四处升到 2.9.3 | — |
| 修：睡眠表情脸不一致 + 尺寸跳大 | 录屏 f_07 暴露出 `sleep.png` 是另一张圆脸、且坐姿图按图高缩放后比站姿大一整圈（窗口 466→339）。用母版脸重绘（尖耳/额前蓝宝石/闭眼眼线一致），去底后把人物重排为画布高度的 62% | 新图 303×512、`alpha_min=0`、透明 63.4%；窗口 `339×485`，与 default `314×485`、longmaid `329×485` 同量级（`test_flash.py` 无异常采样） |
| 修：双屏下桌宠"凭空消失" | `_clamp_to_screen` 原先把 `_pad` 加到右边界（上限 `scr.right()+pad`），双屏时窗口能被推到副屏；`follow` 分支也完全没有边界。改为「至少 65% 窗口留在主屏」，follow 每帧也走一次 clamp | 主屏 1920×1032 + 副屏 1440×900；推到屏外后回收，主屏内保留 65.0%；左/下边界与正常位置均不动（`test_clamp.py` ALL PASS） |
| 发布通道 | github.com 网页上传始终塞不进文件（`input#releases-upload` 是 1×1 的 `sr-only`，注入与拖放均无效），改为 GitHub Actions 在 runner 上打包并 `gh release upload` | 首次运行 9 步全绿，Release 挂上 6 个资产；CI 产物不含 `runtime/dafeiyu`，故 Setup 67.47MB < 本地 89.55MB |

### 做到一半 / 待办

- 各皮肤立绘的「脸不一致」需要统一重绘（生成批次不同），本轮未动素材。
- 果冻过渡动画（形态/换装/动作切换的插值回弹）仍未实现。
- Release v2.9.3 资产已改由 GitHub Actions 构建并上传（Setup 67.47MB / portable 65.64MB / source 5.58MB + 三个 sha256）；本地浏览器上传通道仍不通，不要再试网页拖放。

## v2.9.2（2026-11-24）

| 项 | 改动 | 实测 |
|---|---|---|
| 真人音色提炼 | `app/voice_profile.py`：B 站两段真人配音做 40ms 帧基频统计，用 Edge TTS 实测曲线反查 pitch，得 `jingjing` 363.6Hz / `linluo` 285.7Hz | 反查四组偏差 −3.3/−1.3/−0.3/+4.1 Hz；端到端 372.1Hz 对 363.6Hz 差 8.5Hz |
| 主题三档 | `app/theme.py` + `assets/ui/theme_light.qss`；托盘「主题」子菜单 | 系统浅色 → auto 解析 light；浅色下数值条清晰可读 |
| 语音唤醒词 | `wake_words()` / `_match_wake_word()`：`大肥鱼`、`你好，大肥鱼`、`你好，<角色名>` | 「今天天气怎么样」不误拦 |
| 托盘菜单合并 | 右键菜单的面板/隐藏/退出移入托盘 | 菜单项实测顺序正确 |
| 形态切换静默 | `on_form_change` 去掉语音 | 源码无 `_speak` |
| 去蒙版 + 活动余量 | 默认 `alpha_mask=False` 走真透明；`PAD_RATIO=0.18` 外扩窗口并做 pad 补偿 | 窗口 606×931 / 立绘 360×685，起跳与翻滚不裁头 |
| 发布 | Release v2.9.2 上线 4 个资产（安装包 89.56MB / portable 74.12MB / 源码 27.73MB / sha256） | `_pick_assets()` 正确挑到 Setup 与校验文件 |

## v2.9.1

- 去方形边界（`setMask` 方案，后因锯齿与裁边在 2.9.2 弃用）
- 联网更新重写：`api.github.com` latest + 分块下载 + SHA256
- 开机静默检查更新

## v2.9.0

- 天气播报（三源级联）、科技新闻、全屏自动躲避（DWM 可见边框判定）、拔电省电、右键入口

## v2.8.0

- 语音优先级抢断、自主行动权重池、夜间休息池、频繁戳抗议、脚底对齐

## v2.7.0

- 动作音效跟随语音人格（8 人格 × 20 动作共 160 条）、绿茶人格按参考视频重做

## v2.6.0 及更早

- 养成 / 打工 / 番茄钟 / 记忆知识 / 安全体检 / 多账号 / 素材与立绘多轮重做
