# 发布素材包（路线 1）

时间：2026-11-28

用途：把仓库从“只有代码”变成“可被外部引用”的公开项目。先发技术内容，再求反馈；不要群发、不要买 star。

## 统一链接

- 仓库：https://github.com/cnbprd/WhaleGirlPet
- 最新 Release：https://github.com/cnbprd/WhaleGirlPet/releases/tag/v3.2.0-sprite
- 演示 GIF：https://github.com/cnbprd/WhaleGirlPet/blob/main/docs/demo/whale3d-demo.gif
- 社交预览图：`docs/demo/social-preview.png`（1280×640；GitHub 仓库设置里上传）
- 路线图：https://github.com/cnbprd/WhaleGirlPet/blob/main/docs/3d-engine-roadmap-2026-11-28.md

## 中文技术帖（V2EX / 知乎 / 少数派）

标题：**我用 C++/SDL3/OpenGL 手写了一个透明 3D 桌宠：踩过的 6 个坑**

正文：

> 这是一个早期项目，不是成品软件。它是一只住在 Windows 桌面上的 3D 鲸鱼娘：窗口透明、置顶、拖拽，模型区域可点，卡面区域外点击穿透。
>
> 技术栈是 C++ + SDL3 + OpenGL 3.3 + ozz-animation + 最小 VRM 1.0。最近把 2D 表情/动作卡面接进 3D，17 张卡通过本机 UDP 触发，卡面用独立透明 overlay 窗口绘制，避免把主窗口的可点击区域撑大。
>
> 踩过的坑：
> 1. 透明窗口 + OpenGL 的合成顺序，`WS_EX_LAYERED` 和 `UpdateLayeredWindow` 不是万能解；
> 2. 点击穿透不能只靠 `HTTRANSPARENT`，最后是按模型 alpha 生成 Win32 region；
> 3. 卡面 overlay 必须单独裁 region，否则会挡住模型点击；
> 4. VRM SpringBone 的窗口位移惯性输入，和骨骼动画不是一层；
> 5. 无头固定步长回归比“肉眼看着不卡”可靠；
> 6. 安装器/升级路径比渲染更容易翻车。
>
> 当前 Release 的 exe 和安装器未签名，SmartScreen 会提示未知发布者；介意的话先看源码或只跑便携包。
>
> 如果你也在做桌面宠物/透明窗口/VRM，欢迎在 Discussions 里交流。仓库：https://github.com/cnbprd/WhaleGirlPet

## 英文 Show HN

标题：**Show HN: WhaleGirlPet – a transparent 3D desktop pet built with C++/SDL3/OpenGL**

正文：

> I built a small Windows desktop pet: a transparent, always-on-top 3D character that can be dragged around, with click-through outside the model and a separate 2D card overlay for expressions/actions.
>
> The shell is C++ + SDL3 + OpenGL 3.3, with a minimal VRM 1.0 model, ozz-animation clips, and four two-bone spring chains. The 2D card layer is a second transparent OpenGL window clipped to the card rect, so it doesn't expand the main hit-test region; clicks on the card are forwarded to the window below.
>
> It is early: the 3D body and card layer are working, but the Python cognition layer (chat/ASR/TTS) is still being migrated. The current installer and exe are unsigned, so Windows may show "Unknown publisher".
>
> Repo: https://github.com/cnbprd/WhaleGirlPet
> Release: https://github.com/cnbprd/WhaleGirlPet/releases/tag/v3.2.0-sprite
>
> I’d especially value feedback on transparent-window behavior on different Windows/GPU setups, and on the installer/upgrade path.

## Reddit（r/opensource 或 r/desktop）

标题：**WhaleGirlPet: an early open-source transparent 3D desktop pet (C++/SDL3/OpenGL)**

正文用 Show HN 的缩短版；遵守各版版规，不在多个 subreddit 同一天重复发。先看版规是否允许 self-promotion，必要时用 “Feedback Friday” 类帖子。

## B 站 / 小红书 15 秒脚本

- 0–3s：桌面右下角，角色 idle；字幕“这不是动图，是透明 3D 窗口”
- 3–6s：拖动角色；字幕“可拖拽 / 置顶 / 模型区域可点”
- 6–9s：UDP 触发 `expression/happy`；卡面出现；字幕“17 张表情/动作卡”
- 9–12s：触发 `action/wave` 或 `action/dance`；字幕“卡面是独立 overlay，不挡桌面点击”
- 12–15s：Release 页面；字幕“开源 / 未签名 / 早期项目，求反馈”
- 简介放仓库和 Release 链接；不要写“AI 女友”“擦边”这类词。

## 发布节奏

- 第 1 天：中文技术帖 1 篇 + B 站短视频 1 条
- 第 2–3 天：Show HN（工作日早上，美东时间）；同一天不发 Reddit
- 第 4–7 天：根据评论补 FAQ；把真实问题开成 issue
- 第 2 周：写“第一轮反馈修复”短文，链接回仓库

## 不要做

- 买 star / star 交换 / 互赞群
- 同一天跨多个群刷同一个链接
- 把未签名包说成“已签名”
- 用 2D 旧图冒充 3D 当前效果
- 在标题里承诺“完整 AI 伴侣/本地大模型已全部完成”

## 发布后记录

| 日期 | 渠道 | 链接 | 初始数据 | 带来的 issue/PR |
|---|---|---|---|---|
|  |  |  |  |  |
