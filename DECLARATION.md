# 项目路线声明：放弃 2D 主线，转向 3D

- 项目：鲸鱼娘桌宠 / WhaleGirlPet
- 仓库：https://github.com/cnbprd/WhaleGirlPet
- 生效版本：v3.0.28（路线声明）；v3.1.0（3D 身体第一层）
- 日期：2026-11-26
- 维护者：cnbprd

## 一、结论

自 v3.0.28 起，项目主线从 **2D PySide6 桌面壳** 切换为 **3D C++17 / SDL3 / OpenGL 桌面壳**。

2D 主线已放弃：不再作为产品主线，也不再作为后续新功能和新安装包的发布目标；3D 是唯一的后续开发方向。

## 二、2D 的处理

1. **停止功能开发**：不再为 2D 壳新增功能、玩法、动画或界面改造。
2. **停止新包发布**：不再以 2D 安装包/portable 作为 Release 目标；历史安装包保留在旧 Release 中。
3. **不删除历史**：2D 源码、素材、配置兼容逻辑和历史 Release 保留在仓库/Release 中，作为归档与回滚依据。
4. **只保留阻断性修复**：若出现安全、数据损坏或无法启动等阻断问题，可做最小修复；不做功能扩展，也不承诺持续维护。
5. **不把 2D 当备选主线**：3D 遇到问题时，不回退到 2D 继续堆功能；只修 3D 或明确记录未完成项。

## 三、3D 主线当前基线

v3.0.28 的 3D 核心包已达到以下可用状态：

- 透明、无边框、置顶、非聚焦的 420×620 桌面窗口。
- 每帧 alpha mask + `WM_NCHITTEST` + `SetWindowRgn`；透明区域可穿透，角色区域可拖拽。
- OS 级真实鼠标验收：透明角落触发下层 `BN_CLICKED`；角色中心拖拽移动窗口。
- Win11 托盘图标：写入 `NotifyIconSettings\<App ID>\IsPromoted=1`，Explorer 重启后固定在任务栏。
- 原生托盘菜单、设置页、模型/动画/表情/采样器切换。
- 同进程、同窗口、同 GL context 的模型缓存：切换只换 active `Impl*`，不隐藏窗口、不重启进程、不启 helper。
- 当前包：v3.0.28 `whale3d-whale-girl-v1.zip`，2,727,089 B；SHA256 `9EB9CCAAA1B42D5CFA440E77FFB4E331A0746F6EF35A07D0843B47CE712BE461`。
- v3.1.0 起：默认角色文件为最小 VRM 1.0 `whale_girl.vrm`（351,708 B，19 humanoid bones + 4 条两骨 SpringBone）；包为 `whale3d-whale-girl-v2.zip`（2,803,800 B，SHA256 `C76621D1856F092F859D9A97BE0DE64E70C56D3988E0DD6BD4F721D3422B871E`）。
- 技术约束：不引入完整游戏引擎，不依赖 Qt/PySide6；继续使用自研 C++/SDL3/OpenGL 壳。

## 四、尚未迁移到 3D 的部分

以下能力仍留在 Python 侧，尚未进入 3D 核心包：

- `ai_profiles` 账号/模型配置。
- `_chat_cloud` 与云端 API 路由。
- 语音、记忆、知识库、安全体检等 2D 应用层能力。
- VRM MToon、expressions/BlendShape、look-at、spring colliders、blend/IK/root motion 与正式美术资产管线；当前 VRM 只是最小 humanoid + 两骨 SpringBone 子集。

因此，“转向 3D”指的是**桌面壳和渲染主线**，不是声称 2D 应用的所有云端/业务能力已经迁完。

## 五、验收边界

- 物理手点击穿透仍需用户侧最终目检；自动化验收是 OS 级 `SetCursorPos` + `mouse_event`。
- 新安装路径首次运行时，Explorer 可能尚未读取 `IsPromoted`；需要重启 Explorer 或重新登录一次。
- 3D 模型缓存当前没有 LRU/上限，模型数量增加后需要重新压测内存。
- 2D 历史安装包不再更新；需要 2D 安装包的场景只能使用旧 Release，不视为当前主线交付。

## 六、声明效力

本声明自 2026-11-26 起生效，适用于本仓库后续的路线判断、Issue 分类、Release 说明和文档默认口径。旧版本 Release 的说明是历史记录，不因本声明而追溯修改。
