# 网络安全资料 → 鲸鱼娘落地评估

日期：2026-11-27  
范围：`F:\数据\网络安全-攻防实战课`、`F:\数据\网络安全-文字资料（PDF版）`、`F:\数据\一些网络安全笔记`

## 结论

能落地，但只适合落到**防御侧**：安全体检、威胁识别、日志/防火墙/账号面检查、面向用户的安全知识卡。  
不适合把 Kali、漏洞利用、木马/后门、Rootkit、DDoS 等**攻击操作流程**做成桌宠可执行能力；这既超出桌宠职责，也会把项目变成攻击工具。

## 资料盘点

| 目录 | 文件 | 体积 | 主要内容 |
|---|---:|---:|---|
| 网络安全-攻防实战课 | 52 | 10.52 GB | 51 个 `.ts` 视频：网络基础、Kali 渗透、Web 安全（SQL 注入/XSS/CSRF/文件上传/命令执行） |
| 网络安全-文字资料（PDF版） | 206 | 1.22 GB | 80 个 PDF、55 个 `.doc`、44 个压缩包；覆盖 Windows 安全策略、恶意代码、Rootkit、逆向、漏洞、日志、防火墙、嗅探、无线、Web |
| 一些网络安全笔记 | 3 | 0.12 GB | 网络安全学习笔记/学习文档、Kali 常用命令 |

已抽取并核对的部分文本：

- `聊聊BypassUAC的那些段子.pdf`：UAC 完整性级别、白名单程序/DLL 劫持风险；可用于“UAC 是否被削弱”的防御检查，不接入绕过步骤。
- `Windows系列操作系统的安全配置策略.pdf`：补丁、分区、日志、ACL、关闭 RemoteRegistry、抵御 DoS 的注册表项；可直接转成只读体检项。
- `恶意代码清除与防范.pdf`：木马/病毒/蠕虫的异常端口、启动项、进程、文件关联检查；与 `guard_core` 的持久化审计方向一致。
- `网络协议欺骗攻防小结.pdf`：ARP 欺骗原理与防范；适合做“局域网异常”知识卡，不适合做发包攻击。
- `Web日志分析.pdf`：IIS/NCSA/W3C 日志字段与分析思路；适合做日志摘要/异常登录提示。
- `网络嗅探.pdf`：Sniffer Pro 抓包与网络监控；只取“流量异常识别”，不做嗅探落地。
- `防火墙.pdf` 当前 `pypdf` 报加密 trailer 错误，暂未解析；不影响已有 `secscan.firewall_status()` 的只读检查。

## 能落地的四块

### P0 安全体检（最稳）

在现有 `app/secscan.py` + 安全体检页增加**只读**检查，不改系统设置：

- UAC 是否开启（`EnableLUA`、`ConsentPromptBehaviorAdmin`）
- Defender 实时防护/杀毒/病毒库（已有）
- 防火墙三档（已有）
- RDP / RemoteRegistry / SMBv1 / Guest 账户是否暴露
- 自动播放、脚本宿主、Office 宏等高风险开关
- 事件日志大小/覆盖策略是否过小

产出：一个 0–100 分“主机防御姿态”评分，点开能看到每项证据和修复建议；修复动作只给入口，不自动改注册表。

### P1 防御规则包

在 `app/guard_core.py` 的 `DEFAULT_RULES` 增加少量高置信检测，先做三条：

- 命令行清事件日志：`wevtutil cl` / `Clear-EventLog`
- 命令行关闭防火墙：`netsh firewall ... off` / `Set-NetFirewallProfile -Enabled False`
- 脚本改写 UAC/远程桌面高风险键（只报“配置被削弱”，不报正常管理操作）

要求：每条规则必须有 `id / level / weight / scope / pattern / why`，并补 `tools/test_guard_core.py` 正反例；误报优先于漏报控制。

### P2 安全知识卡

把资料转成**原创摘要**，落到 `app/security_cards.py`（不塞原始 PDF 文本）：

- 什么是 UAC，为什么不要关
- 木马常见落地信号：异常端口、异常启动项、文件关联被改
- ARP 欺骗是什么，家里/宿舍网络怎么防
- 日志为什么不能随便清
- 防火墙三档分别管什么
- 钓鱼/弱口令/补丁/备份的最小习惯

每张卡带“来源书目/章节”，不复制整段原文，不提供攻击步骤。

### P3 学习路径索引

把课程/文字资料按阶段做成“安全学习路线”索引：网络基础 → 攻击面认知 → Web 防御 → 系统面 → 恶意代码 → 流量/DDoS → 笔记。  
只索引标题和本地路径，不把视频/PDF 打包进安装包，避免版权和体积问题；攻击面课程只列目录，不提取步骤。

## 不建议落地

- Kali 渗透、SQL 注入、文件上传木马、命令执行、DDoS、Rootkit 隐藏、UAC 绕过等**操作流程**
- 任何自动扫描/爆破/发包/提权/持久化能力
- 把课程视频或整本 PDF 塞进 `knowledge.db`（版权、体积、检索质量都不合适）

