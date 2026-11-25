# -*- coding: utf-8 -*-
"""v2.0.0 新增面板页：语音人格 / 记忆与知识 / 安全体检 / 账号与形态 / 定时。

页面逻辑放这里，panel.py 只负责 addTab，避免主面板继续膨胀。
每个 tab_* 函数接收 ControlPanel 实例，返回 QWidget，并把需要刷新的控件挂到 panel 上。
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QProgressBar, QPushButton,
                               QSlider, QTableWidget, QTableWidgetItem, QTextEdit,
                               QVBoxLayout, QWidget)

import persona as pers
from paths import AUDIO_ACTION_LABELS, AUDIO_ACTIONS, account_dir, voice_dir


def _row(*widgets):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    for x in widgets:
        lay.addWidget(x)
    return w


def _btn(text: str, slot):
    b = QPushButton(text)
    if slot is not None:
        b.clicked.connect(lambda _=False: slot())
    return b


def _chk(text: str, checked: bool = False, name: str = ""):
    c = QCheckBox(text)
    c.setChecked(bool(checked))
    if name:
        c.setObjectName(name)
    return c


# ---------------- 语音与人格 ----------------
def tab_voice(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel("音频库：音色、语速、音量、本地音效都在这里。换音色只换语气和口音，不动她的性格。"))
    panel.lbl_voice = QLabel("")
    panel.lbl_voice.setWordWrap(True)
    panel.lbl_voice.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_voice)
    lay.addWidget(_row(
        _btn("刷新麦克风", panel._refresh_voice),
    ))

    cmd_hint = QLabel(
        "能直接听懂的：更新病毒库 / 安全体检 / 清理垃圾 / 擦桌面 / 做家务 / 满屏跑 / 跳舞 / 摸头 /"
        " 睡觉 / 起床 / 换装 / 萝莉 / 成熟 / 静音 / 开声音 / 番茄钟 / 喝水提醒 / 久坐提醒 /"
        " 跟着我 / 别跟了 / 碎碎念 / 自主行动 / 置顶 / 变大 / 变小 / 大号 / 小号 / 检查更新 /"
        " 停下 / 打开面板 / 关掉面板 / 躲起来 / 出来。\n"
        "没对上这些词的话，原话交给对话模型处理（设提醒、开文件、查天气都走这条路）。"
    )
    cmd_hint.setWordWrap(True)
    cmd_hint.setStyleSheet("color:#777;font-size:12px;")
    lay.addWidget(cmd_hint)

    lay.addWidget(QLabel("音色库（8 种；只换声音、口音和说话习惯，不改她的性格）"))

    panel.cmb_persona = QComboBox()
    for key, name in pers.persona_index():
        p = pers.get(key)
        tag = "真音色" if p.get("real_voice") else "近似音色"
        panel.cmb_persona.addItem(f"{name}　[{tag}]", key)
    idx = panel.cmb_persona.findData(ctl.config.get("persona", pers.DEFAULT_PERSONA))
    if idx >= 0:
        panel.cmb_persona.setCurrentIndex(idx)
    panel.cmb_persona.currentIndexChanged.connect(panel._on_persona_change)
    lay.addWidget(panel.cmb_persona)

    panel.lbl_persona_note = QLabel("")
    panel.lbl_persona_note.setWordWrap(True)
    panel.lbl_persona_note.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_persona_note)

    lay.addWidget(_row(
        _btn("试听一句", panel._preview_persona),
        _btn("清理语音缓存", panel._clear_tts_cache),
    ))

    # ---- 联网音色实验台：拉取音色 → 试听 → 一句话指令微调 → 存为我的音色 ----
    lay.addWidget(QLabel("联网音色实验台（拉取微软音色库 → 试听 → 用一句话指令微调）"))
    panel.cmb_net_voice = QComboBox()
    panel.cmb_net_voice.addItem("（先点「拉取音色列表」）", "")
    lay.addWidget(panel.cmb_net_voice)
    lay.addWidget(_row(
        _btn("拉取音色列表", panel._fetch_voice_list),
        _btn("试听选中", panel._preview_net_voice),
        _btn("存为我的音色", panel._save_net_voice),
    ))

    panel.sl_pitch = QSlider(Qt.Horizontal)
    panel.sl_pitch.setRange(-60, 60)
    panel.sl_rate = QSlider(Qt.Horizontal)
    panel.sl_rate.setRange(-50, 50)
    panel.sl_vol = QSlider(Qt.Horizontal)
    panel.sl_vol.setRange(10, 100)
    panel.sl_vol.setValue(80)
    _k0 = ctl.config.get("persona", pers.DEFAULT_PERSONA)
    _p0 = pers.get(_k0) or {}
    panel.sl_pitch.setValue(int(_p0.get("pitch", 0)))
    panel.sl_rate.setValue(int(_p0.get("rate", 0)))
    lay.addWidget(_row(QLabel("音高"), panel.sl_pitch, QLabel("低 ← → 高")))
    lay.addWidget(_row(QLabel("语速"), panel.sl_rate, QLabel("慢 ← → 快")))
    lay.addWidget(_row(QLabel("音量"), panel.sl_vol, QLabel("10–100")))
    panel.lbl_vparams = QLabel("")
    panel.lbl_vparams.setWordWrap(True)
    panel.lbl_vparams.setStyleSheet("color:#2f6f4f;font-size:12px;")
    lay.addWidget(panel.lbl_vparams)
    panel.lbl_vnote = QLabel("")
    panel.lbl_vnote.setWordWrap(True)
    panel.lbl_vnote.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_vnote)
    for _sl in (panel.sl_pitch, panel.sl_rate, panel.sl_vol):
        _sl.valueChanged.connect(lambda _v: panel._sync_vparams())
    lay.addWidget(QLabel("优化指令（说人话就行：再尖一点 / 慢 10% / 音高压到 20 / 音量 60 / 换回默认）"))
    panel.ed_voice_cmd = QLineEdit()
    panel.ed_voice_cmd.setPlaceholderText("例：尖一点，慢一点，音量 70")
    lay.addWidget(_row(panel.ed_voice_cmd,
                       _btn("执行指令", panel._apply_voice_cmd),
                       _btn("重置", panel._reset_vparams)))
    panel._sync_vparams()

    panel.chk_tts = QCheckBox("开启方言语音（Edge TTS）")
    panel.chk_tts.setChecked(bool(ctl.config.get("tts_on")))
    panel.chk_tts.toggled.connect(panel._on_tts_toggle)
    lay.addWidget(panel.chk_tts)

    panel.chk_tts_online = QCheckBox("允许联网合成（文本会发给微软，合成后缓存在本地）")
    panel.chk_tts_online.setChecked(bool(ctl.config.get("tts_online", True)))
    panel.chk_tts_online.toggled.connect(lambda v: ctl.set_tts(panel.chk_tts.isChecked(), v))
    lay.addWidget(panel.chk_tts_online)

    lay.addWidget(panel._build_audio_box())

    lay.addStretch(1)
    return w


# ---------------- 模型库 ----------------
def tab_models(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    tip = QLabel("内置下载地址（走 hf-mirror 镜像，全部实测可下）。\n"
                 "只有标「可跑」的单文件模型给一键下载；百 GB 级分片模型只给仓库页，避免误下。")
    tip.setWordWrap(True)
    tip.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(tip)

    panel.lbl_hw = QLabel("")
    panel.lbl_hw.setWordWrap(True)
    panel.lbl_hw.setStyleSheet("color:#2f6f4f;font-size:12px;")
    lay.addWidget(panel.lbl_hw)
    panel.lbl_gpu = QLabel("")
    panel.lbl_gpu.setWordWrap(True)
    panel.lbl_gpu.setStyleSheet("color:#4a3f8a;font-size:12px;")
    lay.addWidget(panel.lbl_gpu)
    lay.addWidget(_row(_btn("重新检测配置", panel._refresh_hw)))

    panel.lbl_cur_model = QLabel("")
    panel.lbl_cur_model.setWordWrap(True)
    lay.addWidget(panel.lbl_cur_model)

    # v3.0.9：去掉「只用 Ollama」——Ollama 那套在这台机上反复出问题，
    # 只留「自动」（Ollama 活着才用它、坏了自动退回）和「只用自带引擎」两项。
    panel.cmb_backend = QComboBox()
    panel.cmb_backend.addItem("自动（有可用的 Ollama 就用它，坏了/跑不动自动退回自带引擎）", "auto")
    panel.cmb_backend.addItem("只用自带引擎 dafeiyu（不经过 Ollama，推荐）", "dafeiyu_cpp")
    panel.cmb_backend.currentIndexChanged.connect(lambda _: panel._on_backend_change())
    lay.addWidget(_row(QLabel("本地推理后端"), panel.cmb_backend))

    # v3.0.9：调度状态一行看全（当前模型/端口/是否排队/上次错误/有没有自动降级）
    panel.lbl_engine = QLabel("")
    panel.lbl_engine.setWordWrap(True)
    panel.lbl_engine.setStyleSheet("color:#555;font-size:12px;")
    lay.addWidget(panel.lbl_engine)

    panel.lst_models = QListWidget()
    panel.lst_models.setMinimumHeight(268)
    lay.addWidget(panel.lst_models)

    net_tip = QLabel("联网添加模型：粘贴一个 .gguf 直链（https://…），下完会自动进上面的「已安装」。\n"
                     "hf-mirror 的仓库页地址也能直接贴，程序会自己找里面的 .gguf。")
    net_tip.setWordWrap(True)
    net_tip.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(net_tip)
    panel.ed_model_url = QLineEdit()
    panel.ed_model_url.setPlaceholderText("https://hf-mirror.com/…/xxx.gguf")
    lay.addWidget(panel.ed_model_url)
    lay.addWidget(_row(_btn("下载到本地", panel._add_model_url),
                       _btn("打开模型目录", panel._open_model_dir),
                       _btn("添加模型文件夹", panel._add_model_dir),
                       _btn("刷新已安装", panel._refresh_models)))
    lay.addWidget(_row(_btn("检查 Ollama 能否真正生成", panel._check_ollama)))

    # ---- v3.0.8：Ollama 官方库（联网），下下来的就是 gguf，不用装 Ollama ----
    o_tip = QLabel("Ollama 官方库（联网）：点「刷新」重新抓 ollama.com/library 的模型清单与下载地址；"
                   "选中一个会填进下面的输入框，再点「查询并下载」。"
                   "下下来的是标准 gguf，交给自带引擎跑，全程不需要 Ollama。")
    o_tip.setWordWrap(True)
    o_tip.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(o_tip)
    panel.lst_ollama = QListWidget()
    panel.lst_ollama.setMinimumHeight(132)
    panel.lst_ollama.itemClicked.connect(panel._pick_ollama_item)
    lay.addWidget(panel.lst_ollama)
    panel.ed_ollama_ref = QLineEdit()
    panel.ed_ollama_ref.setPlaceholderText("qwen3.5:4b / gemma4:e2b / deepseek-coder:6.7b-instruct")
    lay.addWidget(panel.ed_ollama_ref)
    lay.addWidget(_row(_btn("刷新 Ollama 模型库（联网）", panel._refresh_ollama_lib),
                       _btn("查询并下载", panel._dl_ollama),
                       _btn("从本机 Ollama 导入", panel._import_ollama)))

    panel.pbar_model = QProgressBar()
    panel.pbar_model.setVisible(False)
    lay.addWidget(panel.pbar_model)

    panel.lbl_dl = QLabel("")
    panel.lbl_dl.setWordWrap(True)
    panel.lbl_dl.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_dl)

    lay.addWidget(_row(_btn("下载选中", panel._dl_model),
                       _btn("取消下载", panel._cancel_dl),
                       _btn("使用此模型", panel._use_model)))
    lay.addWidget(_row(_btn("删除本地文件", panel._del_model),
                       _btn("复制下载链接", panel._copy_link),
                       _btn("打开仓库页", panel._open_repo)))
    lay.addStretch(1)
    return w


# ---------------- 记忆与知识库 ----------------
def tab_memory(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    panel.lbl_mem = QLabel("")
    panel.lbl_mem.setWordWrap(True)
    lay.addWidget(panel.lbl_mem)

    lay.addWidget(QLabel("她记住的关于你的事："))
    panel.lst_facts = QListWidget()
    panel.lst_facts.setMaximumHeight(110)
    lay.addWidget(panel.lst_facts)
    lay.addWidget(_row(
        _btn("清空记忆", panel._forget_memory),
        _btn("刷新", panel._refresh_memory),
        _btn("备份到本地…", panel._backup_memory),
        _btn("导出可读清单…", panel._export_memory_readable),
    ))
    lay.addWidget(_chk("用记忆增强对话", True, "chk_mem_on"))

    lay.addWidget(QLabel("知识库（导入 txt / md / csv，聊天时自动检索）"))
    panel.lbl_kb = QLabel("")
    lay.addWidget(panel.lbl_kb)
    panel.lst_kb = QListWidget()
    panel.lst_kb.setMaximumHeight(130)
    lay.addWidget(panel.lst_kb)
    lay.addWidget(_row(
        _btn("导入文件", panel._import_kb),
        _btn("删除选中", panel._remove_kb),
    ))
    lay.addStretch(1)
    return w


# ---------------- 安全体检 ----------------
def tab_security(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    tip = QLabel("只做只读检查：Defender 状态、开机自启项、常见后门端口、可疑进程。\n"
                 "不改系统、不删文件；需要深度查杀请点「打开 Defender」。")
    tip.setWordWrap(True)
    tip.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(tip)
    lay.addWidget(_row(
        _btn("开始体检", panel._run_scan),
        _btn("更新病毒库", panel._update_signatures),
        _btn("打开 Defender", panel._open_defender),
    ))
    panel.txt_scan = QTextEdit()
    panel.txt_scan.setReadOnly(True)
    panel.txt_scan.setStyleSheet("font-family:Consolas,'Microsoft YaHei';font-size:12px;")
    lay.addWidget(panel.txt_scan)
    return w


# ---------------- 账号与形态 ----------------
def tab_account(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    # v2.9.7：形态选择搬到「设置 → 桌宠行为」，这页只管账号
    tip_form = QLabel("形态（成熟 / 萝莉）已经搬到「设置 → 桌宠行为」，这页只留账号。")
    tip_form.setWordWrap(True)
    tip_form.setStyleSheet("color:#888;font-size:11px;")
    lay.addWidget(tip_form)

    lay.addWidget(QLabel("本地档案账号（数据各存各的，全部在本机）"))
    panel.lbl_acct = QLabel("")
    lay.addWidget(panel.lbl_acct)
    panel.lst_acct = QListWidget()
    lay.addWidget(panel.lst_acct)
    panel.ed_acct = QLineEdit()
    panel.ed_acct.setPlaceholderText("新账号名字")
    lay.addWidget(panel.ed_acct)
    lay.addWidget(_row(
        _btn("新建", panel._new_account),
        _btn("切换", panel._switch_account),
        _btn("改名", panel._rename_account),
        _btn("删除", panel._delete_account),
    ))
    lay.addWidget(_row(_chk("新账号复制当前档案", True, "chk_copy_acct")))
    lay.addStretch(1)
    return w


# ---------------- 定时 ----------------
def build_schedule(panel, lay) -> None:
    """把「定时任务」整组塞进调用方给的布局里（v2.9.8 与番茄钟/提醒合并成同页）。"""
    ctl = panel.ctl
    panel.chk_night = QCheckBox("22:00 提醒休息（没关机会每 15 分钟再催，最多 4 次）")
    panel.chk_night.setChecked(ctl.night_on())
    panel.chk_night.toggled.connect(ctl.set_night_on)
    lay.addWidget(panel.chk_night)

    panel.lst_sched = QListWidget()
    # v3.0.0：列表与下方使用情况都改成可伸缩，撑满「定时任务」模块，不留底部空白
    panel.lst_sched.setMinimumHeight(96)
    lay.addWidget(panel.lst_sched, 2)

    row = QHBoxLayout()
    panel.cmb_sched_kind = QComboBox()
    panel.cmb_sched_kind.addItem("每天", "daily")
    panel.cmb_sched_kind.addItem("一次性", "once")
    panel.cmb_sched_kind.addItem("每周", "weekly")
    panel.ed_sched_when = QLineEdit()
    panel.ed_sched_when.setPlaceholderText("21:30")
    panel.ed_sched_text = QLineEdit()
    panel.ed_sched_text.setPlaceholderText("提醒内容")
    row.addWidget(panel.cmb_sched_kind)
    row.addWidget(panel.ed_sched_when)
    row.addWidget(panel.ed_sched_text)
    lay.addLayout(row)
    lay.addWidget(_row(
        _btn("添加", panel._add_sched),
        _btn("删除选中", panel._del_sched),
        _btn("启用/停用", panel._toggle_sched),
    ))

    panel.txt_usage = QTextEdit()
    panel.txt_usage.setReadOnly(True)
    panel.txt_usage.setMinimumHeight(150)
    panel.txt_usage.setStyleSheet("font-size:13px;")
    lay.addWidget(panel.txt_usage, 3)
    lay.addWidget(_row(_btn("刷新昨天使用情况", panel._refresh_usage)))


def tab_schedule(panel) -> QWidget:
    """兼容旧调用：单独一页的定时任务。"""
    w = QWidget()
    lay = QVBoxLayout(w)
    build_schedule(panel, lay)
    lay.addStretch(1)
    return w


# ---------------- 音频库 ----------------
AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma")


def tab_audio(panel) -> QWidget:
    """把音效与语音缓存都列出来，能试听、能绑到动作、能删。"""
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)

    lay.addWidget(QLabel("音频库（全部本地文件，不联网）"))
    panel.lbl_audio_lib = QLabel("")
    panel.lbl_audio_lib.setWordWrap(True)
    panel.lbl_audio_lib.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_audio_lib)

    panel.tbl_audio = QTableWidget(0, 4)
    panel.tbl_audio.setHorizontalHeaderLabels(["文件", "类别", "绑定动作", "大小"])
    panel.tbl_audio.setSelectionBehavior(QAbstractItemView.SelectRows)
    panel.tbl_audio.setSelectionMode(QAbstractItemView.SingleSelection)
    panel.tbl_audio.setEditTriggers(QAbstractItemView.NoEditTriggers)
    panel.tbl_audio.verticalHeader().setVisible(False)
    panel.tbl_audio.horizontalHeader().setStretchLastSection(True)
    panel.tbl_audio.setColumnWidth(0, 300)
    panel.tbl_audio.setColumnWidth(1, 90)
    panel.tbl_audio.setColumnWidth(2, 120)
    lay.addWidget(panel.tbl_audio, 1)

    panel.cmb_lib_action = QComboBox()
    for key, label in AUDIO_ACTIONS:
        panel.cmb_lib_action.addItem(label, key)
    lay.addWidget(_row(
        QLabel("绑定到："),
        panel.cmb_lib_action,
        _btn("试听选中", panel._play_selected_audio),
        _btn("绑定", panel._bind_selected_audio),
    ))
    lay.addWidget(_row(
        _btn("导入音频…", panel._import_audio_to_lib),
        _btn("删除选中文件", panel._del_selected_audio),
        _btn("打开音频目录", panel._open_voice_dir),
        _btn("刷新音频库", panel._refresh_audio_lib),
    ))

    panel._refresh_audio_lib()
    lay.addStretch(0)
    return w



