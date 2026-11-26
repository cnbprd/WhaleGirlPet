# -*- coding: utf-8 -*-
"""安全知识卡：只写“看什么信号 + 怎么防”，不写攻击步骤、工具参数或 payload。

这些卡来自 `F:\\数据` 安全资料的防守侧摘要，面向桌宠用户；任何一条都不应
被当成渗透/入侵教程。课程标题索引由 `security_learning.py` 单独负责。
"""

CARDS = [
    {
        "id": "uac",
        "title": "UAC 不是弹窗骚扰，是最后一道确认",
        "summary": "UAC 把“普通操作”和“改系统”隔开。关掉它，等于让任何程序都能直接拿管理员权限。",
        "signals": ["EnableLUA=0", "ConsentPromptBehaviorAdmin=0（不提示直接提权）", "安全桌面提示被关闭"],
        "defense": ["保持 UAC 开启", "不把“始终不提示”当省事", "管理员操作前先确认程序来源"],
        "source": "Windows 系列操作系统的安全配置策略.pdf；聊聊 BypassUAC 的那些段子.pdf（只取防守侧）",
        "tags": ["uac", "提权"],
    },
    {
        "id": "rdp",
        "title": "3389 开着，不等于远程桌面安全",
        "summary": "RDP 暴露在公网时，弱口令、旧客户端漏洞和暴力尝试都会直接落在登录入口上。",
        "signals": ["fDenyTSConnections=0", "3389 处于监听", "公网 IP 可直接连到 RDP"],
        "defense": ["不用时关闭远程桌面", "必须用时走 VPN/白名单", "开启多因素认证并限制登录来源"],
        "source": "Windows 系列操作系统的安全配置策略.pdf；防火墙.pdf",
        "tags": ["rdp", "远程桌面", "3389"],
    },
    {
        "id": "smb1",
        "title": "SMBv1 是旧协议，不该继续开门",
        "summary": "SMBv1 缺少现代保护，历史上被蠕虫类恶意代码大量横向利用。禁用它是低成本高收益。",
        "signals": ["mrxsmb10 服务未禁用", "仍能访问旧式共享", "局域网出现异常 445 连接"],
        "defense": ["禁用 SMBv1", "共享改用 SMB2/3 并加签名", "把文件共享收进最小网段"],
        "source": "Windows 系列操作系统的安全配置策略.pdf；恶意代码清除与防范.pdf",
        "tags": ["smb1", "共享", "445"],
    },
    {
        "id": "guest",
        "title": "Guest 账户不该是“备用入口”",
        "summary": "来宾账户没有个人配置和强口令约束，启用后容易变成被忽视的入口。",
        "signals": ["Guest 账户 Enabled=True", "共享/远程登录允许 Guest", "日志出现 Guest 登录"],
        "defense": ["禁用 Guest", "共享权限去掉 Everyone/Guest", "定期核对本地账户列表"],
        "source": "Windows 系列操作系统的安全配置策略.pdf",
        "tags": ["guest", "来宾", "账户"],
    },
    {
        "id": "autoplay",
        "title": "自动播放：U 盘插上就跑的时代该结束了",
        "summary": "自动播放会让移动介质里的内容在用户没点之前就被系统处理；关闭它不牺牲正常使用。",
        "signals": ["DisableAutoplay 未设 1", "NoDriveTypeAutoRun 未屏蔽可移动盘", "插入 U 盘后自动弹窗/启动"],
        "defense": ["关闭自动播放", "移动介质先扫描再打开", "重要机器禁用未登记 U 盘"],
        "source": "Windows 系列操作系统的安全配置策略.pdf",
        "tags": ["autoplay", "自动播放", "U盘"],
    },
    {
        "id": "office",
        "title": "Office 宏和受保护视图，是一组开关",
        "summary": "“启用所有宏”把文档变成可执行入口；受保护视图被关掉，外部文档会更早进入可编辑状态。正常文档不需要无提示执行宏。",
        "signals": ["VBAWarnings=1（启用所有宏）", "AccessVBOM=1（允许程序访问宏对象）",
                    "DisableInternetFilesInPV=1（Internet 文件不进受保护视图）",
                    "DisableAttachmentsInPV=1（附件不进受保护视图）"],
        "defense": ["宏设为“禁用并提示”或“只允许签名宏”", "保持 Internet 文件/附件/不安全位置的受保护视图",
                    "不点“启用内容”除非确认来源", "外部文档先用只读方式打开"],
        "source": "Windows 系列操作系统的安全配置策略.pdf；恶意代码清除与防范.pdf",
        "tags": ["office", "宏", "vba", "受保护视图", "protected view"],
    },
    {
        "id": "wsh",
        "title": "WSH 脚本宿主：.vbs/.js 也能是入口",
        "summary": "Windows Script Host 默认可用；不需要脚本的机器，关掉它比事后查脚本更省事。",
        "signals": ["wscript.exe 存在且策略未禁用", "右键 .vbs/.js 可直接运行", "脚本从下载目录/临时目录启动"],
        "defense": ["不需要时禁用 WSH", "用 AppLocker/WDAC 限制脚本执行", "不双击来源不明的 .vbs/.js/.wsf"],
        "source": "Windows 系列操作系统的安全配置策略.pdf；恶意代码清除与防范.pdf",
        "tags": ["wsh", "windows script host", "脚本宿主", "vbs", "js"],
    },
    {
        "id": "logs",
        "title": "日志不是垃圾，是事发后的现场",
        "summary": "安全日志太小会很快覆盖；清日志本身也常是入侵收尾动作。",
        "signals": ["Security 日志上限过小", "LogMode=Circular（满了覆盖旧记录）",
                    "日志被批量清除", "登录失败/账户变更记录缺失"],
        "defense": ["把 Security 日志调到至少 20 MB", "需要留证时改为保留/集中收集",
                    "限制谁有清日志权限", "非管理员读不到 Security 日志，别把“读不到”当成“没问题”"],
        "source": "网络日志分析.pdf；Windows 系列操作系统的安全配置策略.pdf",
        "tags": ["日志", "eventlog", "security"],
    },
    {
        "id": "trojan",
        "title": "木马落地，通常先留下“持久化 + 外联”",
        "summary": "不要只盯文件名；看启动项、计划任务、服务、异常外联和签名是否对得上。",
        "signals": ["新增 Run/Startup/计划任务", "无签名 PE 从临时目录启动", "陌生进程监听高位端口", "周期性外联陌生域名"],
        "defense": ["用安全管家做只读持久化审计", "可疑文件交 Defender 深扫", "不在不明来源的程序上点“允许”"],
        "source": "恶意代码清除与防范.pdf；网络安全学习文档.pdf",
        "tags": ["trojan", "木马", "持久化", "外联"],
    },
    {
        "id": "rootkit",
        "title": "Rootkit 的防守视角：看驱动、服务和启动链",
        "summary": "Rootkit 的核心目标是隐藏自己；防守方不必掌握隐藏技巧，只要盯住内核驱动、服务和启动链的异常。",
        "signals": ["新增未知内核驱动/服务", "驱动签名与发布者对不上", "启动项/引导配置被改", "安全工具被异常终止"],
        "defense": ["保持 Secure Boot 与驱动签名校验", "启用内核隔离/驱动阻止列表", "用离线扫描和可信启动排查"],
        "source": "Rootkit 目录；恶意代码清除与防范.pdf（只取检测与防护）",
        "tags": ["rootkit", "驱动", "内核"],
    },
    {
        "id": "injection",
        "title": "注入的本质：输入被当成代码",
        "summary": "SQL 注入、命令注入、脚本注入的共同点是“用户输入越过了数据边界”。防守靠参数化、编码和最小权限。",
        "signals": ["输入里出现 SQL/脚本片段", "数据库错误信息回显到页面", "WAF 连续告警同一参数", "应用账户权限过大"],
        "defense": ["参数化查询/预编译", "输入校验与输出编码", "应用账户最小权限", "错误信息不回显"],
        "source": "Web 安全目录；Web 日志分析.pdf（只取防守侧）",
        "tags": ["injection", "注入", "web"],
    },
    {
        "id": "kali",
        "title": "Kali 是工具箱，不是攻击步骤",
        "summary": "把 Kali 当成“攻击教程”没有防守价值；真正有用的是识别扫描/枚举留下的流量和日志痕迹。",
        "signals": ["短时间大量端口/服务探测", "同一来源连续请求目录/参数", "IDS/防火墙出现扫描告警"],
        "defense": ["关闭不必要端口", "对管理面做白名单", "保留边界日志并设置告警", "只做已授权的资产自查"],
        "source": "02.Kali Linux 渗透测试 课程目录（仅索引标题，不提取操作步骤）",
        "tags": ["kali", "扫描", "枚举"],
    },
    {
        "id": "ddos",
        "title": "DDoS 是流量洪峰，不是单机技巧",
        "summary": "防守 DDoS 的重点是容量、速率限制、清洗和降级预案，而不是在本地“反击”。",
        "signals": ["上行带宽突然打满", "大量半连接/SYN 重传", "同一目标短时间超高请求", "服务延迟与丢包同时上升"],
        "defense": ["入口限速与连接数限制", "CDN/清洗服务", "关键服务做降级与熔断", "保留流量证据并联系运营商"],
        "source": "拒绝服务攻击目录；01 课程 DDoS 原理与实践（只取防守侧）",
        "tags": ["ddos", "流量", "拒绝服务"],
    },
    {
        "id": "phishing",
        "title": "钓鱼和弱口令，最后都落在“人”上",
        "summary": "再好的边界设备也挡不住用户主动交出口令；把“先验证来源”变成习惯比装更多工具有效。",
        "signals": ["登录页域名与官方不一致", "邮件要求紧急改密/扫码", "异地/异常时间登录", "同一口令被多系统复用"],
        "defense": ["重要账户开多因素认证", "口令不跨站复用", "登录前核对域名", "收到异常通知走官方入口复核"],
        "source": "个人信息安全指南（防范电信诈骗指南）；网络安全学习文档.pdf",
        "tags": ["phishing", "钓鱼", "弱口令"],
    },
]


def all_cards() -> list:
    return [dict(c) for c in CARDS]


def relevant_cards(report: dict, limit: int = 4) -> list:
    """按体检 issues 的关键词挑卡；没有命中时给 UAC/日志/钓鱼三张基础卡。"""
    text = " ".join(str(i.get("text", "")) for i in (report.get("issues") or [])).lower()
    tags = []
    for c in CARDS:
        if any(t.lower() in text for t in c["tags"]):
            tags.append(c)
    if not tags:
        tags = [c for c in CARDS if c["id"] in ("uac", "logs", "phishing")]
    return tags[:limit]


def card_text(card: dict) -> str:
    """把一张卡排成纯文本，供安全页/日志复用。"""
    return "\n".join([
        f"【{card['title']}】",
        card["summary"],
        "看什么：" + "；".join(card["signals"]),
        "怎么防：" + "；".join(card["defense"]),
        "依据：" + card["source"],
    ])
