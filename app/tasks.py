# -*- coding: utf-8 -*-
"""打工任务定义：学习（联网知识）、满屏跑腿、摸鱼休息。

v2.3.0 起每个任务绑定一个动作（action），任务期间会循环播放，
不再只是"表情变一下、进度条在走"。
"""

TASK_DEFS = {
    "study": {
        "name": "联网听课",
        "desc": "联网学一个冷知识，读完结算经验和金币",
        "kind": "knowledge",
        "action": "look",          # 低头看书
        "duration": 30,
        "exp": 15,
        "coins": 15,
        "mood": 3,
    },
    "patrol": {
        "name": "满屏跑腿",
        "desc": "在整个屏幕上跑一圈，60 秒",
        "kind": "run",
        "action": "",              # 由 begin_run 自带奔跑动作
        "duration": 60,
        "exp": 10,
        "coins": 10,
        "mood": 2,
    },
    "stretch": {
        "name": "摸鱼休息",
        "desc": "发呆休息 45 秒，心情小幅回升",
        "kind": "rest",
        "action": "floatstep",     # 慢悠悠晃
        "duration": 45,
        "exp": 5,
        "coins": 5,
        "mood": 12,
    },
    "cleanup": {
        "name": "清理电脑垃圾",
        "desc": "扫描临时目录中 7 天以上的临时文件并安全清理，被占用的自动跳过",
        "kind": "clean",
        "action": "crab",          # 横着来回扫
        "duration": 40,
        "exp": 14,
        "coins": 14,
        "mood": 2,
    },
    "wipe": {
        "name": "擦桌面",
        "desc": "拿着抹布把桌面擦一遍，30 秒",
        "kind": "wipe",
        "action": "trot",          # 小碎步
        "duration": 30,
        "exp": 8,
        "coins": 8,
        "mood": 4,
    },
    "chores": {
        "name": "做家务",
        "desc": "整理房间、收拾杂物，50 秒，心情回升",
        "kind": "chore",
        "action": "hop",           # 一趟趟搬东西
        "duration": 50,
        "exp": 12,
        "coins": 12,
        "mood": 6,
    },
}

# 任务动作循环间隔（秒）：一个动作播完，隔这么久再播下一个循环
TASK_ACTION_GAP = 6

KNOWLEDGE_PROMPT_TOPIC = (
    "给我一个轻松有趣的知识点：海洋生物、科普冷知识、生活小常识或历史小故事，"
    "任选一个主题，2-3 句中文讲清楚，最后一句说收获。"
)
