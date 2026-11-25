# -*- coding: utf-8 -*-
"""
鲸鱼娘桌宠（DeepSeek 鲸鱼娘 · 大肥鱼）
PySide6 透明无边框置顶桌宠：养成 / 投喂 / 换装 / 表情 / 番茄钟 / 提醒 / 联网对话 /
改名 / 多后端管理 / 打工任务 / 自主行动 / 满屏跑 / 本地音频。
"""
import json
import os
import random
import re
import sys
import threading
import time

from PySide6.QtCore import QProcess, QSharedMemory, QTimer, Qt, QUrl
from PySide6.QtGui import (QAction, QDesktopServices, QIcon, QKeySequence,
                           QShortcut)
from PySide6.QtWidgets import (QApplication, QMenu, QMessageBox, QSystemTrayIcon)

import accounts
import ambient
import awareness
import care_ui
import companion
import emotion as emo
import hardware
import knowledge
import lines
import local_llm
import maker
import memory as mem
import model_dl
import models_catalog
import ollama_hub
import paths
import persona as pers
import snacks as snack_catalog
import splash as splash_mod
import theme
import websearch
from ai import ChatWorker, build_system_prompt, read_zhipu_key
from audio_manager import AudioManager
from cleanup import CleanWorker
from desktop_icons import IconLayout
from paths import (APP_KEY, APP_NAME, APP_VERSION, DEFAULT_NAME, FORM_DEFAULT_SKIN,
                   FORM_LABELS, SKINS, SKIN_FORM, SIZE_LEVELS, asset_path, config_file)
from pet_window import ALL_ACTIONS, PetWindow
from panel import ControlPanel
from scheduler import Scheduler
from state import PetState, SNACKS
from tasks import TASK_DEFS, KNOWLEDGE_PROMPT_TOPIC, TASK_ACTION_GAP
from tts import TTSService
from updater import DEFAULT_REPO, DownloadWorker, UpdateWorker
from usage import UsageTracker

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False


DEFAULT_CONFIG = {
    "x": None, "y": None, "scale": 1.0, "topmost": True,
    "skin": "default", "size_label": "中", "form": "mature",
    "name": DEFAULT_NAME,
    "water_on": True, "sedentary_on": True, "sound_on": True,
    "auto_on": True, "chatter_on": True,
    # v2.9.3 静音模式：没任务时（闲聊/播报/自主台词）只出气泡不出声
    "mute_idle": True,
    "update_url": "",
    # v2.9.1 联网更新：GitHub Releases（"owner/repo"）
    "update_repo": DEFAULT_REPO, "auto_update_check": True,
    # v2.9.2 去蒙版：透明合成实测无黑框，蒙版会带来锯齿与动起来被裁边，默认关闭
    "alpha_mask": False,
    # v2.9.2 主题：auto / light / dark（面板原来固定深色，浅色桌面上数值看不清）
    "theme": "auto",
    # v2.9.2 只喊唤醒词（大肥鱼/名字）时，自动接着听下一句
    "wake_then_listen": True,
    "water_interval": 45 * 60, "sedentary_interval": 60 * 60,
    "ai_profiles": [{"name": "智谱默认", "endpoint": "", "model": "", "api_key": ""}],
    "active_profile": 0,
    "ai": {"endpoint": "", "model": "", "api_key": ""},
    "audio": {"on": True, "volume": 80, "mappings": {}},
    "tasks": {"done_count": {}},
    "save": {},
    # v2.0.0 新增
    "persona": pers.DEFAULT_PERSONA,
    "tts_on": False, "tts_online": True,
    # v2.9.2 真人音色提炼：linluo（温柔少女）/ jingjing（元气少女）/ off
    "voice_profile": "linluo",
    "llm_on": True, "llm_port": local_llm.DEFAULT_PORT, "llm_ctx": 4096,
    # v3.0.4：本地模型空闲多少分钟后自动卸载（省 2.3GB 内存）；0 = 永不卸载
    "llm_idle_unload_min": 20,
    "llm_model_file": "",
    # v3.0.17：三档分工（大脑 / 快反 / 工具人）。留空 = 不强制切模型，用默认候选。
    #   brain 负责闲聊与业务理解；tool 只接代码/结构化；fast 留给"快问快答"。
    #   注意：本机 4 份 gguf 都是纯文本权重（没有 mmproj），所谓多模态只能走云端。
    #   切换模型要重启引擎（秒级到十几秒），所以 fast 默认留空，避免日常闲聊来回切。
    "model_roles": {"brain": "qwen35-4b-Q4_K_M.gguf",
                    "tool": "deepseek-coder-6.7b-instruct.gguf",
                    "fast": ""},
    "llm_backend": "auto",                      # auto / ollama / dafeiyu_cpp（旧值 llama_cpp 自动认）
    "gpu_when_idle": True,                      # 没在跑游戏时用 GPU（Ollama），跑游戏退 CPU
    "ollama_host": local_llm.OLLAMA_HOST,
    "ollama_model": local_llm.OLLAMA_DEFAULT_MODEL,
    "llm_autostart": False,
    "memory_on": True, "websearch_on": True, "kb_on": True,
    "boot_report_on": True, "boot_report_day": "",
    # v2.2.0 安全防御
    "av_on": True, "av_autoupdate": True, "av_check_day": "",
    "av_last_update": "", "skills_mock": True,
    "av_slots_done": "", "fw_check_day": "",
    "voice_on": True,
    "emotion": {},
    "schedule": {"tasks": [], "night_on": True},
    # v2.9.0 环境播报 + 体贴行为
    "weather_on": True, "weather_city": "郑州", "news_on": True,
    "ambient_interval": 90 * 60,      # 天气/新闻拉取间隔（秒），默认 90 分钟
    "fs_hide_on": True,               # 全屏应用时自动躲起来
    "power_saver_on": True,           # 拔电时暂停本地大模型
    "ambient_geo": {},                # {"lat","lon","name"} 城市坐标缓存
    # v2.9.7 第二批
    "click_sound_on": True,           # 点击音效（点她时的"噗叽"声）
    "follow_mouse": False,            # 跟随鼠标（原先只在托盘/语音里能开）
    "hw_profile": {},                 # 硬件指纹（换显卡/内存时用来提醒）
    "shop_refreshed_at": 0,           # 商城上次联网补货时间戳
    "care_quiet_until": 0,            # 状态栏/动作提问冷却到什么时候
}