## 当前落地状态（2026-11-27 实测）

P0 的 UAC/远程面/Guest/自动播放/Office 宏/事件日志均已接成只读检查，P1 三条规则、P2 知识卡、P3 路线索引也已落到代码；仍坚持“只报不改”。

### P0 安全体检

`app/secscan.py::security_posture()`：

- UAC：`EnableLUA / ConsentPromptBehaviorAdmin / PromptOnSecureDesktop`
- RDP：`fDenyTSConnections`
- SMBv1：`mrxsmb10 Start`
- RemoteRegistry：`Start`
- Guest：`Get-LocalUser -Name Guest`，读 `Enabled`
- 自动播放：`HKCU\...\AutoplayHandlers\DisableAutoplay` + `NoDriveTypeAutoRun` 的 `0x4` 可移动盘位
- Office 宏：Word/Excel 12.0/14.0/15.0/16.0 的 `VBAWarnings / AccessVBOM`
- 事件日志：`Get-WinEvent -ListLog Security/System/Application` 读 `MaximumSizeInBytes / LogMode / RecordCount`；Security 被权限挡住时再尝试注册表 `MaxSize/Retention` 兜底

`build_report()` 已把 Guest 启用、自动播放未关、Office“启用所有宏”、Security 日志过小并入 issues；`panel.refresh_scan()` 新增对应展示。

实测：

- 真机 `UAC=开 consent=5`、`SMBv1=未安装`、`RemoteRegistry=Start 4`、`Guest=已禁用`
- 真机 `自动播放=未显式关闭`（会出一张 warn 卡，分数从 80 降到 70：RDP + 自动播放 + 日志权限提示 + 端口告警都是实际状态，不是代码误报）
- 本机未安装 Office，`office_macros.ok=False`，不硬报风险
- `Security` 日志在当前非管理员权限下读不到，界面明确显示“需要管理员权限才能读取”，不伪造数值
- `render_check` / `smoke_test` / 安全页 UI 测试均 exit 0；真实 Windows QPA 截图见 `docs/_security_posture_ui_win.png`

### P1 防御规则

`app/guard_core.py` 新增：

- H016 清事件日志：`wevtutil cl` / `Clear-EventLog`
- H017 关防火墙：`netsh ... firewall ... state off` / `Set-NetFirewallProfile -Enabled False`
- H018 削弱 UAC：`EnableLUA=0` / `ConsentPromptBehaviorAdmin=0`

`tools/test_guard_core.py` 21 条规则实测：`fw_off.cmd→H017`、`log_clear.ps1→H016`、`uac_off.cmd→H018`，干净样本 `0` 条。

### P2 安全知识卡

`app/security_cards.py` 已有 13 张防守侧卡片：

- 基础面：UAC、RDP/3389、SMBv1、Guest、自动播放、Office 宏、事件日志
- 反扒经验：木马落地信号、Rootkit 驱动/服务异常、注入的输入边界、Kali 扫描痕迹、DDoS 流量洪峰、钓鱼/弱口令
- 每张卡只有“看什么信号 / 怎么防 / 依据”，没有工具命令、payload、利用步骤
- `panel` 安全页新增“安全知识卡”按钮；体检结果也会自动带 2 张相关卡
- `tools/test_security_cards.py` 13 张卡字段完整，并断言不含 `sqlmap/msfconsole/meterpreter/mimikatz/nc -e/bash -i/hping3/loic`

### P3 学习路线索引

`app/security_learning.py` 按目录扫描：

- 01 基础 → 02 攻击面认知（只列课程标题） → 03 Web 防御 → 04 系统面 → 05 恶意代码 → 06 流量/DDoS → 07 笔记
- 实测索引 `231` 个文件 / `9,222.6 MB` / `7` 个阶段；只读文件名、路径、大小，不读 PDF/视频正文
- 安全页新增“学习路线”按钮；不把资料打包进安装包
- `tools/test_security_learning.py` 通过，输出明确写“不提供攻击步骤”

### 仍未落地 / 已知边界

- 事件日志的 `Security` 档在非管理员权限下只能提示“需要管理员权限”，无法读取真实大小；要完整检查需以管理员运行。
- 脚本宿主（WSH）、事件日志覆盖策略、Office 受保护视图等更多 P0 项还没逐一接。
- 所有修复仍只给系统设置入口，不做一键改注册表。
- 课程视频/PDF 都没打包进安装包，也没进 `knowledge.db`；P3 只是本地索引。
- “Kali/注入/木马/Rootkit/DDoS”只作为**防守识别卡**存在，不存攻击步骤，也不提供可执行工具链。

## 建议第一步

原建议已完成：P0 的 UAC/远程面/Guest/自动播放/Office 宏/日志 + P1 三条规则 + P2 卡片 + P3 索引都已接上。后续按用户提问频率补脚本宿主、日志覆盖策略和更多知识卡；仍然不做“渗透工具箱”。
