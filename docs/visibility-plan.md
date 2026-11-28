# SignPath 路线 1：先积累公开可见度，再重新申请

时间：2026-11-28

## 目标

SignPath Foundation 拒绝的理由不是代码质量，而是“公开信任与可见度信号不足”。因此路线 1 的目标不是刷 star，而是留下**可验证的外部痕迹**：

- GitHub stars / forks / contributors
- 外部文章、独立讨论、视频或社区引用
- 持续提交与 release 记录
- 真实用户 issue / discussion

## 当前基线（2026-11-28）

| 项 | 当前 |
|---|---|
| 仓库创建 | 2026-11-24 |
| Stars / forks / watchers | 0 / 0 / 0 |
| 最新公开 Release | `v3.2.0-sprite`，2026-11-28 |
| Release 资产下载 | 3–4 次/个 |
| 仓库描述/主页/topics | 已补：3D 桌宠、SDL3、OpenGL、VRM、本地 LLM 等 16 个 topics |
| Discussions | 已开启 |
| README | 已改成“下载优先 + 3D 主线 + Star 理由” |
| SignPath | 2026-11-27 拒绝；门户无组织 |

## 90 天目标（可核验）

- 50+ stars、5+ forks、2+ 外部 contributor
- 3+ 个独立外部引用（文章、视频、社区帖，不含自述）
- 1 个演示视频，播放 500+
- 10+ 个真实 issue/discussion，至少 3 个来自非作者
- 连续 4 周有提交或 release

达到后重新申请；不要在未达到时反复提交。

## 四周执行表

### 第 1 周：把“可点开”做出来

- [x] 仓库 description / homepage / topics / discussions
- [x] README 首屏改成下载入口、3D 主线、Star 理由
- [x] 补一张真实应用截图或 10–15 秒 GIF（`docs/demo/whale3d-demo.gif`，真实运行录屏）
- [ ] 补 Release notes 的“30 秒上手”和已知限制
- [ ] 检查安装包在干净 Windows 上的首次启动（无 C 盘残留）
- [ ] 在仓库置顶一个“想要什么功能”的 Discussion

### 第 2 周：发第一轮内容

- 中文长文：`我用 C++/SDL3/OpenGL 手写了一个透明 3D 桌宠：踩过的 6 个坑`
  - 重点写透明窗口、点击穿透、VRM/SpringBone、无头回归，不写“AI 女友”
- 英文 Show HN：`Show HN: WhaleGirlPet – a transparent 3D desktop pet built with C++/SDL3/OpenGL`
- V2EX / 少数派 / 知乎择一，先发技术帖，不群发
- B 站/小红书 10–15 秒演示：角色在桌面走动 + 一张卡面 + 安装包下载口播

### 第 3 周：接反馈，做第二个 release

- 收集 issue，修 1–2 个真实用户问题
- 发 `v3.2.1` 或 `v3.3.0`，Release notes 里链接外部讨论
- 给第一个外部 contributor 的 PR 写 review；哪怕只是文档修正

### 第 4 周：整理证据，重新申请

- 统计 stars/forks/contributors、外部链接、下载量、issue 数
- 在申请表的 Reputation 栏直接贴：
  - Release 链接与下载量
  - 2–3 个外部文章/视频/讨论链接
  - issue/discussion 链接
  - 最近 4 周 commit/release 记录
- 说明上次拒绝后的改进，不争辩、不重复提交

## 渠道优先级

1. GitHub 自身：topics、README、Release、Discussions、good first issue
2. 中文技术社区：V2EX、知乎、少数派（选一个主发，其余引用）
3. 英文：Show HN、Reddit `r/opensource` / `r/desktop`（遵守版规，不跨版刷）
4. 视频：B 站、YouTube Shorts、小红书（同一素材剪不同比例）
5. 开源目录/awesome list：只提交真实可用的项目，不付钱买榜

## 禁止项

- 买 star、star 交换、批量小号、互赞群
- 把 2D 旧图冒充 3D 当前效果
- 把未签名安装包说成“已签名/已通过 SmartScreen”
- 用“AI 女友/擦边”做流量；这与项目定位和 Foundation 审核都不利

## 重新申请前的硬门槛

- 至少 50 stars，且不是短期刷出来的
- 至少 3 个独立外部引用，能点开验证
- 最近 4 周有持续提交/release
- README/Release 的安装与限制描述和实际一致
- 申请邮箱与 SignPath 账号一致