class Controller:
    def __init__(self, app: QApplication, defer_show: bool = False):
        self.app = app
        # v2.9.5 启动屏：defer_show=True 时桌宠先不露脸，等初始化完由 show_pet() 统一显示
        self.defer_show = defer_show
        # 先定位当前账号，后面的配置/记忆/知识库才落在正确目录
        self.accounts = accounts.init_store()
        self.config = self._load_config()
        # 旧人格键（大马华语）自动迁移到韩语人格，避免存档里留下不存在的键
        if self.config.get("persona") in pers.LEGACY_ALIASES:
            self.config["persona"] = pers.LEGACY_ALIASES[self.config["persona"]]
        # 面板里「存为我的音色」的自定义音色，启动时注册成可用人格
        pers.register_custom(self.config.get("custom_voices"))
        self.state = PetState()
        self.state.from_dict(self.config.get("save", {}))

        self.panel = None
        self.worker = None
        self.know_worker = None
        self.clean_worker = None
        self.update_worker = None
        self.update_dl = None
        self.llm_worker = None
        self.scan_worker = None
        # v3.0.10 安全管家
        self.guard_worker = None
        self.defender_worker = None
        self.guard_report = {}
        self.icon_layout = None
        self.ollama_import = None
        self.collision_timer = None
        self.history = []

        self.audio = AudioManager(self.config)

        # ---- v2.0.0 组件 ----
        self.emotion = emo.EmotionState()
        try:
            self.emotion.from_dict(self.config.get("emotion") or {})
        except Exception:  # noqa: BLE001
            pass
        self.memory = mem.MemoryStore()
        self._init_memory_tiers()
        self.kb = knowledge.KnowledgeBase()
        self.usage = UsageTracker()
        self.tts = TTSService(self.config, self.audio)
        self.llm = local_llm.ServerManager(self.config)
        self.dl_worker = None
        self.dl_speed = 0.0
        self.sec_worker = None
        self.sign_worker = None
        self.skill_worker = None
        self._last_skill = {}
        self._security_line = ""
        self.scheduler = Scheduler(self.config)
        self.scheduler.fire.connect(self._on_schedule_fire)
        self.scheduler.night_remind.connect(self._on_night_remind)

        self.pet = PetWindow(self, show_now=not defer_show)

        # v3.0.1：首启新人礼包刚发过就立刻落盘，保证「只发一次」的标记存得住
        if getattr(self.state, "_gift_just_sent", False):
            try:
                self.save_config()
            except Exception:  # noqa: BLE001
                pass

        # ---- v2.9.7 新增窗口（用到才建，避免拖慢启动）----
        self.shop_win = None
        self.bag_win = None
        self.status_win = None
        self.ask_win = None
        self.tool_win = None
        self._care_last_beg = 0.0
        self._care_last_ask = 0.0
        self._status_shown_at = 0.0

        # ---- 定时器 ----
        self.decay_timer = QTimer()
        self.decay_timer.setInterval(30_000)
        self.decay_timer.timeout.connect(self._on_decay)
        self.decay_timer.start()

        # v2.9.8：删掉每分钟自动 +2 金币的「金币到账」节奏。
        # 一方面用户不想要那句"叮——又攒了一点金币"的语音/气泡，
        # 另一方面它一小时白送 120 金币，远超打工单次 5~15，是零食定价通胀的源头。
        # 金币现在只从打工结算来（`_finish_task` → `state.reward`）。

        self.idle_timer = QTimer()
        self.idle_timer.setInterval(90_000)
        self.idle_timer.timeout.connect(self._on_idle_talk)
        self.idle_timer.start()

        # 自主行动
        self.auto_timer = QTimer()
        self.auto_timer.setInterval(20_000)
        self.auto_timer.timeout.connect(self._on_auto)
        self.auto_timer.start()

        # ---- v2.9.7 关心节奏：状态栏 / 撒娇讨零食 / 随机动作提问 ----
        self.care_timer = QTimer()
        self.care_timer.setInterval(60_000)
        self.care_timer.timeout.connect(self._on_care_tick)
        self.care_timer.start()

        # ---- v2.9.7 硬件适配：启动 30 秒后查一次，之后每小时一次 ----
        self.hw_timer = QTimer()
        self.hw_timer.setInterval(60 * 60_000)
        self.hw_timer.timeout.connect(lambda: self._check_hardware(quiet=True))
        self.hw_timer.start()
        QTimer.singleShot(30_000, lambda: self._check_hardware(quiet=False))

        self.water_timer = QTimer()
        self.water_timer.setInterval(self.config.get("water_interval", 45 * 60) * 1000)
        self.water_timer.timeout.connect(self._on_water)
        if self.config.get("water_on", True):
            self.water_timer.start()

        self.sedentary_timer = QTimer()
        self.sedentary_timer.setInterval(self.config.get("sedentary_interval", 60 * 60) * 1000)
        self.sedentary_timer.timeout.connect(self._on_sedentary)
        if self.config.get("sedentary_on", True):
            self.sedentary_timer.start()

        # 打工任务
        self.task_active = None  # {"key", "left", "total", "fact"}
        self.task_timer = QTimer()
        self.task_timer.setInterval(1000)
        self.task_timer.timeout.connect(self._on_task_tick)

        # v2.3.0 分钟级定时：病毒库 9/12/21 点更新、防火墙每周体检
        self.minute_timer = QTimer()
        self.minute_timer.setInterval(60 * 1000)
        self.minute_timer.timeout.connect(self._on_minute)
        self.minute_timer.start()
        self.voice_worker = None
        self._last_voice = {}

        # 番茄钟
        self.tomato_left = 0
        self.tomato_timer = QTimer()
        self.tomato_timer.setInterval(1000)
        self.tomato_timer.timeout.connect(self._on_tomato_tick)

        self._build_tray()
        self._build_hotkey()
        self._check_install_model_flag()
        self._save_timer = QTimer()
        self._save_timer.setInterval(60_000)
        self._save_timer.timeout.connect(self.save_config)
        self._save_timer.start()

        # 使用统计采样（只记进程名与时长，不记窗口标题）
        self.usage_timer = QTimer()
        self.usage_timer.setInterval(self.usage.sample_sec * 1000)
        self.usage_timer.timeout.connect(self._on_usage_tick)
        self.usage_timer.start()

        # 定时任务 / 22:00 休息提醒
        self.sched_timer = QTimer()
        self.sched_timer.setInterval(30_000)
        self.sched_timer.timeout.connect(self.scheduler.tick)
        self.sched_timer.start()

        # 情绪自然衰减
        self.emotion_timer = QTimer()
        self.emotion_timer.setInterval(5 * 60_000)
        self.emotion_timer.timeout.connect(self._on_emotion_decay)
        self.emotion_timer.start()

        # ---- v2.9.0 环境播报（天气/新闻）----
        self.ambient_worker = None
        self._ambient_last = 0.0        # 上次成功拉取的时间戳
        self._ambient_cache = {}        # {"weather":{}, "news":[...], "city":""}
        self._ambient_rot = 0            # 交替说天气/新闻
        self.ambient_timer = QTimer()
        self.ambient_timer.setInterval(5 * 60_000)
        self.ambient_timer.timeout.connect(self._on_ambient_tick)
        self.ambient_timer.start()
        QTimer.singleShot(25_000, self._on_ambient_tick)

        # ---- v2.9.0 体贴行为（全屏躲避 / 拔电省电）----
        self._fs_hidden = False          # 当前是否因为全屏被自动藏起来
        self._user_hidden = False        # 用户自己点了隐藏
        self._was_battery = None         # None=还没测过
        self.guard_timer = QTimer()
        self.guard_timer.setInterval(4_000)
        self.guard_timer.timeout.connect(self._on_guard)
        self.guard_timer.start()

        QTimer.singleShot(1200, self._maybe_boot_report)
        # v2.9.5：自动检查更新从 6 秒延到 20 秒，避开启动屏和"刚开就弹框"的观感
        QTimer.singleShot(20000, self._auto_check_update)
        if self.config.get("llm_autostart"):
            QTimer.singleShot(2000, self._warm_local_llm)

    # ================= 配置 =================
    def _load_config(self):
        cfg = dict(DEFAULT_CONFIG)
        try:
            with open(config_file(), "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg.update(saved)
                cfg["ai"] = {**DEFAULT_CONFIG["ai"], **saved.get("ai", {})}
                cfg["audio"] = {**DEFAULT_CONFIG["audio"], **saved.get("audio", {})}
                cfg["tasks"] = {**DEFAULT_CONFIG["tasks"], **saved.get("tasks", {})}
                # 旧版单组配置迁移为第一套后端
                if not saved.get("ai_profiles") and saved.get("ai"):
                    cfg["ai_profiles"] = [{
                        "name": "默认",
                        "endpoint": saved["ai"].get("endpoint", ""),
                        "model": saved["ai"].get("model", ""),
                        "api_key": saved["ai"].get("api_key", ""),
                    }]
        except (OSError, ValueError):
            pass
        if not cfg["ai_profiles"]:
            cfg["ai_profiles"] = [{"name": "智谱默认", "endpoint": "", "model": "", "api_key": ""}]
        return cfg

    def save_config(self):
        self.pet.save_position()
        self.config["save"] = self.state.to_dict()
        try:
            self.config["emotion"] = self.emotion.to_dict()
        except Exception:  # noqa: BLE001
            pass
        try:
            with open(config_file(), "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    # ================= 角色名 =================
    def get_name(self) -> str:
        return (self.config.get("name") or DEFAULT_NAME).strip() or DEFAULT_NAME

    def set_name(self, name: str):
        self.config["name"] = name.strip() or DEFAULT_NAME
        self.save_config()
        self.tray.setToolTip(APP_NAME)
        self.refresh_panel()

    # ================= 后端配置 =================
    def profiles(self) -> list:
        return self.config.setdefault("ai_profiles", [])

    def active_profile(self) -> dict:
        ps = self.profiles()
        if not ps:
            ps.append({"name": "智谱默认", "endpoint": "", "model": "", "api_key": "",
                       "api_format": "openai", "models": []})
        i = self.config.get("active_profile", 0)
        i = max(0, min(i, len(ps) - 1))
        self.config["active_profile"] = i
        prof = ps[i]
        # v3.0.15：接入协议的旧数据兼容
        prof.setdefault("api_format", "openai")
        prof.setdefault("models", [])
        return prof

    def switch_profile(self, idx: int):
        if 0 <= idx < len(self.profiles()):
            self.config["active_profile"] = idx
            self.save_config()

    def save_profile_fields(self, name: str, endpoint: str, model: str, api_key: str):
        prof = self.active_profile()
        prof["name"] = name.strip() or "未命名后端"
        prof["endpoint"] = endpoint.strip()
        prof["model"] = model.strip()
        prof["api_key"] = api_key.strip()
        self.save_config()

    def new_profile(self):
        self.profiles().append({"name": f"后端 {len(self.profiles()) + 1}", "endpoint": "", "model": "", "api_key": ""})
        self.config["active_profile"] = len(self.profiles()) - 1
        self.save_config()

    def delete_active_profile(self):
        ps = self.profiles()
        if len(ps) <= 1:
            return False
        idx = self.config.get("active_profile", 0)
        ps.pop(idx)
        self.config["active_profile"] = max(0, min(idx, len(ps) - 1))
        self.save_config()
        return True

    # ================= 音频 =================
    def play_audio(self, action: str) -> bool:
        return self.audio.play(action)

    # ================= 音效（本地音频优先，失败回退蜂鸣） =================
    def beep(self, kind: str):
        # v2.9.7：点击音效单独开关（"噗叽"这一声可以关掉，其他提示音不受影响）
        if kind == "pat" and not self.config.get("click_sound_on", True):
            return
        if self.play_audio(kind):
            return
        if not self.config.get("sound_on", True) or not _HAS_WINSOUND:
            return
        try:
            if kind == "pat":
                winsound.Beep(880, 80)
            elif kind == "feed":
                winsound.Beep(660, 90); winsound.Beep(880, 120)
            elif kind == "error":
                winsound.Beep(220, 180)
            elif kind == "coin":
                winsound.Beep(1320, 60)
            elif kind == "done":
                winsound.Beep(880, 100); winsound.Beep(1175, 160)
        except RuntimeError:
            pass

    # ================= 语音 / 情绪 =================
    def _speak(self, text: str, ms: int = 2400, priority: int = 0):
        """气泡 + 可选方言语音（TTS 只合成短句，长段只显示）。
        priority：喂食/拍拍 2 > 对话回复 1 > 闲聊/自主/播报 0。
        v2.9.3 静音模式：priority 0 一律只出字不出声（没任务时不吵），
        真正有事要说（对话回复、投喂、拍拍）照常发声。"""
        self.pet.bubble.show_text(text, ms)
        if priority <= 0 and self.config.get("mute_idle", True):
            return
        if not (self.config.get("tts_on") and self.config.get("tts_online")):
            return
        if len(text) > 60:
            return
        try:
            key = self.config.get("persona", pers.DEFAULT_PERSONA)
            p = pers.get(key) or {}
            self.tts.say(pers.dialectize(text, key), p, self.emotion.voice_hint(),
                         priority=priority)
        except Exception:  # noqa: BLE001
            pass

    def set_persona(self, key: str):
        if not pers.has(key):
            return
        self.config["persona"] = key
        self.save_config()
        self._speak(f"好哒，以后就用「{pers.label(key)}」这个腔调跟你说话。", 3000)
        self.refresh_panel()

    def set_tts(self, on: bool, online: bool = True):
        self.config["tts_on"] = bool(on)
        self.config["tts_online"] = bool(online)
        self.tts.set_enabled(bool(on))
        self.save_config()

    def _on_emotion_decay(self):
        try:
            self.emotion.decay()
        except Exception:  # noqa: BLE001
            pass

    # ================= v2.9.7 零食商城 / 背包 / 状态栏 / 打工入口 =================
    def open_shop(self):
        if self.shop_win is None:
            self.shop_win = care_ui.SnackShopWindow(self)
        else:
            self.shop_win.rebuild()
        self.shop_win.show()
        self.shop_win.raise_()

    def buy_snack(self, key: str):
        ok, msg = self.state.buy(key)
        if ok:
            self.beep("feed")
            self.pet.set_expression("happy", 1800)
            # v3.0.0：第一次买进新玩具直接加一笔亲密度（参考养成游戏"买玩具"是一次性大额）
            toy = snack_catalog.by_key(key) or {}
            if toy.get("kind") == "toy":
                self.state.gain_intimacy("toy_buy")
                msg += " 她抱着新玩具不撒手了。"
        self.save_config()
        self.refresh_panel()
        return ok, msg

    def play_toy(self, key: str):
        """陪她玩背包里的玩具：v3.0.1 改成一次性消耗——玩一次就从背包里扣掉一个。"""
        toy = snack_catalog.by_key(key) or {}
        if toy.get("kind") != "toy":
            return False
        if not self.state.take_from_bag(key):
            self.pet.bubble.show_text("这个玩具已经玩完了，去商城再挑一个吧。", 2600)
            return False
        self.state.mood = min(100.0, self.state.mood + int(toy.get("mood", 8)))
        self.state.gain_intimacy("play")
        self.state.spend("play")
        self.pet.set_expression("happy", 3000)
        try:
            self.pet.do_action("hop", 2400)
        except Exception:  # noqa: BLE001
            pass
        self.beep("pat")
        left = int(self.state.bag.get(key, 0))
        tail = f"（这一个玩坏了，背包还剩 {left} 个）" if left else "（最后一个也玩坏了）"
        self._speak(f"玩玩{toy['name']}！最喜欢这个了。{tail}", 3200)
        self.save_config()
        self.refresh_panel()
        return True

    def refresh_shop_online(self):
        """联网淘新零食；返回新增列表（空列表 = 没淘到）。"""
        try:
            added = snack_catalog.fetch_online(k=6)
        except Exception:  # noqa: BLE001
            return []
        if added:
            self.config["shop_refreshed_at"] = time.time()
            self.save_config()
        return added

    def open_backpack(self, why: str = ""):
        if self.bag_win is None:
            self.bag_win = care_ui.BackpackWindow(self)
        else:
            self.bag_win.rebuild()
        self.bag_win.show()
        self.bag_win.raise_()
        if why:
            self.pet.bubble.show_text(why, 2600)

    def eat_from_bag(self, key: str):
        ok, msg = self.state.eat(key, auto_buy=False)
        if ok:
            self.emotion.apply("feed_like", 1.0)
            self.beep("feed")
            self.pet.set_expression("happy", 2200)
            self._speak(msg, 3200)
        else:
            self._speak(msg, 2600)
            if not self.state.bag_list():
                self.open_backpack(companion.empty_bag_line())
        self.save_config()
        self.refresh_panel()
        return ok, msg

    def do_drink(self):
        ok, msg = self.state.drink()
        if ok:
            self.emotion.apply("feed_like", 0.6)
            self.beep("feed")
            self.pet.set_expression("happy", 2000)
            self._speak(msg, 3000)
        else:
            self._speak(msg, 2200)
        self.save_config()
        self.refresh_panel()
        return ok, msg

    def beg_snack(self):
        """撒娇讨零食：背包有货就先吃背包里的，没货就开口讨并亮出商城。"""
        st = self.state
        bag = st.bag_list()
        if bag:
            it, _n = bag[0]
            self._speak(random.choice([
                f"背包里还有{it['emoji']}{it['name']}，我先吃一份～",
                f"翻到{it['emoji']}{it['name']}了，这个归我。",
            ]), 3000)
            return self.eat_from_bag(it["key"])
        affordable = [s for s in snack_catalog.all_items()
                      if s["cost"] <= st.coins and s["cost"] <= 25]
        snack = random.choice(affordable) if affordable else None
        self.pet.set_expression("shy", 2600)
        self.emotion.apply("pat", 0.8)
        self._speak(companion.beg_line(st, snack), 4200)
        self.open_shop()
        if not affordable:
            self.pet.bubble.show_text("不过我现在钱包空空的，先去打份工吧。", 3600)
        return (False, "beg")

    def maybe_status_bar(self, force: bool = False):
        """需求到了就亮状态栏大气泡；冷却 10 分钟，避免一直弹。"""
        kind = self.state.need_kind()
        if not kind:
            return False
        now = time.time()
        if not force and now - self._status_shown_at < 600:
            return False
        if self.status_win is None:
            self.status_win = care_ui.StatusBarWindow(self)
        self.status_win.show_need(kind)
        self._status_shown_at = now
        self._speak(companion.need_line(kind), 3000)
        return True

    def offer_work(self):
        """打工指令：给 3 个活，10 秒不点就自己随机挑一个开工。"""
        keys = random.sample(list(TASK_DEFS.keys()), min(3, len(TASK_DEFS)))
        pairs = [(k, TASK_DEFS[k]["name"]) for k in keys]
        self.pet.set_expression("curious", 2400)
        self._speak("想干哪份活？十秒没动静我就自己挑了。", 3600)
        self.ask_win = care_ui.ActionAskBubble(
            self, pairs, timeout_ms=10_000,
            title="挑一份活", tip="三个选项，10 秒没选我自己开工。",
            on_pick=self.start_task)

    def open_task_page(self):
        self.open_panel()
        try:
            self.panel.side.setCurrentRow(1)
        except Exception:  # noqa: BLE001
            pass

    def open_settings_page(self):
        """v2.9.8：右键/托盘里的「设置」统一落到侧栏第 5 项（设置页）。"""
        self.open_panel()
        try:
            self.panel.side.setCurrentRow(4)
        except Exception:  # noqa: BLE001
            pass

    def open_theme_settings(self):
        """兼容旧调用名（托盘「主题（在设置里改）」）。"""
        self.open_settings_page()

    def do_action(self, key: str):
        self.pet.do_action(key)

    def ask_action_bubble(self):
        """偶尔冒出来问一句"做哪个动作"，两个选项。"""
        pool = [a for a in ALL_ACTIONS if a not in ("change", "tumble")]
        pairs = companion.action_pairs(pool)
        if len(pairs) < 2:
            return
        self.ask_win = care_ui.ActionAskBubble(self, pairs, timeout_ms=12_000)

    def _on_care_tick(self):
        """每 60 秒看一次她现在缺什么，按情况开口。"""
        try:
            if self.panel is not None and self.panel.isVisible():
                return
            if self.task_active:
                return
            st = self.state
            now = time.time()
            if st.need_kind() and now - self._status_shown_at > 600:
                if self.maybe_status_bar():
                    return
            if st.is_hungry(50) and not st.bag_list() and now - self._care_last_beg > 600:
                if random.random() < 0.5:
                    self._care_last_beg = now
                    self.beg_snack()
                    return
            if now - self._care_last_ask > random.randint(720, 1200):
                self._care_last_ask = now
                if random.random() < 0.6:
                    self.ask_action_bubble()
        except Exception:  # noqa: BLE001
            pass

    # ================= v2.9.7 硬件适配 =================
    def _check_hardware(self, quiet: bool = True):
        try:
            info = hardware.check_and_update(self.config)
            self.save_config()
        except Exception as e:  # noqa: BLE001
            if not quiet:
                self.pet.bubble.show_text(f"硬件检测没成功：{str(e)[:40]}", 4000)
            return
        item = info.get("model")
        if info["changed"]:
            self.pet.bubble.show_text(
                "硬件变了：" + "；".join(info["changed"])
                + (f"。我重新配成 {item['name']}。" if item else "。"), 14_000)
            self._apply_model_choice(item, announce=False)
            self.pet.set_expression("curious", 4000)
        elif info["first_time"] and not quiet:
            if item:
                self._apply_model_choice(item, announce=True)

    def _apply_model_choice(self, item: dict, announce: bool = True):
        """按硬件推荐落地：记下推荐模型，没下载就提示去哪儿下。"""
        if not item:
            return
        self.config["llm_model_recommend"] = item["id"]
        if not self.config.get("llm_model_file"):
            self.config["llm_model_file"] = item["file"]
        self.save_config()
        path = os.path.join(self.models_dir(), item["file"])
        if os.path.exists(path):
            if announce:
                self.pet.bubble.show_text(f"本机最搭的是 {item['name']}，已经在硬盘里，随时能用。", 6000)
            return
        tip = (f"按本机配置推荐 {item['name']}（{item['size_mb'] / 1024:.1f}GB）："
               f"{item['note']}。要装就在「自定义模型」页点下载。")
        self.pet.bubble.show_text(tip, 12_000)
        self.panel and self.panel.append_chat("assistant", "（硬件适配）" + tip)

    # ================= v2.9.7 大肥鱼做小软件 =================
    def make_tool(self, ask: str):
        ask = (ask or "").strip()
        if not ask:
            self._speak("你要我做什么样的小工具？说一下功能就行。", 3000)
            return
        self._speak("行，我写写看——先别急着运行，等我写出来你点头。（本地模型慢的话要一两分钟）", 4200)
        messages = [{"role": "system", "content": "你是一个严谨的 Windows 小工具工程师。"},
                    {"role": "user", "content": maker.PROMPT.format(ask=ask)}]
        worker = local_llm.LocalChatWorker(self.llm, messages, max_tokens=800, temperature=0.25)
        worker.reply_ready.connect(lambda text: self._on_tool_code(ask, text))
        worker.failed.connect(lambda err: self._on_tool_failed(err))
        self.tool_worker = worker
        worker.start()

    def _on_tool_failed(self, err: str):
        self.last_tool_error = err
        self._speak(f"写代码没成（{err}）。先在「自定义模型」把本地模型跑起来再试。", 4200)

    def _on_tool_code(self, ask: str, text: str):
        code = maker.extract_code(text)
        if not code:
            self._speak("模型没给出完整代码，换个说法再试一次？", 3600)
            return
        risks = maker.check_code(code)
        path = maker.save_script(code, ask)
        if risks:
            self.pet.bubble.show_text(
                "代码写好了，但有风险点（" + "、".join(risks) + "），我先不给跑，源码在：" + path, 12_000)
            self.panel and self.panel.append_chat(
                "assistant", f"（小软件）已保存 {path}，检测到风险：{'、'.join(risks)}，未运行。")
            return
        self.panel and self.panel.append_chat("assistant", f"（小软件）已保存到 {path}")
        self._ask_run_tool(path, code)

    def _ask_run_tool(self, path: str, code: str):
        """用户点头才运行；不点就只留文件。"""
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox()
        box.setWindowTitle("要现在跑一下吗？")
        box.setText(f"脚本已存到：\n{path}\n\n只在当前目录跑，最长 20 秒。")
        box.setDetailedText(code)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        if box.exec() == QMessageBox.Yes:
            ok, out = maker.run_script(path)
            self.pet.bubble.show_text(("跑完了：" if ok else "运行出错：") + out[:300], 9000)
            self.panel and self.panel.append_chat("assistant", f"（小软件）{out[:800]}")
        else:
            self.pet.bubble.show_text("好，先放着，想跑再说。", 2600)


    def snacks(self):
        return SNACKS

    def on_pat(self):
        # v2.8：1 秒内被戳 ≥7 次就抗议一句，不再每戳都涨好感
        now = time.time()
        self._pat_ts = [t for t in getattr(self, "_pat_ts", []) if now - t < 1.0] + [now]
        if len(self._pat_ts) >= 7:
            self._pat_ts = []
            self.pet.set_expression("angry", 2600)
            self._speak("别戳了别戳了，戳坏了你赔不起。", 2600, priority=2)
            return
        self.state.pat()
        self.emotion.apply("pat", 1.2)
        self.beep("pat")
        # 40% 概率说点别的，避免每次戳都是同一句
        if random.random() < 0.4:
            self._speak(lines.pick(lines.CHAT_IDLE), 2600, priority=2)
        else:
            self._speak(lines.pick(lines.PAT), 2200, priority=2)
        self.refresh_panel()

    def on_feed(self, snack_key: str):
        """用户投喂：不饿就先收进背包，饿了才当场吃（v2.9.7）。"""
        snack = snack_catalog.by_key(snack_key)
        if not snack:
            self._speak("这个我这儿没有。", 2200)
            return
        st = self.state
        if st.is_hungry(55):
            ok, msg = st.eat(snack_key, auto_buy=True)
            if ok:
                self.emotion.apply("feed_like", 1.0)
                self.beep("feed")
                self._speak(companion.eat_line(snack), 3000)
                self.pet.set_expression("happy", 2600)
            else:
                self.emotion.apply("feed_hate", 0.8)
                self.beep("error")
                self._speak(msg, 2600)
                self.pet.set_expression("angry", 2200)
        else:
            ok, msg = st.buy(snack_key)
            if ok:
                self.emotion.apply("feed_like", 0.7)
                self.beep("feed")
                self.pet.set_expression("curious", 2200)
                self._speak(companion.bag_line(snack), 3000)
                self.open_backpack("（不饿，先收进背包）")
            else:
                self.beep("error")
                self._speak(msg, 2600)
        self.save_config()
        self.refresh_panel()


    def feed_snack(self, key: str):
        self.pet.do_feed(key)

    def on_walk(self):
        self.state.spend("walk")        # v3.0.0：散步按动作扣饱食/水分
        self.beep("walk")
        self.pet.bubble.show_text(lines.pick(lines.WALK), 2000)

    def on_run(self):
        self.state.spend("run")
        self.emotion.apply("run", 1.0)
        self.beep("walk")
        self._speak("跑起来咯——满屏溜达！", 2000)

    def on_sleep(self):
        self.beep("sleep")
        self.pet.bubble.show_text(lines.pick(lines.SLEEP), 2500)

    def on_wake(self):
        self.beep("wake")
        self.pet.bubble.show_text(lines.pick(lines.WAKE), 2000)

    def on_jump(self):
        self.state.spend("jump")
        self.pet.bubble.show_text(lines.pick(["嘿咻！", "跳高高～", "飞咯！"]), 1600)

    def on_squish(self):
        self.state.spend("squish")
        self.pet.bubble.show_text(lines.pick(["呜哇，被压扁啦！", "弹弹弹～", "噗叽～"]), 1600)

    def on_shake(self):
        self.pet.bubble.show_text(lines.pick(["抖一抖，精神抖擞！", "摇摇晃晃～"]), 1500)

    # ================= 动作体系 =================
    # v2.9.3 切换类动作不出声：换装/换形态只是"换个样子"，配一句台词反而吵
    SILENT_ACTIONS = {"change"}

    def on_action(self, key: str):
        ev = {"run": "run", "brawl": "run", "tumble": "collide",
              "eatrice": "feed_like", "hop": "run"}.get(key)
        if ev:
            self.emotion.apply(ev, 0.8)
        self.beep(key)
        if key in self.SILENT_ACTIONS:
            return
        self._speak(lines.pick(lines.ACTION_LINES.get(key, lines.HAPPY)), 2200)

    def on_panic(self):
        self.beep("panic")

    def perform_random(self):
        self.pet.do_action(random.choice(ALL_ACTIONS))

    def toggle_chatter(self, on: bool):
        self.config["chatter_on"] = bool(on)
        self.save_config()

    # ================= 满屏跑撞图标 =================
    def begin_run(self, duration_ms: int = 60000):
        # v3.0.6：满屏跑撞图标会用 LVM_SETITEMPOSITION 真的挪用户的桌面图标，
        # 每挪一次资源管理器就重排/刷新一遍，表现为"桌面/资源管理器不定时刷新"。
        # 默认改成不碰真实图标（只让桌宠自己撞、自己喊疼），要玩真格的在面板里打开开关。
        self.icon_layout = None
        if self.config.get("allow_icon_scatter", False):
            try:
                self.icon_layout = IconLayout()
                self.icon_layout.reload()
            except Exception:  # noqa: BLE001
                self.icon_layout = None
        self._collided = False
        self.pet.do_run(duration_ms)
        self._schedule_collision()

    def _schedule_collision(self):
        if self.collision_timer is not None:
            self.collision_timer.stop()
        self.collision_timer = QTimer()
        self.collision_timer.setSingleShot(True)
        self.collision_timer.timeout.connect(self._on_collision_timer)
        self.collision_timer.start(random.randint(3000, 6000))

    def _on_collision_timer(self):
        if self.pet.state != "run":
            self.icon_layout = None
            return
        center = self.pet.geometry().center()
        moved = 0
        if self.icon_layout is not None:
            moved = self.icon_layout.scatter_near(center.x(), center.y(), n=3)
        self._collided = moved > 0
        self.pet.do_panic(2600)
        self.beep("panic")
        self.pet.bubble.show_text(
            lines.pick(lines.PANIC_HIT if moved else lines.PANIC), 2400)
        QTimer.singleShot(2600, self._restore_icons)

    def _restore_icons(self):
        if self.icon_layout is not None:
            self.icon_layout.restore()
            self.icon_layout = None
        if getattr(self, "_collided", False):
            self.pet.bubble.show_text(lines.pick(lines.PANIC_DONE), 2200)
            self._collided = False

    # ================= 检查更新 =================
    def _auto_check_update(self):
        if self.config.get("auto_update_check", True):
            self.check_update(silent=True)

    def check_update(self, silent: bool = False):
        repo = str(self.config.get("update_repo", "") or "").strip()
        url = str(self.config.get("update_url", "") or "").strip()
        if not silent:
            self.panel and self.panel.set_update_status("正在检查更新……")
        self.update_worker = UpdateWorker(repo, url)
        self.update_worker.result.connect(
            lambda info, s=silent: self._on_update_result(info, s))
        self.update_worker.start()

    def _on_update_result(self, info: dict, silent: bool = False):
        status = info.get("status")
        if status != "ok":
            if silent:
                return
            msg = {"no_url": "未配置更新地址，先在设置页填写仓库或清单地址。",
                   "offline": "网络不可用，检查更新失败。",
                   "parse": "更新信息解析失败，请检查地址。",
                   "http_404": "仓库或 Release 不存在（404）。",
                   }.get(status, f"检查更新失败（{status}）。")
            self.panel and self.panel.set_update_status(msg)
            return
        if info.get("newer"):
            latest, current = info["latest"], info["current"]
            self.pet.bubble.show_text(f"有新版本 v{latest} 啦！", 4200)
            self.pet.set_expression("happy", 3000)
            brief = f"有新版本 v{latest}（当前 v{current}）。"
            self.panel and self.panel.set_update_status(brief)
            # v2.9.5 静默检查不再弹对话框：只发一条托盘通知，装不装由用户在面板里决定
            if silent:
                self.config["pending_update"] = {
                    "latest": latest, "notes": (info.get("notes") or "")[:600],
                    "setup": info.get("setup") or "", "url": info.get("url") or "",
                    "size": int(info.get("size") or 0), "sha": info.get("sha") or "",
                }
                try:
                    self.tray.showMessage(
                        APP_NAME, brief + "\n面板「设置 → 检查更新」里可以下载安装。",
                        QSystemTrayIcon.MessageIcon.Information, 6000)
                except Exception:  # noqa: BLE001
                    pass
                return
            self._arm_update_reminder(info)
            box = QMessageBox(self.panel)
            box.setIcon(QMessageBox.Information)
            box.setWindowTitle("发现新版本")
            box.setText(f"有新版本 v{info['latest']}（当前 v{info['current']}）。")
            box.setInformativeText((info.get("notes") or "暂无更新说明。")[:1200])
            dl_btn = None
            if info.get("setup") or info.get("exe"):
                size = int(info.get("size") or 0)
                label = "下载并安装" + (f"（{size / 1048576:.0f}MB）" if size else "")
                dl_btn = box.addButton(label, QMessageBox.AcceptRole)
            if info.get("url"):
                page_btn = box.addButton("打开发布页", QMessageBox.ActionRole)
                page_btn.clicked.connect(
                    lambda _=False, u=info["url"]: QDesktopServices.openUrl(QUrl(u)))
            box.addButton("以后再说", QMessageBox.RejectRole)
            # v2.9.6：30 分钟没人管就自动关，之后交给托盘每小时提醒一次
            QTimer.singleShot(30 * 60 * 1000, box.reject)
            box.exec()
            if dl_btn is not None and box.clickedButton() is dl_btn:
                self.start_update_download(info)
        else:
            msg = f"当前已是最新版本 v{info['current']}。"
            if not silent:
                self.pet.bubble.show_text("已经是最新版本啦。", 2600)
            self.panel and self.panel.set_update_status(msg)

    def _arm_update_reminder(self, info: dict):
        """v2.9.6：手动点「检查更新」发现新版本后，只要没装就每小时托盘提醒一次。"""
        self._pending_info = info
        if getattr(self, "_update_remind", None) is None:
            self._update_remind = QTimer(self.app)
            self._update_remind.setInterval(60 * 60 * 1000)
            self._update_remind.timeout.connect(self._remind_update)
        self._update_remind.start()

    def _remind_update(self):
        info = getattr(self, "_pending_info", None) or self.config.get("pending_update") or {}
        latest = info.get("latest") or "新版本"
        try:
            self.tray.showMessage(
                APP_NAME, f"还有 v{latest} 没装呢。面板「设置 → 检查更新」里可以更新。",
                QSystemTrayIcon.MessageIcon.Information, 6000)
        except Exception:  # noqa: BLE001
            pass
        self.pet.bubble.show_text(f"v{latest} 还等着你装呢～", 3000)

    def _disarm_update_reminder(self):
        t = getattr(self, "_update_remind", None)
        if t is not None:
            t.stop()

    def start_update_download(self, info: dict):
        url = info.get("setup") or info.get("exe") or ""
        name = url.split("/")[-1].split("?")[0] or "WhaleGirlPet-Setup.exe"
        if not name.lower().endswith(".exe"):
            name = "WhaleGirlPet-Setup.exe"
        self.update_dl = DownloadWorker(url, name, info.get("sha", ""))
        self.update_dl.progress.connect(self._on_update_progress)
        self.update_dl.done.connect(self._on_update_done)
        self.update_dl.failed.connect(self._on_update_failed)
        self.update_dl.start()
        self.pet.bubble.show_text("开始下载新版本，别急着关我。", 3000)

    def _on_update_progress(self, pct: int, got: int, total: int):
        mb = got / 1048576
        msg = (f"下载中 {pct}%（{mb:.1f}/{total / 1048576:.1f}MB）" if total
               else f"下载中 {mb:.1f}MB")
        self.panel and self.panel.set_update_status(msg)

    def _on_update_done(self, path: str):
        self._disarm_update_reminder()
        self.panel and self.panel.set_update_status("下载完成，准备安装。")
        box = QMessageBox(self.panel)
        box.setWindowTitle("安装新版本")
        box.setText("新版本已下载并校验通过。现在安装吗？（安装时桌宠会退出，装好后自动启动）")
        box.setInformativeText(path)
        ok = box.addButton("现在安装", QMessageBox.AcceptRole)
        box.addButton("稍后", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not ok:
            return
        self._launch_installer(path)

    def _on_update_failed(self, why: str):
        self.panel and self.panel.set_update_status(f"下载失败：{why}")
        self.pet.bubble.show_text("下载没成功，等会儿再试试。", 2800)

    def _launch_installer(self, path: str):
        try:
            if os.path.basename(path).lower().endswith(".exe"):
                QProcess.startDetached(path, ["/SILENT", "/CLOSEAPPLICATIONS",
                                             "/RESTARTAPPLICATIONS"])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
        except Exception:  # noqa: BLE001
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
            return
        # 安装器需要覆盖正在运行的 exe，先退场
        QTimer.singleShot(1200, self.quit_app)

    # ================= 外观 =================
    def set_skin(self, key: str):
        if key in SKINS:
            self.pet.set_skin(key)
            self.refresh_panel()

    def set_size(self, label: str):
        s = SIZE_LEVELS.get(label, 1.0)
        self.config["size_label"] = label
        self.pet.set_pet_scale(s)
        self.refresh_panel()

    # ================= 面板 =================
    def open_panel(self):
        if self.panel is None:
            self.panel = ControlPanel(self)
        self.panel.refresh()
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def open_panel_chat(self):
        self.open_panel()
        self.panel.chat_input.setFocus()

    def open_data_dir(self):
        """托盘入口：记忆/知识库/音色缓存都在账号数据目录里，本地直接看。"""
        try:
            d = paths.account_dir()
        except Exception:  # noqa: BLE001
            d = ""
        if not d or not os.path.isdir(d):
            self.pet.bubble.show_text("数据目录还没建出来。", 3000)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        self.pet.bubble.show_text("数据目录已打开：记忆、知识库、语音缓存都在里面。", 4200)

    def refresh_panel(self):
        if self.panel is not None:
            self.panel.refresh()

    def hide_pet(self):
        self._user_hidden = True
        self.pet.hide()
        self.tray.showMessage(APP_NAME, "桌宠已隐藏，从托盘菜单或快捷键 Alt+Shift+F 唤回。")

    # ================= 聊天（本地模型优先，云端兜底） =================
    def _chat_busy(self) -> bool:
        return bool((self.worker is not None and self.worker.isRunning()) or
                    (self.llm_worker is not None and self.llm_worker.isRunning()) or
                    (self.skill_worker is not None and self.skill_worker.isRunning()))

    def _init_memory_tiers(self):
        """v3.0.16：三层记忆。开机先做一次衰减 + 压缩，之后每轮用 core 块注入 prompt。"""
        self.memory_tiers = None
        try:
            import memory_tiers as mt
            self.memory_tiers = mt.MemoryTiers(self.memory)
            self.memory_tiers.tick_decay()
            self.memory_tiers.compress()
        except Exception:  # noqa: BLE001
            pass

    def _system_text(self, user_text: str, no_think: bool = True) -> str:
        key = self.config.get("persona", pers.DEFAULT_PERSONA)
        p = pers.get(key) or {}
        parts = [p.get("system", "").strip()]
        parts.append(f"你在跟你的主人聊天。你的名字是「{self.get_name()}」。")
        parts.append(self.emotion.to_prompt())
        if self.config.get("memory_on", True):
            # v3.0.16：三层记忆的 Core 块（预算 420 字）先注入，facts 只在这一处出现
            core = ""
            try:
                if self.memory_tiers is not None:
                    core = self.memory_tiers.core(budget=420, n_facts=8)
            except Exception:  # noqa: BLE001
                core = ""
            if core:
                parts.append(core)
            ctx = self.memory.context_block(user_text, n_recent=4, n_facts=0)
            if ctx:
                parts.append(ctx)
        if self.config.get("kb_on", True):
            ctx = self.kb.context_block(user_text, k=2)
            if ctx:
                parts.append(ctx)
        parts.append("用口语回答，2 到 4 句，不要分点罗列，不要用书面腔；不确定就说不确定。")
        if no_think:
            parts.append("/no_think")
        return "\n\n".join([x for x in parts if x])

    def _build_messages(self, user_text: str) -> list:
        msgs = [{"role": "system", "content": self._system_text(user_text, True)}]
        if self.config.get("memory_on", True):
            msgs.extend(self.memory.recent(6))
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def send_chat(self, text: str, attach: list | None = None, show: bool = True):
        """统一聊天入口：用户气泡只在这里画一次，避免面板和控制器各画一遍。

        v3.0.0：面板「发送」和语音都走这里，show=False 表示气泡已由调用方画好；
        attach 是本地附件列表，只注入路径，不上传内容。
        """
        text = (text or "").strip()
        attach = [f for f in (attach or []) if f]
        if not text and not attach:
            return
        self._web_retry_done = False
        if self._chat_busy():
            self.panel and self.panel.set_chat_status(f"{self.get_name()}还在想上一句……")
            return
        # ---- 气泡：附件逐个一条，文字只挂在第一条上，避免重复 ----
        if show and self.panel is not None:
            try:
                if attach:
                    for i, f in enumerate(attach):
                        self.panel.append_chat("user", text if i == 0 else "", attachment=f)
                elif text:
                    self.panel.append_chat("user", text)
            except Exception:  # noqa: BLE001
                pass
        # ---- 附件转成文字注入（每条一次，不再按附件重复追加原文） ----
        ask_text = text
        if attach:
            parts = []
            for f in attach:
                kind = ("图片" if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))
                        else "文件")
                parts.append(f"（用户发来{kind}：{os.path.basename(f)}，路径 {f}）")
            ask_text = ("，".join(parts) + ("，" + text if text else "")).strip()
        self.history.append({"role": "user", "content": ask_text})
        self.panel and self.panel.set_chat_status("思考中……")
        self.pet.set_expression("curious", 4000)
        if self.config.get("memory_on", True):
            try:
                self.memory.add_message("user", text)
                for k, v in mem.extract_facts(text):
                    self.memory.add_fact(k, v)
            except Exception:  # noqa: BLE001
                pass
        self.emotion.apply_text(text)      # v2.9.6：聊什么都能让性格慢慢长一点
        self.emotion.apply("chat", 1.0)

        import skills as sk
        blocked, why = sk.guard(ask_text)
        if blocked:
            self._finish_reply("这个操作要删东西或者动磁盘，我不做。要不要我帮你把文件挪到回收站？",
                               "安全前置拦截")
            return
        if (self.config.get("llm_on", True) and local_llm.available(self.config)
                and sk.looks_like_command(ask_text)):
            try:
                self.skill_worker = local_llm.LocalChatWorker(
                    self.llm, self._router_messages(ask_text), max_tokens=180,
                    temperature=0.1, fmt="json", role="tool")
                self.skill_worker.reply_ready.connect(
                    lambda raw: self._on_skill_route(raw, ask_text))
                self.skill_worker.failed.connect(lambda r: self._chat_plain(ask_text))
                self.skill_worker.start()
                return
            except Exception:  # noqa: BLE001
                pass
        self._chat_plain(ask_text)

    def _router_messages(self, text: str) -> list:
        sys = ("你是指令解析器，只输出一个 JSON 对象，不要任何解释文字。\n"
               "可用 skill 只有这 4 个：\n"
               "1 set_reminder：设提醒，必填 time、content；可选 repeat、priority。\n"
               "2 check_weather：查天气，必填 city；可选 date。\n"
               "3 open_file：打开文件，必填 path；可选 mode（只读 或 编辑）。\n"
               "4 chat：普通闲聊，必填 reply（一句话回复）。\n"
               '输出格式：{"skill":"set_reminder","parameters":{"time":"...","content":"..."}}\n'
               "用户的话没有明确要办的事，就用 chat。不要编造不存在的 skill。\n"
               "时间原样保留用户说法（例如「明天七点」），不要改年份。")
        return [{"role": "system", "content": sys},
                {"role": "user", "content": text}]

    def _on_skill_route(self, raw: str, text: str):
        import skills as sk
        try:
            res = sk.handle(raw, text, mock=bool(self.config.get("skills_mock", True)))
        except Exception:  # noqa: BLE001
            res = {"ok": False, "reason": "handler_crash", "say": ""}
        self._last_skill = res
        if res.get("ok"):
            self.panel and self.panel.set_chat_status(
                "能力层：" + str(res.get("skill")))
            self._finish_reply(res.get("say") or "记下了。",
                               "能力层·" + str(res.get("skill")))
            return
        # 拦截/不合法 → 退回普通对话，不硬顶
        self.panel and self.panel.set_chat_status(
            "能力层拒了（%s），回普通对话" % res.get("reason", ""))
        self._chat_plain(text)

    # 代码类请求的识别词。v3.0.17 收紧过一次：去掉「异常」「bug」这类日常也常说的词
    #   （实测：切到 6.7B 要 23.6s、单轮 6.5s，误触发一次代价很大）。
    CODE_HINTS = ("报错", "错误信息", "traceback", "Traceback", "SyntaxError",
                  "Exception", "这段代码", "代码", "函数", "编译", "正则",
                  "写个脚本", "重构", "单元测试", "pandas", "numpy", "SQL", "sql")

    def _looks_like_code(self, text: str) -> bool:
        t = str(text or "")
        return any(h in t for h in self.CODE_HINTS)

    def _chat_plain(self, text: str):
        if self.config.get("llm_on", True) and local_llm.available(self.config):
            try:
                role = "tool" if self._looks_like_code(text) else "brain"
                if role == "tool":
                    # 换模型 = 重启引擎，实测 23.6s，先告诉用户不是在卡死
                    self.pet.bubble.show_text("我要把专写代码的那个脑子叫醒，得等十几二十秒…", 6000)
                self.llm_worker = local_llm.LocalChatWorker(
                    self.llm, self._build_messages(text), max_tokens=260,
                    temperature=0.8, role=role)
                self.llm_worker.reply_ready.connect(self._on_local_reply)
                self.llm_worker.failed.connect(self._on_local_failed)
                self.llm_worker.start()
                return
            except Exception:  # noqa: BLE001
                pass
        self._chat_cloud(text)

    def _chat_cloud(self, text: str):
        prof = self.active_profile()
        if not (prof.get("api_key") or read_zhipu_key()):
            self._on_ai_failed("no_key")
            return
        self.worker = ChatWorker(
            endpoint=prof.get("endpoint", ""), model=prof.get("model", ""),
            api_key=prof.get("api_key", ""), history=self.history, user_text=text,
            system_prompt=self._system_text(text, False),
            api_format=prof.get("api_format", "openai"),
            proxy=prof.get("proxy", ""), extra_headers=prof.get("headers", ""),
            params_override=prof.get("params", ""))
        self.worker.reply_ready.connect(self._on_ai_reply)
        self.worker.failed.connect(self._on_ai_failed)
        self.worker.start()

    def _on_local_reply(self, content: str):
        self._finish_reply(content, "本地 Qwen3")

    def _on_local_failed(self, reason: str):
        self.panel and self.panel.set_chat_status(f"本地模型没答上来（{reason}），换云端试试……")
        text = self.history[-1]["content"] if self.history else ""
        prof = self.active_profile()
        if prof.get("api_key") or read_zhipu_key():
            self._chat_cloud(text)
        else:
            self._on_ai_failed(f"local_{reason}")

    def _polish_reply(self, text: str) -> str:
        """v3.0.14：把模型输出里那些「乱」的东西收掉，只留人话。

        处理六类：markdown 记号、代码块、列表符号/小标题、链接地址、
        整句复读、多余空白与残破标点；顺带剥掉 assistant: 这类前缀。
        只做清字，不改语义，清洗后的文本同时用于气泡、聊天记录和 TTS。
        """
        t = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        t = re.sub(r"^\s*(?:assistant|user|bot|AI|Reply|Answer)\s*[:：]\s*", "", t, flags=re.I)
        t = re.sub(r"```.*?```", " ", t, flags=re.S)
        t = re.sub(r"`([^`\n]{0,60})`", r"\1", t)
        t = re.sub(r"\*\*([^*\n]{1,80})\*\*", r"\1", t)
        t = re.sub(r"\*([^*\n]{1,80})\*", r"\1", t)
        t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)
        t = re.sub(r"^\s{0,3}(?:[-+*•·]|\d{1,2}[.、)])\s+", "", t, flags=re.M)
        t = re.sub(r"\[([^\]\n]{1,60})\]\((?:https?://|www\.)[^)\n]*\)", r"\1", t)
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"^\s{0,3}>\s*", "", t, flags=re.M)
        t = re.sub(r"^\s*[-—=]{3,}\s*$", "", t, flags=re.M)
        t = re.sub(r"\n\s*\n+", "\n", t)
        t = re.sub(r"[ \t\u3000]{2,}", " ", t)
        # 整句复读：同一句连着三遍以上，折成一遍
        t = re.sub(r"([^\n。！？!?]{3,30}[。！？!?])(?:\s*\1){2,}", r"\1", t)
        # 半截括号/引号收尾、结尾挂着的逗号
        t = re.sub(r"([「『（(\[【])\s*$", "", t, flags=re.M)
        t = re.sub(r"[，、,;；]\s*$", "。", t)
        # 短回复（<=100 字）把换行也抹平：气泡里本来就是一段话，分行只会显得碎
        t = t.strip()
        if len(t) <= 100:
            t = re.sub(r"\n+", " ", t).strip()
        return t

    def _finish_reply(self, content: str, source: str = ""):
        content = self._polish_reply(content)
        if not content:
            self._on_ai_failed("empty")
            return
        # v2.9.6：答不上来 → 先联网学一遍，再用她自己的话重答（不照搬）
        if self._needs_web_relearn(content):
            q = self.history[-1]["content"] if self.history else ""
            self._web_relearn(q, content)
            return
        self.history.append({"role": "assistant", "content": content})
        if self.config.get("memory_on", True):
            try:
                self.memory.add_message("assistant", content)
            except Exception:  # noqa: BLE001
                pass
        self.state.chat_bonus()
        self.emotion.apply("chat", 1.0)
        self.panel and self.panel.append_chat("assistant", content)
        self.panel and self.panel.set_chat_status(source)
        self._speak(content, 4200)
        self.pet.set_expression("happy", 3000)
        self.beep("chat")
        self.refresh_panel()

    def _on_ai_reply(self, content: str):
        self._finish_reply(content, "云端")

    # ---------- v2.9.6 答不上来先联网学 ----------
    WEB_MISS_HINTS = ("不知道", "不清楚", "不确定", "查不到", "没查到", "没有联网",
                      "无法获取", "无法回答", "不太了解", "没听说过", "我没法", "我无法")

    def _needs_web_relearn(self, content: str) -> bool:
        if not self.config.get("websearch_on", True):
            return False
        if getattr(self, "_web_retry_done", False):
            return False
        q = self.history[-1]["content"] if self.history else ""
        if not q or len(q) < 2:
            return False
        return any(h in (content or "") for h in self.WEB_MISS_HINTS)

    def _web_relearn(self, question: str, draft: str):
        """上网查一遍，回来后用自己的话重答；查不到就老实说查不到。"""
        import threading

        self._web_retry_done = True
        self.panel and self.panel.set_chat_status("这句我答不上来，先上网学一下……")
        self.pet.set_expression("curious", 4000)

        def work():
            try:
                ctx = websearch.context_block(question, k=5, max_chars=1100)
            except Exception:  # noqa: BLE001
                ctx = ""
            QTimer.singleShot(0, lambda: self._after_web_relearn(question, ctx, draft))

        threading.Thread(target=work, daemon=True).start()

    def _after_web_relearn(self, question: str, ctx: str, draft: str):
        if not ctx:
            self._finish_reply("我上网查了一圈也没找到靠谱说法，这个我真说不准，不瞎编。", "联网学习失败")
            return
        sys_prompt = (
            self._system_text(question, False).replace("/no_think", "").strip()
            + "\n\n" + ctx
            + "\n\n注意：上面只是参考资料，必须换成你自己的话、用 2 到 4 句口语讲清楚；"
              "不许整段照抄，不许罗列标题、链接或来源清单；资料打架时以更新的那条为准。"
        )
        prof = self.active_profile()
        if prof.get("api_key") or read_zhipu_key():
            self.worker = ChatWorker(
                endpoint=prof.get("endpoint", ""), model=prof.get("model", ""),
                api_key=prof.get("api_key", ""), history=self.history, user_text=question,
                system_prompt=sys_prompt)
            self.worker.reply_ready.connect(lambda c: self._finish_reply(c, "联网学习后作答"))
            self.worker.failed.connect(lambda r: self._finish_reply(draft, "本地草稿"))
            self.worker.start()
            return
        if self.config.get("llm_on", True) and local_llm.available(self.config):
            try:
                self.llm_worker = local_llm.LocalChatWorker(
                    self.llm,
                    [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": question}],
                    max_tokens=260, temperature=0.6)
                self.llm_worker.reply_ready.connect(lambda c: self._finish_reply(c, "联网学习后作答"))
                self.llm_worker.failed.connect(lambda r: self._finish_reply(draft, "本地草稿"))
                self.llm_worker.start()
                return
            except Exception:  # noqa: BLE001
                pass
        self._finish_reply(draft, "本地草稿")

    def _on_ai_failed(self, reason: str):
        fallback = {
            "no_key": lines.pick(lines.NO_KEY),
            "offline": lines.pick(lines.OFFLINE),
            "http_401": "密钥好像不对，去设置页检查一下 API Key。",
            "http_429": "问的人太多啦，本鱼被限流了，稍后再试。",
        }.get(reason, "本鱼没接上话，先陪你扯两句。")
        self.history.append({"role": "assistant", "content": fallback})
        if self.config.get("memory_on", True):
            try:
                self.memory.add_message("assistant", fallback)
            except Exception:  # noqa: BLE001
                pass
        self.emotion.apply("task_fail", 0.6)
        self.panel and self.panel.append_chat("assistant", fallback)
        self.panel and self.panel.set_chat_status(f"没连上（{reason}），已用本地台词。")
        self._speak(fallback, 3000)
        self.pet.set_expression("sleepy", 3000)
        self.beep("error")

    def save_ai_settings(self):
        if self.panel is None:
            return
        card = getattr(self.panel, "api_card", None)
        if card is not None:
            card._save()
            return
        self.save_profile_fields(
            self.panel.ed_profile_name.text(),
            self.panel.ed_endpoint.text(),
            self.panel.ed_model.text(),
            self.panel.ed_key.text())
        self.panel.lbl_ai_status.setText("已保存当前后端。")

    def test_ai_connection(self):
        self.save_ai_settings()
        prof = self.active_profile()
        card = getattr(self.panel, "api_card", None) if self.panel else None
        if not (prof.get("api_key") or read_zhipu_key()):
            if card is not None:
                card.set_connected(False, "未检测到 API Key。")
            return
        if card is not None:
            card.lbl_status.setText("正在测试连接……")
        self.worker = ChatWorker(prof.get("endpoint", ""), prof.get("model", ""),
                                 prof.get("api_key", ""), [], "只回复两个字：连通",
                                 system_prompt=build_system_prompt(self.get_name()),
                                 api_format=prof.get("api_format", "openai"),
                                 proxy=prof.get("proxy", ""),
                                 extra_headers=prof.get("headers", ""),
                                 params_override=prof.get("params", ""))

        def _ok(c):
            if card is not None:
                card.set_connected(True, f"连接成功：{c[:20]}")
            elif self.panel:
                self.panel.lbl_ai_status.setText(f"连接成功：{c[:20]}")

        def _bad(r):
            if card is not None:
                card.set_connected(False, f"连接失败：{r}")
            elif self.panel:
                self.panel.lbl_ai_status.setText(f"连接失败：{r}")

        self.worker.reply_ready.connect(_ok)
        self.worker.failed.connect(_bad)
        self.worker.start()

    # ================= 形态切换 =================
    def set_form(self, form: str):
        self.pet.set_form(form)

    def on_form_change(self, form: str, skin: str):
        # v2.9.2 形态切换不再语音播报：切换频繁时太吵，也会打断正在说的话
        self.save_config()
        self.refresh_panel()

    # ================= 账号（本地多档案） =================
    def account_list(self) -> list:
        return self.accounts.all()

    def account_name(self) -> str:
        try:
            return self.accounts.current().get("name", "默认")
        except Exception:  # noqa: BLE001
            return "默认"

    def new_account(self, name: str, copy_current: bool = False) -> bool:
        try:
            info = self.accounts.create(name, self.accounts.current_slug() if copy_current else "")
        except Exception:  # noqa: BLE001
            return False
        self.refresh_panel()
        return bool(info)

    def rename_account(self, slug: str, name: str) -> bool:
        ok = self.accounts.rename(slug, name)
        self.refresh_panel()
        return ok

    def delete_account(self, slug: str) -> bool:
        ok = self.accounts.delete(slug)
        self.refresh_panel()
        return ok

    def switch_account(self, slug: str) -> bool:
        if slug == self.accounts.current_slug():
            return True
        self.save_config()                    # 先把旧账号存盘
        if not self.accounts.activate(slug):
            return False
        try:
            self.memory.close()
        except Exception:  # noqa: BLE001
            pass
        self.config = self._load_config()
        self.state = PetState()
        self.state.from_dict(self.config.get("save", {}))
        self.emotion = emo.EmotionState()
        try:
            self.emotion.from_dict(self.config.get("emotion") or {})
        except Exception:  # noqa: BLE001
            pass
        self.memory = mem.MemoryStore()
        self._init_memory_tiers()
        self.kb = knowledge.KnowledgeBase()
        self.usage = UsageTracker()
        self.audio = AudioManager(self.config)
        self.tts = TTSService(self.config, self.audio)
        self.llm.config = self.config
        self.scheduler.config = self.config
        self.history = []
        self.pet.base = self.pet._load_skin(self.config.get("skin", "default"))
        self.pet.restore_base_expression()
        self.pet._update_pix()
        self.refresh_panel()
        self._speak(f"切到「{self.account_name()}」啦。", 2600)
        return True

    # ================= 使用统计 / 开机播报 =================
    def _on_usage_tick(self):
        try:
            self.usage.tick()
            self.usage.save()
        except Exception:  # noqa: BLE001
            pass

    def yesterday_report(self) -> str:
        try:
            return self.usage.report_text(self.usage.yesterday_key())
        except Exception:  # noqa: BLE001
            return ""

    def _maybe_boot_report(self):
        # 每天一次病毒库过期检查：独立于早报是否已播
        self._maybe_update_signatures()
        if not self.config.get("boot_report_on", True):
            return
        try:
            today = self.usage.today
            if self.config.get("boot_report_day") == today:
                return
            text = self.usage.report_text(self.usage.yesterday_key())
            self.config["boot_report_day"] = today
            self.save_config()
        except Exception:  # noqa: BLE001
            return
        if text:
            self.pet.bubble.show_text("昨天你的电脑是这么用的：\n" + text, 9000)
            self.pet.set_expression("curious", 4000)
        # 病毒防御与拦截信息：异步取，避免卡开机
        if self.config.get("av_on", True):
            try:
                import secscan
                self.sec_worker = secscan.SummaryWorker()
                self.sec_worker.done.connect(self._on_boot_security)
                self.sec_worker.start()
            except Exception:  # noqa: BLE001
                pass

    def _on_boot_security(self, summary: str):
        if not summary:
            return
        self._security_line = summary
        try:
            log = os.path.join(paths.runtime_dir(), "boot.log")
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "security": summary}, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass
        self.pet.bubble.show_text("病毒防御：" + summary, 8000)
        self.pet.set_expression("happy", 3000)
        self.refresh_panel()

    def security_line(self) -> str:
        return getattr(self, "_security_line", "")

    def _maybe_update_signatures(self):
        if not self.config.get("av_autoupdate", True):
            return
        try:
            import secscan
            today = self.usage.today
            if self.config.get("av_check_day") == today:
                return
            av = secscan.av_health()
            self.config["av_check_day"] = today
            self.save_config()
            if not av.get("ok") or av.get("stale"):
                self.update_signatures(silent=True)
        except Exception:  # noqa: BLE001
            pass

    def update_signatures(self, silent: bool = False) -> bool:
        if self.sign_worker is not None and self.sign_worker.isRunning():
            return False
        try:
            import secscan
            self.sign_worker = secscan.UpdateWorker()
            self.sign_worker.done.connect(
                lambda ok, msg: self._on_sign_done(ok, msg, silent))
            self.sign_worker.start()
            return True
        except Exception:  # noqa: BLE001
            return False

    def _on_sign_done(self, ok: bool, msg: str, silent: bool):
        self.config["av_last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save_config()
        if ok:
            text = "病毒库已更新到最新。"
        else:
            text = "病毒库更新没成功：" + (msg[:60] or "未知原因")
        if not silent:
            self.pet.bubble.show_text(text, 5000)
            self.refresh_panel()

    # ---------- v2.3.0 定时：病毒库 9/12/21 点、防火墙每周 ----------
    AV_SLOTS = ("09:00", "12:00", "21:00")
    FW_NAMES = {"Domain": "域网络", "Private": "专用网络", "Public": "公用网络"}

    def _on_minute(self):
        now = time.strftime("%H:%M")
        today = time.strftime("%Y-%m-%d")
        if now in self.AV_SLOTS:
            stamp = f"{today} {now}"
            if self.config.get("av_slots_done") != stamp:
                self.config["av_slots_done"] = stamp
                self.save_config()
                self.pet.bubble.show_text(f"到 {now} 了，我去更新一次病毒库。", 4000)
                self.update_signatures(silent=True)
        self._maybe_firewall_weekly()
        self._maybe_unload_local_model()

    def _maybe_unload_local_model(self):
        """v3.0.4：本地 4B 模型常驻要吃 2.3GB。空闲超过 llm_idle_unload_min 分钟就卸掉，
        下次要用再按需拉起（首次约 8–15 秒）。设 0 表示永不卸载。"""
        try:
            limit = float(self.config.get("llm_idle_unload_min", 20) or 0)
            if limit <= 0:
                return
            self.llm.config = self.config
            if self.llm.should_unload(limit):
                mins = int(self.llm.idle_minutes())
                self.llm.stop()
                # 只在面板开着的时候提示，免得平时乱弹
                if self.panel is not None and self.panel.isVisible():
                    self.pet.bubble.show_text(
                        f"本地模型闲着 {mins} 分钟了，我先卸载腾出内存，下次要用再叫醒它。", 4000)
        except Exception:  # noqa: BLE001
            pass

    def _maybe_firewall_weekly(self):
        """每 7 天体检一次防火墙（只读，不改任何开关）。"""
        if not self.config.get("av_on", True):
            return
        today = time.strftime("%Y-%m-%d")
        last = str(self.config.get("fw_check_day") or "")
        if last:
            try:
                import datetime as dt
                if (dt.date.fromisoformat(today) - dt.date.fromisoformat(last)).days < 7:
                    return
            except Exception:  # noqa: BLE001
                pass
        try:
            import secscan
            self.config["fw_check_day"] = today
            self.save_config()
            self.fw_worker = secscan.FirewallWorker()
            self.fw_worker.done.connect(self._on_firewall_week)
            self.fw_worker.start()
        except Exception:  # noqa: BLE001
            pass

    def _on_firewall_week(self, rows: list):
        if not rows:
            return
        off = [self.FW_NAMES.get(r.get("name", ""), r.get("name", ""))
               for r in rows if not r.get("enabled")]
        if off:
            self.pet.bubble.show_text(
                "⚠ 每周防火墙体检：" + "、".join(off) + " 是关着的，我建议你打开。", 7000)
            self.pet.set_expression("angry", 4000)
        else:
            self.pet.bubble.show_text("每周防火墙体检：三档都开着，很好。", 4000)

    # ---------- v2.3.0 语音命令 ----------
    def voice_listen(self):
        if self.voice_worker is not None and self.voice_worker.isRunning():
            return
        if self._chat_busy():
            self.pet.bubble.show_text("等我把这句说完再听你说。", 2500)
            return
        self.pet.bubble.show_text("我在听，说一句吧（说完停一下）……", 5000)
        self.pet.set_expression("curious", 6000)
        try:
            import voice_cmd
            self.voice_worker = voice_cmd.VoiceWorker(wait_s=4, timeout_s=14)
            self.voice_worker.done.connect(self._on_voice)
            self.voice_worker.start()
        except Exception as e:  # noqa: BLE001
            self.pet.bubble.show_text("语音模块起不来：" + str(e)[:40], 3500)

    def _on_voice(self, res: dict):
        self._last_voice = res or {}
        text = str((res or {}).get("text") or "").strip()
        self.panel and self.panel.set_chat_status(("听到：" + text) if text else "没听清")
        if not text:
            reason = str((res or {}).get("reason") or "")
            tip = {"no_mic": "没找到麦克风，检查一下设备。",
                   "no_speech": "没听到声音，再说一次？",
                   "timeout": "听的时间到了，没抓到语音。",
                   "empty_text": "听到了，但没识别出字。"}.get(
                       reason, "没听清（" + reason[:30] + "）")
            self.pet.bubble.show_text(tip, 3200)
            return
        self.pet.bubble.show_text("听到：" + text, 2500)
        # v2.9.2 唤醒词：大肥鱼 / 你好，大肥鱼 / 改名后的名字（含「你好，名字」）
        wake = self._match_wake_word(text)
        if wake:
            rest = text.strip()[len(wake):].strip(" ，,。.!！?？、")
            self.pet.bubble.show_text("在呢，说吧。", 2200)
            self.pet.set_expression("happy", 2500)
            # v3.0.0：这里不再先画一条用户气泡，交给 send_chat 统一画一次，避免语音双发
            if not rest:
                # 只喊了名字：接着听下一句，不用再按快捷键
                if self.config.get("wake_then_listen", True) and not self._chat_busy():
                    QTimer.singleShot(700, self.voice_listen)
                return
            text = rest
        # 先当本地命令执行（打开面板、换装、动作、打工、安全体检…）；没命中再走对话
        if self._dispatch_voice(text):
            return
        self.send_chat(text)

    def wake_words(self) -> list:
        """唤醒词候选：固定「大肥鱼」+ 当前角色名 + 用户自己加的叫法（各带「你好」说法）。"""
        name = str(self.config.get("name") or DEFAULT_NAME).strip()
        bases = ["大肥鱼"]
        if name and name not in bases:
            bases.append(name)
        for w in (self.config.get("wake_words_extra") or []):
            w = str(w).strip()
            if w and w not in bases:
                bases.append(w)
        out = []
        for w in bases:
            for form in (w, "你好" + w, "你好，" + w):
                if form not in out:
                    out.append(form)
        return out

    def _match_wake_word(self, text: str) -> str:
        """只有整句或以唤醒词开头才算唤醒，避免「大肥鱼好看吗」这类闲聊被拦截。"""
        t = (text or "").strip()
        for w in sorted(self.wake_words(), key=len, reverse=True):
            if t == w or t.startswith(w):
                return w
        return ""

    def _dispatch_voice(self, text: str) -> bool:
        """语音 → 本地功能。命中就执行，并把这一句回灌到面板聊天记录。"""
        low = (text or "").strip()
        if not low:
            return False
        # v2.9.7：做小软件的指令要把整句话当需求给模型，先单独接
        ma = re.search(r"(?:做|写)(?:个|一个|款)?(.{2,40}?)(?:的小?软件|的小?工具|的?脚本|程序)", low)
        if ma or any(k in low for k in ("做个小软件", "做个小工具", "写个小工具", "写个脚本")):
            ask = low
            for w in ("大肥鱼", "帮我", "给我", "做个小软件", "做个小工具", "写个小工具", "写个脚本"):
                ask = ask.replace(w, "")
            self.make_tool(ask.strip("，。 ") or low)
            self.panel and self.panel.append_chat("user", text)
            return True
        for keys, label, fn in self._voice_commands():
            if any(k in low for k in keys):
                try:
                    fn()
                except Exception as e:  # noqa: BLE001
                    self.pet.bubble.show_text(f"{label}没做成：{str(e)[:30]}", 3000)
                    return True
                self.pet.bubble.show_text(f"好，{label}。", 2200)
                self.panel and self.panel.append_chat("user", text)
                self.panel and self.panel.append_chat("assistant", f"（语音）好，{label}。")
                return True
        return False

    def _voice_commands(self) -> list:
        """(关键词, 说法, 动作)。先具体后笼统，避免"打开"吃掉"打开面板"。"""
        def _skin_next():
            skins = ["default", "jk", "hanfu", "longmaid", "blackgown", "blackgreen", "blackred"]
            cur = self.config.get("skin", "default")
            nxt = skins[(skins.index(cur) + 1) % len(skins)] if cur in skins else skins[0]
            self.set_skin(nxt)

        def _close_panel():
            if self.panel is not None:
                self.panel.close()

        def _feed():
            snacks = self.snacks()
            self.feed_snack(snacks[0]["key"] if snacks else "fish")

        def _set_topmost(on):
            self.pet.set_topmost(bool(on))
            self.save_config()

        def _set_scale(step):
            self.pet.set_pet_scale(self.pet.scale + step)
            self.save_config()

        def _size(label):
            self.set_size(label)

        return [
            (("零食商城", "买零食", "零食店", "逛商城", "去购物"), "打开零食商城", self.open_shop),
            (("打开背包", "看背包", "背包里有什么"), "打开背包", self.open_backpack),
            (("去打工", "打工", "找份活", "上班"), "看工作选项", self.offer_work),
            (("喝水", "口渴", "想喝点"), "喝水去了", self.do_drink),
            (("状态栏", "我还好吗"), "看看状态", lambda: self.maybe_status_bar(force=True)),
            (("更新病毒库", "升级病毒库", "更新杀毒"), "病毒库更新了",
             lambda: self.update_signatures()),
            (("安全体检", "检查电脑安全", "体检"), "开始安全体检", self.run_scan),
            (("清理垃圾", "清理电脑垃圾", "清垃圾"), "开始清理垃圾",
             lambda: self.start_task("cleanup")),
            (("擦桌面", "擦一下桌面"), "开始擦桌面", lambda: self.start_task("wipe")),
            (("做家务", "收拾房间"), "开始做家务", lambda: self.start_task("chores")),
            (("联网学习", "去上课", "学习"), "去联网上课", lambda: self.start_task("study")),
            (("满屏跑", "跑一圈"), "开始满屏跑", lambda: self.begin_run(15000)),
            (("跑步", "跑起来"), "跑起来", lambda: self.pet.do_run(15000)),
            (("散步", "走两步", "走走"), "散步去", self.pet.do_walk),
            (("跳舞", "跳个舞"), "跳舞", lambda: self.pet.do_action("dance")),
            (("蹦一下", "跳一下"), "跳一下", self.pet.do_jump),
            (("摇一摇", "抖一下"), "晃一晃", self.pet.do_shake),
            (("表演", "来个表演", "随便做点啥"), "表演一个", self.perform_random),
            (("摸头", "摸摸头"), "摸摸头", self.pet.do_pat),
            (("喂零食", "喂点吃的", "吃点东西"), "喂你了", _feed),
            (("睡觉", "休息一下"), "去睡觉", self.pet.do_sleep),
            (("起床", "醒醒", "醒来"), "醒过来了", self.pet.wake),
            (("换装", "换衣服", "换一套"), "换装了", _skin_next),
            (("萝莉", "小形态"), "换成萝莉形态", lambda: self.set_form("loli")),
            (("成熟", "大形态"), "换成成熟形态", lambda: self.set_form("mature")),
            (("静音", "别出声", "闭嘴"), "静音了", lambda: self.toggle_sound(False)),
            (("开声音", "出声", "取消静音"), "声音打开了", lambda: self.toggle_sound(True)),
            (("番茄钟", "计时二十五分钟"), "番茄钟开始", lambda: self.start_tomato(25)),
            (("停止计时", "关掉计时器", "结束番茄钟"), "计时停了", self.stop_tomato),
            (("喝水提醒", "提醒我喝水"), "喝水提醒开着", lambda: self.toggle_water(True)),
            (("不用喝水提醒", "关掉喝水提醒"), "喝水提醒关了", lambda: self.toggle_water(False)),
            (("久坐提醒", "提醒我站起来"), "久坐提醒开着", lambda: self.toggle_sedentary(True)),
            (("不用久坐提醒", "关掉久坐提醒"), "久坐提醒关了", lambda: self.toggle_sedentary(False)),
            (("跟着我", "跟着鼠标"), "跟着你跑", lambda: self.pet.set_follow(True)),
            (("别跟着我", "别跟了"), "不跟了", lambda: self.pet.set_follow(False)),
            (("碎碎念", "多说点话", "陪我聊会"), "开始碎碎念", lambda: self.toggle_chatter(True)),
            (("别碎碎念", "安静点"), "不念叨了", lambda: self.toggle_chatter(False)),
            (("自主行动", "自己动起来"), "自主行动开了", lambda: self.set_auto(True)),
            (("别自己动了", "停止自主行动"), "自主行动关了", lambda: self.set_auto(False)),
            (("置顶", "一直在上面"), "置顶打开", lambda: _set_topmost(True)),
            (("取消置顶", "别置顶"), "置顶取消", lambda: _set_topmost(False)),
            (("变大", "大一点", "放大"), "变大了", lambda: _set_scale(0.1)),
            (("变小", "小一点", "缩小"), "变小了", lambda: _set_scale(-0.1)),
            (("大号", "大尺寸"), "换成大号", lambda: _size("大")),
            (("中号", "中尺寸"), "换成中号", lambda: _size("中")),
            (("小号", "小尺寸"), "换成小号", lambda: _size("小")),
            (("检查更新", "有没有新版本", "更新版本"), "去检查更新了", self.check_update),
            (("停下", "停止", "别跑了"), "停下了", self._voice_stop),
            (("关掉面板", "关闭面板"), "关掉面板", _close_panel),
            (("打开面板", "控制面板", "打开设置"), "打开面板", self.open_panel),
            (("躲起来", "隐藏"), "隐藏起来", self.pet.hide),
            (("出来", "显示"), "出来了", self.pet.show),
        ]

    def _voice_stop(self):
        try:
            self.cancel_task()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.pet.finish_action()
            self.pet.finish_state()
        except Exception:  # noqa: BLE001
            pass

    # ================= 定时 / 22:00 休息 =================
    def _on_schedule_fire(self, task: dict):
        text = (task.get("text") or "时间到啦").strip()
        self._speak(f"叮——{text}", 6000)
        self.pet.set_expression("curious", 3000)
        self.beep("done")
        self.refresh_panel()

    def _on_night_remind(self, n: int):
        if n <= 0:
            msg = random.choice([
                "十点啦，今天的活儿收个尾，早点去睡吧。",
                "到十点了哦，剩下的明天再弄，别熬。",
            ])
            expr = "sleepy"
        else:
            msg = random.choice([
                f"第 {n} 次催你了——电脑关不关？",
                f"还不睡？（{n}/4）我可盯着呢。",
                f"再刷一会儿我可要一直喊了，{n} 次了。",
            ])
            expr = "angry"
        self._speak(msg, 6000)
        self.pet.set_expression(expr, 4000)
        self.beep("done")

    def night_on(self) -> bool:
        return bool(self.config.setdefault("schedule", {}).get("night_on", True))

    def set_night_on(self, on: bool):
        self.config.setdefault("schedule", {})["night_on"] = bool(on)
        self.scheduler.reset_night()
        self.save_config()

    def schedule_tasks(self) -> list:
        try:
            return self.scheduler.tasks()
        except Exception:  # noqa: BLE001
            return []

    def add_schedule(self, kind: str, when: str, text: str, weekday: int = -1):
        return self.scheduler.add(kind, when, text, weekday)

    def remove_schedule(self, tid):
        self.scheduler.remove(tid)

    def toggle_schedule(self, tid, on: bool):
        self.scheduler.toggle(tid, on)

    # ================= 安全体检 =================
    def run_scan(self):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return
        import secscan
        self.scan_worker = secscan.ScanWorker()
        self.scan_worker.done.connect(self._on_scan_done)
        self.scan_worker.start()

    def _on_scan_done(self, report: dict):
        self._scan_report = report
        self.panel and self.panel.refresh_scan(report)

    def last_scan(self) -> dict:
        return getattr(self, "_scan_report", None) or {}

    # ================= v3.0.10 安全管家（自研启发式，只报不杀） =================
    def run_guard_scan(self) -> bool:
        """起一轮后台扫描；已在跑就返回 False。"""
        if self.guard_worker is not None and self.guard_worker.isRunning():
            return False
        import guard_core
        self.guard_worker = guard_core.GuardWorker()
        self.guard_worker.progress.connect(self._on_guard_progress)
        self.guard_worker.done.connect(self._on_guard_done)
        self.guard_worker.failed.connect(self._on_guard_failed)
        self.guard_worker.start()
        return True

    def _on_guard_progress(self, pct: int, msg: str):
        if self.panel:
            try:
                self.panel.on_guard_progress(pct, msg)
            except Exception:  # noqa: BLE001
                pass

    def _on_guard_done(self, rep: dict):
        self.guard_report = rep or {}
        try:
            import guard_core
            rep["files"] = guard_core.save_report(rep)
        except Exception as e:  # noqa: BLE001
            rep["files"] = {"error": str(e)}
        if self.panel:
            try:
                self.panel.refresh_guard(self.guard_report)
            except Exception:  # noqa: BLE001
                pass
        # 她本人报一句，别让扫描结果只躺在面板里
        try:
            score, level = self.guard_report.get("score", 0), self.guard_report.get("level", "")
            n = len(self.guard_report.get("findings") or [])
            if n:
                self.pet.bubble.show_text(
                    f"安全管家扫完了：风险分 {score}（{level}），{n} 条线索。"
                    "我只报不杀，要处置就交 Defender。", 5000)
            else:
                self.pet.bubble.show_text("安全管家扫完了，没发现值得报警的东西。", 3600)
        except Exception:  # noqa: BLE001
            pass

    def _on_guard_failed(self, msg: str):
        if self.panel:
            try:
                self.panel.lbl_guard.setText(f"扫描失败：{msg}")
                self.panel.btn_guard.setEnabled(True)
            except Exception:  # noqa: BLE001
                pass

    def guard_defender(self):
        """把高/中危的文件线索交给 Defender 逐个深扫；没有就整机快扫。"""
        import guard_core
        paths = []
        for f in (self.guard_report or {}).get("findings") or []:
            if f.get("kind") not in ("file", "pe"):
                continue
            p = str(f.get("target", ""))
            if p and os.path.exists(p):
                paths.append(p)
        paths = paths[:8]
        quick = not paths
        self.defender_worker = guard_core.DefenderWorker(paths, quick)
        self.defender_worker.done.connect(self._on_defender_done)
        self.defender_worker.start()
        return paths, quick

    def _on_defender_done(self, res: dict):
        if self.panel:
            try:
                self.panel.on_defender_done(res or {})
            except Exception:  # noqa: BLE001
                pass

    # ================= 知识库 / 记忆 =================
    def import_knowledge(self, path: str) -> dict:
        res = self.kb.import_file(path)
        self.refresh_panel()
        return res

    def kb_stats(self) -> dict:
        try:
            return self.kb.stats()
        except Exception:  # noqa: BLE001
            return {}

    def kb_docs(self) -> list:
        try:
            return self.kb.docs()
        except Exception:  # noqa: BLE001
            return []

    def remove_kb_doc(self, doc_id):
        self.kb.remove(doc_id)
        self.refresh_panel()

    def memory_facts(self) -> list:
        try:
            return self.memory.facts(20)
        except Exception:  # noqa: BLE001
            return []

    def memory_count(self) -> int:
        try:
            return self.memory.count()
        except Exception:  # noqa: BLE001
            return 0

    def forget_memory(self) -> int:
        n = 0
        try:
            n = self.memory.forget_all()
        except Exception:  # noqa: BLE001
            pass
        self.refresh_panel()
        return n

    # ================= 本地模型 =================
    def local_llm_ready(self) -> bool:
        try:
            return self.llm.is_running() or self.llm.health()
        except Exception:  # noqa: BLE001
            return False

    def _warm_local_llm(self):
        if not local_llm.available(self.config):
            return
        threading.Thread(target=self.llm.start, daemon=True).start()

    def start_local_llm(self):
        self._warm_local_llm()

    def stop_local_llm(self):
        try:
            self.llm.stop()
        except Exception:  # noqa: BLE001
            pass

    def local_llm_info(self) -> dict:
        m = self.llm.model()
        backend = ""
        ollama = []
        try:
            backend = self.llm.backend
            if backend == "ollama":
                ollama = local_llm.ollama_models(self.llm.ollama_host)
        except Exception:  # noqa: BLE001
            backend = backend or "dafeiyu_cpp"
        use = ""
        if backend == "ollama":
            use = self.llm.ollama_model
            if not any(x["name"] == use for x in ollama):
                use = self.llm._pick_ollama_model()
        return {
            "available": local_llm.available(self.config),
            "running": self.local_llm_ready(),
            "model": os.path.basename(m) if (m and backend == "dafeiyu_cpp") else use,
            "port": self.llm.port,
            "backend": backend,
            "ollama": ollama,
            "ollama_host": self.llm.ollama_host,
            "loaded": local_llm.ollama_loaded(self.llm.ollama_host) if backend == "ollama" else [],
        }

    # ================= 模型库 =================
    def local_models(self):
        return model_dl.local_models(self.config)

    def model_search_dirs(self) -> list:
        """面板里提示用户「模型放哪能被扫到」。"""
        try:
            return local_llm.model_dirs(self.config)
        except Exception:  # noqa: BLE001
            return []

    def download_model(self, item_id: str) -> bool:
        it = models_catalog.by_id(item_id)
        if not it or not models_catalog.can_download(it):
            return False
        w = self.dl_worker
        if w is not None and w.isRunning():
            return False
        dest = os.path.join(self.models_dir(), it["file"])
        self.dl_worker = model_dl.ModelDownloader(item_id, it["url"], dest)
        self.dl_worker.progress.connect(self._on_dl_progress)
        self.dl_worker.done.connect(self._on_dl_done)
        self.dl_worker.failed.connect(self._on_dl_failed)
        self.dl_worker.start()
        return True

    def models_dir(self) -> str:
        """模型下载落地目录：优先数据目录（v3.0.7，装在 Program Files 时程序目录写不进去）。"""
        d = os.path.join(paths.data_dir(), "models")
        try:
            os.makedirs(d, exist_ok=True)
            if os.access(d, os.W_OK):
                return d
        except OSError:
            pass
        d = os.path.join(paths.runtime_dir(), "models")
        os.makedirs(d, exist_ok=True)
        return d

    def download_model_url(self, url: str):
        """联网添加模型：.gguf 直链或 hf-mirror 仓库页。返回 (ok, 给用户看的一句话)。"""
        u = (url or "").strip()
        if not u.lower().startswith(("http://", "https://")):
            return False, "地址要以 http:// 或 https:// 开头。"
        w = self.dl_worker
        if w is not None and w.isRunning():
            return False, "已经有下载任务在跑，先等它完成或点「取消下载」。"
        real, name = model_dl.resolve_gguf_url(u)
        if not real or not name:
            return False, "这个地址里没找到 .gguf（仓库页可能只有分片或 safetensors）。"
        if not name.lower().endswith(".gguf"):
            return False, "只接受 .gguf 单文件模型。"
        dest = os.path.join(self.models_dir(), name)
        if os.path.exists(dest):
            return False, f"{name} 已经在本地了，不用重复下载。"
        self.dl_worker = model_dl.ModelDownloader("custom:" + name, real, dest)
        self.dl_worker.progress.connect(self._on_dl_progress)
        self.dl_worker.done.connect(self._on_dl_done)
        self.dl_worker.failed.connect(self._on_dl_failed)
        self.dl_worker.start()
        return True, f"开始下载 {name}，下完会出现在「已安装模型」里。"

    def cancel_download(self) -> bool:
        w = self.dl_worker
        if w is not None and w.isRunning():
            w.stop()
            return True
        return False

    def _on_dl_progress(self, item_id: str, got: int, total: int):
        try:
            self.dl_speed = self.dl_worker.speed if self.dl_worker else 0.0
        except Exception:  # noqa: BLE001
            self.dl_speed = 0.0
        if self.panel is not None:
            try:
                self.panel.on_model_progress(item_id, got, total)
            except Exception:  # noqa: BLE001
                pass

    def _on_dl_done(self, item_id: str, path: str):
        self.dl_speed = 0.0
        it = models_catalog.by_id(item_id) or {}
        name = it.get("file") or os.path.basename(path)
        # v3.0.8：存绝对路径，杜绝不同目录同名模型切错
        self.config["llm_model_file"] = path if (path and os.path.isabs(path)) else name
        self.save_config()
        self.dl_worker = None
        if self.panel is not None:
            try:
                self.panel.pbar_model.setVisible(False)
                self.panel.lbl_dl.setText(f"下载完成：{os.path.basename(path)}，已设为当前模型（重启生效）。")
                self.panel._refresh_v2()
            except Exception:  # noqa: BLE001
                pass

    def _on_dl_failed(self, item_id: str, why: str):
        self.dl_speed = 0.0
        self.dl_worker = None
        if self.panel is not None:
            try:
                self.panel.pbar_model.setVisible(False)
                self.panel.lbl_dl.setText(f"下载未完成：{why}")
            except Exception:  # noqa: BLE001
                pass

    def use_ollama_model(self, name: str) -> bool:
        """切到 Ollama 后端并指定模型（面板「Ollama 里的模型」点使用）。"""
        name = (name or "").strip()
        if not name or not local_llm.ollama_model_present(name, self.llm.ollama_host):
            return False
        self.config["ollama_model"] = name
        self.config["llm_backend"] = "ollama"
        self.save_config()
        try:
            if self.local_llm_ready():
                self.llm.stop()
        except Exception:  # noqa: BLE001
            pass
        return True

    def check_ollama(self):
        """真打一次生成请求，判断 Ollama 是「只是列着模型」还是「真能跑」。

        v3.0.7 实测：Ollama 的 llama-server.exe 缺失时 /api/tags 完全正常，
        只有生成才 500/404，用户看到的假象就是"模型在、但不启用"。
        返回 (ok, 一句话)。
        """
        import json as _json
        import urllib.error as _ue
        import urllib.request as _ur
        host = self.config.get("ollama_host", local_llm.OLLAMA_HOST)
        if not local_llm.ollama_alive(host):
            return False, "Ollama 没在运行（11434 连不上）。用自带引擎就行，不用管它。"
        try:
            name = self.llm._pick_ollama_model()
        except Exception:  # noqa: BLE001
            name = self.config.get("ollama_model", "")
        body = {"model": name, "messages": [{"role": "user", "content": "hi"}],
                "stream": False, "options": {"num_predict": 1}}
        req = _ur.Request(host.rstrip("/") + "/api/chat",
                          data=_json.dumps(body).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with _ur.urlopen(req, timeout=25) as r:
                data = _json.loads(r.read().decode("utf-8"))
            if (data.get("message") or {}).get("content") is not None:
                return True, f"Ollama 正常，{name} 能生成。"
            return False, f"Ollama 回了空内容（{name}）。"
        except _ue.HTTPError as e:
            try:
                detail = (e.read() or b"").decode("utf-8", "ignore")[:200]
            except Exception:  # noqa: BLE001
                detail = ""
            try:
                self.llm.ollama_broken = True
            except Exception:  # noqa: BLE001
                pass
            if "llama-server binary not found" in detail:
                return False, (f"Ollama 自己坏了：找不到 llama-server.exe（HTTP {e.code}）。"
                               "重装 Ollama 就好，这期间桌宠会自动用自带引擎。")
            return False, f"Ollama 生成失败（HTTP {e.code}）：{detail or '没有返回内容'}"
        except Exception as e:  # noqa: BLE001
            return False, f"连不上 Ollama：{e}"

    def ollama_library(self, refresh: bool = False) -> list:
        """Ollama 官方库名单（联网抓 ollama.com/library，带 12 小时缓存）。"""
        try:
            return ollama_hub.library(refresh)
        except Exception:  # noqa: BLE001
            return []

    def ollama_hub_tags(self, name: str) -> list:
        try:
            return ollama_hub.tags(name)
        except Exception:  # noqa: BLE001
            return []

    def download_ollama(self, ref: str):
        """从 Ollama 官方 registry 下载权重 blob（就是标准 GGUF），交给自带引擎跑。

        ref 形如 qwen3.5:4b；不写 tag 就当 latest。
        """
        ref = (ref or "").strip().strip("/")
        if not ref:
            return False, "先填模型名，比如 qwen3.5:4b、gemma4:e2b。"
        if ":" in ref:
            name, tag = ref.split(":", 1)
        else:
            name, tag = ref, "latest"
        if not name:
            return False, "模型名不能为空。"
        w = self.dl_worker
        if w is not None and w.isRunning():
            return False, "已经有下载任务在跑，先等它完成或点「取消下载」。"
        m = ollama_hub.manifest(name, tag)
        if not m or not m.get("model_url"):
            return False, f"Ollama registry 里没找到 {name}:{tag}（名字或 tag 不对，或是分片模型）。"
        dest = os.path.join(self.models_dir(), ollama_hub.dest_name(name, tag))
        if os.path.exists(dest):
            return False, f"{os.path.basename(dest)} 已经在本地了，直接点「使用此模型」。"
        size_mb = m.get("model_size", 0) / 1048576
        self.dl_worker = model_dl.ModelDownloader("ollama:" + ref, m["model_url"], dest)
        self.dl_worker.progress.connect(self._on_dl_progress)
        self.dl_worker.done.connect(self._on_dl_done)
        self.dl_worker.failed.connect(self._on_dl_failed)
        self.dl_worker.start()
        return True, (f"开始从 Ollama 官方库下载 {name}:{tag}（{size_mb:.0f} MB）。"
                      "下完就是普通 gguf，直接用自带引擎跑，不用启动 Ollama。")

    def import_ollama_models(self) -> bool:
        """把本机 Ollama 已下载的权重复制到模型目录（不联网、不启动 Ollama）。"""
        w = self.ollama_import
        if w is not None and w.isRunning():
            return False
        try:
            self.ollama_import = ollama_hub.OllamaImportWorker(
                self.models_dir(), [os.path.join(paths.runtime_dir(), "models")])
            self.ollama_import.done_stats.connect(self._on_ollama_imported)
            self.ollama_import.start()
            return True
        except Exception:  # noqa: BLE001
            self.ollama_import = None
            return False

    def _on_ollama_imported(self, stats: dict):
        self.ollama_import = None
        copied = stats.get("copied", 0)
        skipped = stats.get("skipped", 0)
        mb = stats.get("bytes", 0) / 1048576
        msg = f"从本机 Ollama 导入完成：新增 {copied} 个（{mb:.0f} MB），已存在 {skipped} 个"
        errs = stats.get("errors") or []
        if errs:
            msg += "；跳过 " + "；".join(errs[:3])
        if self.panel is not None:
            try:
                self.panel.lbl_dl.setText(msg)
                self.panel._refresh_v2()
            except Exception:  # noqa: BLE001
                pass

    def use_model(self, file_name: str) -> bool:
        """file_name 可以是绝对路径，也可以是文件名（会在所有模型目录里找）。"""
        name = (file_name or "").strip()
        p = local_llm.resolve_model(name, self.config)
        if not p:
            return False
        # 存绝对路径，避免不同目录里同名模型切错
        self.config["llm_model_file"] = p
        self.save_config()
        try:
            if self.local_llm_ready():
                self.llm.stop()
        except Exception:  # noqa: BLE001
            pass
        return True

    def delete_model(self, file_name: str) -> float:
        p = local_llm.resolve_model(file_name, self.config)
        if not p or not os.path.exists(p):
            return 0.0
        size = os.path.getsize(p) / 1048576
        try:
            os.remove(p)
        except OSError:
            return 0.0
        part = p + ".part"
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
        cur = str(self.config.get("llm_model_file", ""))
        if cur and (cur == p or os.path.basename(cur) == file_name
                    or os.path.basename(cur) == os.path.basename(p)):
            self.config["llm_model_file"] = ""
            self.save_config()
        return size

    # ================= 打工任务 =================
    def task_state(self):
        return self.task_active

    def start_task(self, key: str):
        if self.task_active is not None:
            return
        defn = TASK_DEFS.get(key)
        if not defn:
            return
        self.task_active = {"key": key, "left": defn["duration"], "total": defn["duration"],
                            "fact": "", "last_action": -999}
        # v3.0.0：开工先按工种扣一次体力，干活越重饿得越快
        self.state.spend({"study": "work_study", "patrol": "work_run",
                          "stretch": "work_rest", "cleanup": "work_clean",
                          "wipe": "work_wipe", "chores": "work_chores"}.get(key, ""))
        kind = defn["kind"]
        self._play_task_action(defn)
        if kind == "run":
            self.begin_run(defn["duration"] * 1000)
        elif kind == "clean":
            self.pet.set_expression("curious", 0)
            self._start_cleanup()
        elif kind in ("rest", "wipe", "chore"):
            self.pet.set_expression("sleepy", 0)
            if kind == "wipe":
                self.pet.bubble.show_text(lines.pick(lines.WIPE), 2600)
            elif kind == "chore":
                self.pet.bubble.show_text(lines.pick(lines.CHORE), 2600)
        else:
            self.pet.set_expression("curious", 0)
            self._fetch_knowledge()
        self.task_timer.start()
        self.panel and self.panel.refresh_tasks()

    def _fetch_knowledge(self):
        prof = self.active_profile()
        self.know_worker = ChatWorker(
            endpoint=prof.get("endpoint", ""), model=prof.get("model", ""),
            api_key=prof.get("api_key", ""), history=[], user_text=KNOWLEDGE_PROMPT_TOPIC,
            system_prompt=KNOWLEDGE_PROMPT_TOPIC, max_tokens=200, temperature=0.7)
        self.know_worker.reply_ready.connect(self._on_knowledge)
        self.know_worker.failed.connect(self._on_knowledge_failed)
        self.know_worker.start()

    def _on_knowledge(self, fact: str):
        if self.task_active:
            self.task_active["fact"] = fact
        self.panel and self.panel.set_task_fact(fact)

    def _start_cleanup(self):
        self.clean_worker = CleanWorker()
        self.clean_worker.done.connect(self._on_clean_done)
        self.clean_worker.start()

    def _on_clean_done(self, res: dict):
        mb = res.get("bytes", 0) / 1048576
        fact = (f"清理出 {mb:.1f} MB：删除 {res.get('removed', 0)} 个临时文件，"
                f"{res.get('skipped', 0)} 个被占用已跳过。")
        if self.task_active:
            self.task_active["fact"] = fact
        self.panel and self.panel.set_task_fact(fact)

    def _on_knowledge_failed(self, reason: str):
        fact = "联网没接上，本鱼先凭记忆讲一句：鲸鱼是用肺呼吸的哺乳动物，不是鱼哦。"
        if self.task_active:
            self.task_active["fact"] = fact
        self.panel and self.panel.set_task_fact(fact)

    def _on_task_tick(self):
        if not self.task_active:
            return
        self.task_active["left"] -= 1
        if self.task_active["left"] <= 0:
            self._finish_task()
            return
        # 任务期间不再每 6 秒重播一次动作：v3.0.0 起每个工种是一整套持续表演
        self.panel and self.panel.refresh_tasks()

    TASK_WORK_STATE = {"knowledge": "work_study", "rest": "work_rest",
                       "clean": "work_clean", "wipe": "work_wipe", "chore": "work_chores"}

    def _play_task_action(self, defn: dict):
        """按工种给桌宠一套持续动作（v3.0.0：做到完工，不是闪一下）。"""
        kind = str((defn or {}).get("kind") or "")
        st = self.TASK_WORK_STATE.get(kind)
        if st:
            try:
                self.pet.do_task_work(st)
            except Exception:  # noqa: BLE001
                pass
            return
        # kind == "run" 由 begin_run 负责整套奔跑，不重复设置

    def _finish_task(self):
        active = self.task_active
        if not active:
            return
        defn = TASK_DEFS[active["key"]]
        leveled = self.state.reward(exp=defn["exp"], coins=defn["coins"], mood=defn["mood"])
        done = self.config.setdefault("tasks", {}).setdefault("done_count", {})
        done[active["key"]] = done.get(active["key"], 0) + 1
        self.task_active = None
        self.task_timer.stop()
        self.pet.finish_state()       # v3.0.0：把 work_* 状态一起收回 idle
        self.beep("done")
        msg = f"完工！拿到 {defn['coins']} 金币、{defn['exp']} 经验。"
        if leveled:
            msg += f"\n升到 Lv.{self.state.level}！"
        self.pet.bubble.show_text(msg, 3200)
        self.pet.set_expression("happy", 3000)
        self.save_config()
        self.panel and self.panel.refresh_tasks()
        self.refresh_panel()

    def cancel_task(self):
        if self.task_active is None:
            return
        self.task_active = None
        self.task_timer.stop()
        self.pet.finish_state()
        self.panel and self.panel.refresh_tasks()

    # ================= 自主行动 =================
    def set_auto(self, on: bool):
        self.config["auto_on"] = bool(on)
        self.save_config()

    def is_night(self) -> bool:
        """夜间窗口：默认 23:00–07:00，可在 config.schedule.night_range 改。"""
        if not self.night_on():
            return False
        rng = self.config.setdefault("schedule", {}).get("night_range", [23, 7])
        try:
            a, b = int(rng[0]), int(rng[1])
        except (TypeError, IndexError, ValueError):
            a, b = 23, 7
        h = time.localtime().tm_hour
        return h >= a or h < b

    def auto_weights(self) -> dict:
        """v2.8 自主行动权重表：按心情分档，夜间切到休息池（可被 config["auto_weights"] 覆盖）。"""
        w = self.config.get("auto_weights")
        if isinstance(w, dict) and w:
            return {k: max(0.0, float(v)) for k, v in w.items()}
        mood = int(getattr(self.state, "mood", 60))
        pool = {"chatter": 30, "walk": 25, "random_action": 15,
                "expression": 15, "run": 10, "sleep": 5}
        if mood < 30:
            pool.update(chatter=12, walk=12, random_action=8, expression=8, run=2, sleep=58)
        elif mood > 70:
            pool.update(chatter=28, walk=30, random_action=22, expression=12, run=20, sleep=2)
        if self.is_night():
            pool = {"chatter": 6, "walk": 6, "random_action": 6,
                    "expression": 8, "run": 0, "sleep": 74}
        return pool

    def _on_auto(self):
        if not self.config.get("auto_on", True):
            return
        if self.task_active is not None:
            return
        if self.pet.state in ("sleep", "drag", "run"):
            return
        self.pet.night = self.is_night()
        pool = self.auto_weights()
        total = sum(pool.values()) or 1.0
        r = random.uniform(0, total)
        acc, pick = 0.0, "sleep"
        for k, v in pool.items():
            acc += v
            if r <= acc:
                pick = k
                break
        if pick == "chatter" and self.config.get("chatter_on", True):
            # v3.0.16：有"还没做完的事"就先提它（议程），否则随机碎碎念
            said = None
            try:
                ag = self.memory_tiers.agenda(2) if self.memory_tiers is not None else []
            except Exception:  # noqa: BLE001
                ag = []
            if ag and random.random() < 0.5:
                said = f"鱼片，{ag[0]}——这事你没忘吧？"
            self.pet.bubble.show_text(said or lines.pick(lines.CHAT_IDLE), 3200)
            if said:
                try:
                    self.memory.add_message("assistant", said)
                except Exception:  # noqa: BLE001
                    pass
        elif pick == "walk":
            self.pet.do_walk()
        elif pick == "random_action":
            self.pet.trigger_random()
        elif pick == "expression":
            expr = random.choice(["happy", "shy", "curious", "sleepy"])
            self.pet.set_expression(expr, 2500)
        elif pick == "run":
            self.begin_run(6000)
        else:
            self.pet.set_expression("sleep", 6000)

    # ================= v2.9.0 环境播报（天气 / 新闻） =================
    def set_weather_city(self, city: str):
        city = (city or "").strip()
        if not city:
            return
        self.config["weather_city"] = city
        self.config["ambient_geo"] = {}
        self.save_config()
        self._ambient_last = 0.0
        self._on_ambient_tick(force=True)

    def _ambient_busy(self) -> bool:
        return self.ambient_worker is not None and self.ambient_worker.isRunning()

    def _on_ambient_tick(self, force: bool = False):
        if self._ambient_busy():
            return
        if not (self.config.get("weather_on", True) or self.config.get("news_on", True)):
            return
        gap = max(600, int(self.config.get("ambient_interval", 90 * 60)))
        if not force and time.time() - self._ambient_last < gap:
            return
        self.ambient_worker = ambient.AmbientWorker(
            self.config.get("weather_city", "郑州"),
            want_news=bool(self.config.get("news_on", True)))
        self.ambient_worker.done.connect(self._on_ambient_done)
        self.ambient_worker.failed.connect(self._on_ambient_failed)
        self.ambient_worker.start()

    def _on_ambient_done(self, data: dict):
        self.ambient_worker = None
        self._ambient_last = time.time()
        self._ambient_cache = data or {}
        geo = (data or {}).get("geo") or {}
        if geo:
            self.config["ambient_geo"] = geo
            self.save_config()
        if not getattr(self, "_ambient_greeted", False):
            # 启动后第一份数据：先报天气，让"会看天气"这件事一眼可见
            self._ambient_greeted = True
            self.speak_weather()
        else:
            self.speak_ambient()

    def _on_ambient_failed(self, why: str):
        self.ambient_worker = None
        self._ambient_last = time.time()   # 失败也记时，避免每 5 分钟重试刷网络

    def speak_weather(self) -> bool:
        w = (self._ambient_cache or {}).get("weather") or {}
        if not w:
            self.pet.bubble.show_text("天气还没拿到，等我会联网再说。", 2400)
            return False
        city = (self._ambient_cache or {}).get("city") or self.config.get("weather_city", "")
        line = ambient.weather_line(w, city)
        if not line:
            return False
        self._speak(line, 5200, priority=0)
        self.pet.set_expression("curious", 3000)
        return True

    def speak_news(self) -> bool:
        news = (self._ambient_cache or {}).get("news") or []
        if not news:
            self.pet.bubble.show_text("新闻还没拉到，稍等。", 2200)
            return False
        self._speak(ambient.news_line(random.choice(news)), 5200, priority=0)
        return True

    def speak_ambient(self):
        """天气与新闻交替，避免每次都报同一类。"""
        self._ambient_rot = (self._ambient_rot + 1) % 2
        if self._ambient_rot == 1:
            if not self.speak_weather():
                self.speak_news()
        else:
            if not self.speak_news():
                self.speak_weather()

    # ================= v2.9.0 体贴行为（全屏躲避 / 拔电省电） =================
    def _on_guard(self):
        if self.config.get("fs_hide_on", True):
            try:
                fs = awareness.foreground_fullscreen(int(self.pet.winId()))
            except Exception:  # noqa: BLE001
                fs = False
            if fs and not self._fs_hidden and not self._user_hidden:
                self._fs_hidden = True
                self.pet.hide()
            elif not fs and self._fs_hidden:
                self._fs_hidden = False
                if not self._user_hidden:
                    self.pet.show()
        if self.config.get("power_saver_on", True):
            bat = awareness.on_battery()
            if self._was_battery is None:
                self._was_battery = bat
            elif bat != self._was_battery:
                self._was_battery = bat
                if bat:
                    self.stop_local_llm()
                    self.pet.bubble.show_text("拔电了，我把本地大模型歇了，先省点电。", 4200)
                else:
                    if self.config.get("llm_autostart"):
                        QTimer.singleShot(1500, self._warm_local_llm)
                    self.pet.bubble.show_text("接上电了，大模型叫醒了。", 3000)

    # ================= 番茄钟 =================
    def start_tomato(self, minutes: int):
        self.tomato_left = minutes * 60
        self.tomato_timer.start()
        self.panel and self.panel.set_tomato(self._fmt_tomato())
        self.pet.bubble.show_text(f"好，专注 {minutes} 分钟，本鱼盯着你。", 2200)

    def stop_tomato(self):
        self.tomato_timer.stop()
        self.tomato_left = 0
        self.panel and self.panel.set_tomato("未开始")

    def _on_tomato_tick(self):
        self.tomato_left -= 1
        if self.tomato_left <= 0:
            self.tomato_timer.stop()
            self.state.add_exp(20)
            self.state.mood = min(100, self.state.mood + 10)
            self.beep("done")
            self.pet.bubble.show_text(lines.pick(lines.TOMATO_DONE), 3500)
            self.pet.set_expression("happy", 3000)
            self.panel and self.panel.set_tomato("已完成！")
            self.refresh_panel()
        else:
            self.panel and self.panel.set_tomato(self._fmt_tomato())

    def _fmt_tomato(self):
        m, s = divmod(self.tomato_left, 60)
        return f"{m:02d}:{s:02d}"

    # ================= 提醒开关 =================
    def toggle_water(self, on: bool):
        self.config["water_on"] = on
        if on:
            self.water_timer.start()
        else:
            self.water_timer.stop()
        self.save_config()

    def toggle_sedentary(self, on: bool):
        self.config["sedentary_on"] = on
        if on:
            self.sedentary_timer.start()
        else:
            self.sedentary_timer.stop()
        self.save_config()

    def toggle_sound(self, on: bool):
        self.config["sound_on"] = on
        self.audio.set_enabled(on)
        self.save_config()

    def set_theme(self, mode: str):
        """主题：auto / light / dark。面板和内联配色一起换，不用重开。"""
        if mode not in ("auto", "light", "dark"):
            return
        self.config["theme"] = mode
        self.save_config()
        if self.panel is not None:
            try:
                self.panel.apply_theme()
            except Exception:
                pass

    def set_voice_profile(self, key: str):
        """切换真人音色提炼档位（只调 Edge TTS 的音调参数，不做克隆）。"""
        self.config["voice_profile"] = key
        self.save_config()
        try:
            import voice_profile as vp
            if key == "off":
                text = "音色回到原生 TTS，不再往真人样本靠。"
            else:
                persona_key = self.config.get("persona", pers.DEFAULT_PERSONA)
                voice = (pers.get(persona_key) or {}).get("voice", "zh-CN-XiaoxiaoNeural")
                text = vp.describe(voice, key)
            self.pet.bubble.show_text(text, 5200)
        except Exception:
            pass
        self.pet.set_expression("happy", 2500)

    def _on_water(self):
        self.pet.bubble.show_text(lines.pick(lines.WATER), 4000)
        self.pet.set_expression("curious", 3000)
        self.beep("water")
        self.water_timer.start()

    def _on_sedentary(self):
        self.pet.bubble.show_text(lines.pick(lines.SEDENTARY), 4000)
        self.pet.set_expression("shy", 3000)
        self.beep("sedentary")
        self.sedentary_timer.start()

    # ================= 周期衰减 / 金币 / 闲聊 =================
    def _on_decay(self):
        # v3.0.0：睡着时基础代谢降到 35%，心情只在长时间无互动时才掉
        sleeping = self.pet.state == "sleep"
        low = self.state.decay(sleeping=sleeping)
        if low and random.random() < 0.5:
            self.pet.set_expression("sleepy", 3000)
            self.pet.bubble.show_text(lines.pick(lines.SLEEPY), 2600)
        self.refresh_panel()

    def _on_idle_talk(self):
        if self.config.get("chatter_on", True) and self.pet.state not in ("sleep", "drag"):
            self.pet.bubble.show_text(lines.pick(lines.CHAT_IDLE), 3000)

    # ================= 托盘 / 快捷键 =================
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        # v2.9.6 托盘统一用透明底 Q 版大肥鱼图标
        icon_path = asset_path(os.path.join("ui", "pet_flat.ico"))
        if not os.path.exists(icon_path):
            icon_path = asset_path(os.path.join("ui", "pet.ico"))
        if not os.path.exists(icon_path):
            icon_path = asset_path(SKINS[self.config.get("skin", "default")][1])
        icon = QIcon(icon_path)
        self.app.setWindowIcon(icon)
        self.tray.setIcon(icon)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_panel = QAction(icon, "设置", menu)
        act_panel.triggered.connect(self.open_panel)
        # v3.0.0：剪贴板搜索项与单独的「隐藏桌宠」已按用户要求删除。
        # 隐藏统一走「显示 / 隐藏桌宠」一个开关，不再留两个功能重复的入口。
        act_show = QAction("显示 / 隐藏桌宠（Alt+Shift+F）", menu)
        act_show.triggered.connect(self.toggle_visibility)
        act_auto = QAction("自主行动", menu)
        act_auto.setCheckable(True)
        act_auto.setChecked(self.config.get("auto_on", True))
        act_auto.toggled.connect(self.set_auto)
        # v2.9.3 静音模式：没任务时的闲聊/播报只出字不出声
        act_mute = QAction("静音模式（闲聊不发声）", menu)
        act_mute.setCheckable(True)
        act_mute.setChecked(self.config.get("mute_idle", True))
        act_mute.toggled.connect(self.set_mute_idle)
        act_quit = QAction("退出程序", menu)
        act_quit.triggered.connect(self.quit_app)
        # v3.0.14：菜单里「设置」（顶部带图标）与「设置…」重复，删掉后者。
        # 主题等设置都在控制面板里，点「设置」直达即可。
        menu.addAction(act_panel)
        menu.addSeparator()
        menu.addAction(act_show)
        menu.addSeparator()
        menu.addAction(act_auto)
        menu.addAction(act_mute)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        # v2.9.3 修 bug：activated 会连右键(Context)一起触发，原先右键托盘图标就顺手把桌宠藏了
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        """只有左键单击才切换显示；右键只弹菜单，不碰桌宠。"""
        try:
            trigger = QSystemTrayIcon.ActivationReason.Trigger
        except AttributeError:
            trigger = QSystemTrayIcon.Trigger
        if reason == trigger:
            self.toggle_visibility()

    def set_mute_idle(self, on: bool):
        self.config["mute_idle"] = bool(on)
        self.save_config()

    def ask_search_clipboard(self):
        """v2.9.6：读剪贴板前必须先问用户，同意才读；读完不留存。"""
        box = QMessageBox(self.panel if self.panel is not None else None)
        box.setWindowTitle("读取剪贴板")
        box.setIcon(QMessageBox.Question)
        box.setText("要用我剪贴板里的内容去搜一下吗？\n只会读这一次，读完不保存。")
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)   # 桌宠是置顶无边框窗，弹框要压得住
        ok = box.addButton("同意，去搜", QMessageBox.AcceptRole)
        box.addButton("不用了", QMessageBox.RejectRole)
        box.setDefaultButton(box.buttons()[1])
        box.exec()
        if box.clickedButton() is not ok:
            self.pet.bubble.show_text("好，那我不动剪贴板。", 1600)
            return
        self.search_in_browser()

    def search_in_browser(self):
        """把剪贴板内容丢给本机浏览器搜索；没装外部浏览器就退回默认浏览器。"""
        import urllib.parse
        from PySide6.QtGui import QGuiApplication

        text = (QGuiApplication.clipboard().text() or "").strip()
        if not text:
            self.pet.bubble.show_text("先复制一段要查的东西，我再帮你搜～", 1800)
            return
        text = " ".join(text.split())[:180]
        url = "https://www.bing.com/search?q=" + urllib.parse.quote(text)
        exe, family = paths.pick_browser()
        if exe:
            args = paths.browser_args(exe, url)
            if QProcess.startDetached(exe, args):
                name = os.path.basename(exe).replace(".exe", "")
                self.pet.bubble.show_text(f"丢进 {name} 帮你查了～", 1600)
                return
        # 没探测到外部浏览器，或启动失败：交给系统默认浏览器（不管用户装的是哪个都能开）
        QDesktopServices.openUrl(QUrl(url))
        self.pet.bubble.show_text("用默认浏览器打开搜索页了", 1600)

    def _check_install_model_flag(self):
        """安装时勾了「要，装一个」→ 首次启动自动下默认模型，下完删标记。"""
        try:
            flag = os.path.join(os.path.dirname(sys.executable), "want_local_model.flag")
        except Exception:  # noqa: BLE001
            return
        if not os.path.exists(flag):
            return
        try:
            os.remove(flag)
        except OSError:
            pass
        QTimer.singleShot(4000, self._auto_get_local_model)

    def _auto_get_local_model(self):
        """安装时选了「装一个」：按本机配置挑最搭的那个，不再固定 4B。"""
        item, why = hardware.best()
        if not item:
            item = models_catalog.by_id("qwen3-4b")
        if not item:
            return
        p = os.path.join(self.models_dir(), item["file"])
        if os.path.exists(p):
            self.pet.bubble.show_text(f"本地模型已经在了（{item['name']}），能离线聊。", 3200)
            return
        self.pet.bubble.show_text(f"按你的机器挑了 {item['name']}：{why}", 5000)
        try:
            self.download_model(item["id"])
        except Exception as e:  # noqa: BLE001
            self.pet.bubble.show_text(f"本地模型没下成：{str(e)[:30]}", 4000)

    def _build_hotkey(self):
        sc = QShortcut(QKeySequence("Alt+Shift+F"), self.app)
        sc.setContext(Qt.ApplicationShortcut)
        sc.activated.connect(self.toggle_visibility)

        # Ctrl+Alt+V：语音说一句
        scv = QShortcut(QKeySequence("Ctrl+Alt+V"), self.app)
        scv.setContext(Qt.ApplicationShortcut)
        scv.activated.connect(self.voice_listen)

    def show_pet(self):
        """启动屏结束后统一露脸（v2.9.5）：位置在构造时已 clamp，直接 show 再置顶。"""
        self.pet.show()
        self.pet.raise_()

    def toggle_visibility(self):
        if self.pet.isVisible():
            self._user_hidden = True
            self.pet.hide()
        else:
            self._user_hidden = False
            self._fs_hidden = False
            self.pet.show()
            self.pet.raise_()

    def quit_app(self):
        for w in (self.worker, self.know_worker, self.clean_worker, self.update_worker,
                  self.llm_worker, self.scan_worker, self.ambient_worker, self.update_dl,
                  self.guard_worker, self.defender_worker):
            if w is not None and w.isRunning():
                try:
                    w.stop()
                except Exception:  # noqa: BLE001
                    pass
                if not w.wait(2000) and w.isRunning():
                    # 联网请求仍阻塞在 socket 上时，兜底强停线程，避免程序退不掉
                    w.terminate()
                    w.wait(1000)
        if self.icon_layout is not None:
            self.icon_layout.restore()
            self.icon_layout = None
        try:
            self.usage.save(force=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            self.llm.stop()
        except Exception:  # noqa: BLE001
            pass
        self.save_config()
        try:
            self.memory.close()
        except Exception:  # noqa: BLE001
            pass
        self.tray.hide()
        self.app.quit()


def main():
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("WhaleGirlPet")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    shm = QSharedMemory(APP_KEY)
    if not shm.create(1):
        QMessageBox.information(None, APP_NAME, "桌宠已经在运行啦～")
        return 0

    # v2.9.8：上次储存位置迁移时被占用的旧文件，这里再清一遍（此时数据库还没开）
    try:
        paths.cleanup_pending()
    except Exception:  # noqa: BLE001
        pass

    # v3.0.4：清掉上次异常退出留下的 dafeiyu-server 孤儿进程（实测残留 2.39GB 内存）
    try:
        killed = local_llm.kill_stray_servers()
        if killed:
            print(f"[startup] 清理残留推理进程 {killed} 个")
    except Exception:  # noqa: BLE001
        pass

    # v2.9.6 先关掉 PyInstaller 的原生启动图（只在 onefile 打包后存在），
    # 交给下面自绘的透明启动屏接管，避免两张图叠在一起
    try:
        import pyi_splash  # type: ignore[import-not-found]
        pyi_splash.close()
    except Exception:  # noqa: BLE001
        pass

    # v2.9.5 启动屏：先把「鲸鱼娘加载中」画出来，初始化完再一次性露桌宠。
    # 以前是 PetWindow 构造里直接 show()，接着各组件陆续初始化、6 秒后还可能弹更新框。
    keep = {"splash": splash_mod.LoadingSplash(), "controller": None}
    keep["splash"].show()
    app.processEvents()

    def _boot_log(msg: str):
        """v3.0.6：启动过程写时间线到 runtime/startup.log，方便下次排查卡在哪一步。"""
        try:
            p = os.path.join(paths.runtime_dir(), "startup.log")
            with open(p, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
        except Exception:  # noqa: BLE001
            pass

    def _boot_step2():
        keep["splash"].set_step("正在读取配置与记忆…")
        _boot_log("step2 开始：构造 Controller")
        try:
            keep["controller"] = Controller(app, defer_show=True)
        except Exception as e:  # noqa: BLE001
            _boot_log(f"step2 异常：{e!r}")
            keep["splash"]._hard_close()
            QMessageBox.critical(None, APP_NAME, f"启动失败：{e}")
            app.quit()
            return
        _boot_log("step2 完成")
        QTimer.singleShot(320, _boot_step3)

    def _boot_step3():
        keep["splash"].set_step("正在加载形象与语音…")
        _boot_log("step3")
        QTimer.singleShot(280, _boot_step4)

    def _boot_step4():
        _boot_log("step4 开始：露出桌宠")
        try:
            keep["controller"].show_pet()
            _boot_log("step4 桌宠已显示")
        except Exception as e:  # noqa: BLE001
            # 桌宠没露出来也要把启动屏收掉，否则屏幕上留一个卡住的大肥鱼
            _boot_log(f"step4 show_pet 异常：{e!r}")
        finally:
            try:
                keep["splash"].finish()
                _boot_log("step4 启动屏已请求淡出")
            except Exception:  # noqa: BLE001
                keep["splash"]._hard_close()
                _boot_log("step4 启动屏强制关闭")

    _boot_log("step1 启动屏已显示")
    QTimer.singleShot(260, _boot_step2)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
