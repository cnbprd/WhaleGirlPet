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
                               QTableWidget, QTableWidgetItem, QTextEdit,
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
    lay.addWidget(QLabel("输入方式（说一句就行，走的是同一个能力层）"))
    panel.lbl_voice = QLabel("")
    panel.lbl_voice.setWordWrap(True)
    panel.lbl_voice.setStyleSheet("color:#666;font-size:12px;")
    lay.addWidget(panel.lbl_voice)
    lay.addWidget(_row(
        _btn("语音说一句（Ctrl+Alt+V）", ctl.voice_listen),
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

    lay.addWidget(QLabel("人格腔调（8 种，声音与用词一起换）"))

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

    panel.chk_tts = QCheckBox("开启方言语音（Edge TTS）")
    panel.chk_tts.setChecked(bool(ctl.config.get("tts_on")))
    panel.chk_tts.toggled.connect(panel._on_tts_toggle)
    lay.addWidget(panel.chk_tts)

    panel.chk_tts_online = QCheckBox("允许联网合成（文本会发给微软，合成后缓存在本地）")
    panel.chk_tts_online.setChecked(bool(ctl.config.get("tts_online", True)))
    panel.chk_tts_online.toggled.connect(lambda v: ctl.set_tts(panel.chk_tts.isChecked(), v))
    lay.addWidget(panel.chk_tts_online)

    lay.addWidget(QLabel("本地大模型（离线推理，云端不可用时兜底）"))
    panel.lbl_llm = QLabel("")
    panel.lbl_llm.setWordWrap(True)
    lay.addWidget(panel.lbl_llm)
    lay.addWidget(_row(
        _btn("启动本地模型", panel._start_llm),
        _btn("停止", panel._stop_llm),
        _btn("刷新状态", panel._refresh_llm),
    ))
    panel.chk_llm = QCheckBox("优先用本地模型回答")
    panel.chk_llm.setChecked(bool(ctl.config.get("llm_on", True)))
    panel.chk_llm.toggled.connect(panel._on_llm_toggle)
    lay.addWidget(panel.chk_llm)

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

    panel.lst_models = QListWidget()
    panel.lst_models.setMinimumHeight(268)
    lay.addWidget(panel.lst_models)

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
    lay.addWidget(QLabel("形态（萝莉保留为第二形态）"))
    panel.cmb_form = QComboBox()
    for fk, flabel in (("mature", "成熟形态"), ("loli", "萝莉形态")):
        panel.cmb_form.addItem(flabel, fk)
    cur = ctl.config.get("form", "mature")
    i = panel.cmb_form.findData(cur)
    if i >= 0:
        panel.cmb_form.setCurrentIndex(i)
    panel.cmb_form.currentIndexChanged.connect(panel._on_form_change)
    lay.addWidget(panel.cmb_form)

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
def tab_schedule(panel) -> QWidget:
    ctl = panel.ctl
    w = QWidget()
    lay = QVBoxLayout(w)
    panel.chk_night = QCheckBox("22:00 提醒休息（没关机会每 15 分钟再催，最多 4 次）")
    panel.chk_night.setChecked(ctl.night_on())
    panel.chk_night.toggled.connect(ctl.set_night_on)
    lay.addWidget(panel.chk_night)

    lay.addWidget(QLabel("定时任务"))
    panel.lst_sched = QListWidget()
    panel.lst_sched.setMaximumHeight(150)
    lay.addWidget(panel.lst_sched)

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

    lay.addWidget(QLabel("昨天电脑使用情况"))
    panel.txt_usage = QTextEdit()
    panel.txt_usage.setReadOnly(True)
    panel.txt_usage.setMaximumHeight(120)
    lay.addWidget(panel.txt_usage)
    lay.addWidget(_row(_btn("刷新", panel._refresh_usage)))

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



