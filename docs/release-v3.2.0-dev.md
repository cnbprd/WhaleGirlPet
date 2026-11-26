# 鲸鱼娘 3.2.0-dev（3D 核心测试包）

这是 v3.2 的预发布测试包，不是稳定版。稳定版仍是 `v3.1.2`。

## 本版内容

- 安全知识卡转规则：14 张防守知识卡映射为 `KR-*` 规则，9 条自动、5 条保留人工核对；安全页显示规则命中，真机命中 `KR-RDP-01 / KR-AUTOPLAY-01 / KR-WSH-01`，综合评分 62/100。
- ASR 单句输入：`app/asr_service.py` 默认关闭，按钮/热键显式触发一次 SAPI 录音，结束自动关闭；`voice_cmd.recognize(min_conf=0.30)` 拒绝低置信度假词。
- gaze/lean 平滑：180 ms attack / 420 ms release；`WHALE3D_SPRING=0` 下 `neutral→gaze` 60 ms 0.176 / 满值 0.712，`neutral→reset` 0.000，证明姿态层精确归零。
- reset 残差归因：默认弹簧下仍有 0.4–0.8 的整窗差，来自头发/尾巴 SpringBone 的正弦相位，不是姿态未归零；spring-off 对照已写入文档。
- 10 分钟 3D 浸泡：600 s、RSS 67.6→67.8 MB、CPU 平均 35.4% / 峰值 38.5%、FPS 平均 27.68；这是 bounded soak，不是 24 小时结论。

## 资产

| 文件 | 大小 | SHA256 |
|---|---|---|
| `whale3d-whale-girl-v3.2-dev.zip` | 2,814,755 B | `FDEFE4EAB2A17805664E4AE8DAE16CA3ADE28252D1A53650A067F564D9717B0C` |
| `WhaleGirlPet-Setup-3.2.0-dev.exe` | 4,424,684 B | `7E859016691F0816AAD5A605C4035C37E9CF9D05653EF30C183F575874A8E5FF` |

便携包已解压到干净临时目录启动：`Model springs: 4 chains, vrm=1`、2,076 三角形、`Hit mask ready: 420x620 center_alpha=255`、`fps=26.5`、退出码 0。安装器已用同一 payload 编译，内嵌 exe 的 `FileVersion/ProductVersion` 为 `3.2.0.0`；本轮未重做完整安装/卸载回归。

## 已知边界

- 5 条证据依赖规则（Rootkit / 注入 / Kali / DDoS / 钓鱼）仍需人工核对，不强行自动判。
- ASR 只覆盖单句、显式一次录音；没有连续/流式识别，也没有音素级口型。
- 10 分钟浸泡不等于 24 小时无泄漏结论。
- 安装器未签名；SmartScreen 提示时请先核对同名 `.sha256`。
- `v3.1.2` 仍是稳定版，升级前请自行备份用户数据。
