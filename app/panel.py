# -*- coding: utf-8 -*-
"""控制面板：养成数值、投喂、换装、大小、番茄钟、提醒、聊天、打工任务、AI 后端、音频与自主行动。"""
import os

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QScrollArea, QSlider, QStackedWidget,
                               QTabWidget, QTableWidgetItem, QTextEdit,
                               QVBoxLayout, QWidget)

import models_catalog
import panel_v2
import paths
import persona as pers
import theme
import voice_tweak
from paths import (APP_VERSION, AUDIO_ACTIONS, AUDIO_ACTION_LABELS,
                   SIZE_LEVELS, SKINS)
from state import SNACKS
from tasks import TASK_DEFS


class _VoiceListWorker(QThread):
    """后台拉取微软 Edge TTS 音色库（联网，不能阻塞界面）。"""
    got = Signal(list)
    err = Signal(str)

    def run(self):  # noqa: D102
        try:
            import asyncio

            import edge_tts
            voices = asyncio.run(edge_tts.list_voices())
            self.got.emit(list(voices or []))
        except Exception as e:  # noqa: BLE001
            self.err.emit(str(e)[:140])


class ControlPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.ctl = controller
        self.setWindowTitle("鲸鱼娘桌宠 · 控制面板")
        self.setObjectName("PanelRoot")
        self.resize(560, 700)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        # 主题在 tabs 建完后再套（apply_theme 还要改聊天区等内联样式）

        # v2.9.3 macOS 风格：左侧 QListWidget 侧边栏 + 右侧 QStackedWidget 内容区
        # （QTabWidget 的 West 模式会把中文标签挤成竖排、宽度又不可控，换成列表侧栏）
        pages = [
            (self._tab_status(), "养成"),
            (self._tab_tasks(), "打工"),
            (self._tab_remind(), "番茄钟/提醒"),
            (self._tab_chat(), "聊天"),
            (self._tab_settings(), "设置"),
            (panel_v2.tab_voice(self), "语音人格"),
            (panel_v2.tab_models(self), "模型库"),
            (panel_v2.tab_security(self), "安全体检"),
            (panel_v2.tab_account(self), "账号形态"),
            (panel_v2.tab_schedule(self), "定时"),
        ]
        self.side = QListWidget()
        self.side.setObjectName("SideBar")
        self.side.setFixedWidth(138)
        self.side.setFocusPolicy(Qt.NoFocus)
        self.side.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.side.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.stack = QStackedWidget()
        for page, label in pages:
            self.side.addItem(QListWidgetItem(label))
            self.stack.addWidget(page)
        self.side.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.side.setCurrentRow(0)
        # 外部（shot_panel 等）按 tabs.setCurrentIndex / tabs.widget 访问，QStackedWidget 同名接口兼容
        self.tabs = self.stack

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 10)
        head = QHBoxLayout()
        head.setContentsMargins(12, 4, 12, 2)
        title = QLabel("鲸鱼娘桌宠")
        title.setObjectName("PanelTitle")
        ver = QLabel(f"v{APP_VERSION}")
        ver.setObjectName("PanelVer")
        head.addWidget(title)
        head.addStretch()
        head.addWidget(ver)
        root.addLayout(head)
        body = QHBoxLayout()
        body.setSpacing(10)
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self.side)
        body.addWidget(self.stack, 1)
        root.addLayout(body)
        self.apply_theme()

        try:
            self.load_chat_history()
        except Exception:  # noqa: BLE001
            pass

    def apply_theme(self):
        """按 config["theme"]（auto/light/dark）套整套配色，包括写死颜色的聊天区。"""
        mode = self.ctl.config.get("theme", theme.DEFAULT)
        self.setStyleSheet(theme.load_qss(mode))
        pal = theme.palette(mode)
        for name, style in (
            ("chat_scroll",
             f"QScrollArea{{background:{pal['chat_bg']};border:1px solid {pal['chat_border']};"
             f"border-radius:10px;}}QWidget#ChatBox{{background:{pal['chat_bg']};}}"),
            ("chat_input",
             f"QTextEdit{{background:{pal['input_bg']};border:1px solid {pal['input_border']};"
             f"border-radius:8px;padding:5px;}}"),
            ("chat_status", f"color:{pal['sub']};font-size:11px;"),
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                try:
                    widget.setStyleSheet(style)
                except Exception:
                    pass
        self.refresh()

    # ---------- 养成页 ----------
    def _tab_status(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名字："))
        self.ed_name = QLineEdit()
        self.ed_name.setMaxLength(12)
        self.ed_name.editingFinished.connect(
            lambda: self.ctl.set_name(self.ed_name.text()))
        name_row.addWidget(self.ed_name)
        lay.addLayout(name_row)

        self.lbl_level = QLabel()
        self.lbl_coins = QLabel()
        lay.addWidget(self.lbl_level)
        lay.addWidget(self.lbl_coins)

        self.bar_hunger = self._add_bar(lay, "饱食度")
        self.bar_mood = self._add_bar(lay, "心情")
        self.bar_intimacy = self._add_bar(lay, "亲密度")

        lay.addWidget(QLabel("投喂零食："))
        grid = QGridLayout()
        self.snack_btns = {}
        for i, (key, s) in enumerate(SNACKS.items()):
            btn = QPushButton(f"{s['emoji']} {s['name']}\n{s['cost']} 金币")
            btn.setMinimumHeight(52)
            btn.clicked.connect(lambda _=False, k=key: self.ctl.feed_snack(k))
            self.snack_btns[key] = btn
            grid.addWidget(btn, i // 2, i % 2)
        lay.addLayout(grid)

        lay.addWidget(QLabel("换装："))
        self.skin_combo = QComboBox()
        for key, (label, _) in SKINS.items():
            self.skin_combo.addItem(label, key)
        self.skin_combo.currentIndexChanged.connect(
            lambda _: self.ctl.set_skin(self.skin_combo.currentData()))
        lay.addWidget(self.skin_combo)

        lay.addWidget(QLabel("大小："))
        self.size_combo = QComboBox()
        for label in SIZE_LEVELS:
            self.size_combo.addItem(label)
        self.size_combo.currentIndexChanged.connect(
            lambda _: self.ctl.set_size(self.size_combo.currentText()))
        lay.addWidget(self.size_combo)
        lay.addStretch()
        return w

    def _add_bar(self, lay, name):
        bar = QLabel()
        lay.addWidget(bar)
        bar.setProperty("name", name)
        return bar

    # ---------- 打工页 ----------
    def _tab_tasks(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("打工任务：完成后结算金币与经验；学习任务联网取知识点，清理任务只动临时目录。"))

        self.task_rows = {}
        for key, defn in TASK_DEFS.items():
            box = QGroupBox(f"{defn['name']}（{defn['coins']} 金币 / {defn['exp']} 经验）")
            bl = QVBoxLayout(box)
            bl.addWidget(QLabel(defn["desc"]))
            row = QHBoxLayout()
            prog = QLabel("未开始")
            btn = QPushButton("开始")
            btn.clicked.connect(lambda _=False, k=key: self._task_button(k))
            row.addWidget(prog)
            row.addStretch()
            row.addWidget(btn)
            bl.addLayout(row)
            lay.addWidget(box)
            self.task_rows[key] = {"prog": prog, "btn": btn, "def": defn}

        lay.addWidget(QLabel("学习知识点："))
        self.task_fact = QTextEdit()
        self.task_fact.setReadOnly(True)
        self.task_fact.setMaximumHeight(110)
        lay.addWidget(self.task_fact)
        lay.addStretch()
        return w

    def _task_button(self, key: str):
        active = self.ctl.task_state()
        if active and active["key"] == key:
            self.ctl.cancel_task()
        elif active is None:
            self.ctl.start_task(key)

    def refresh_tasks(self):
        active = self.ctl.task_state()
        for key, row in self.task_rows.items():
            if active and active["key"] == key:
                row["btn"].setText("取消")
                row["prog"].setText(f"进行中… 剩余 {active['left']} 秒")
                for k2, r2 in self.task_rows.items():
                    if k2 != key:
                        r2["btn"].setEnabled(False)
            else:
                row["btn"].setText("开始")
                row["prog"].setText("未开始")
                row["btn"].setEnabled(active is None)

    def set_task_fact(self, text: str):
        self.task_fact.setPlainText(text)

    # ---------- 更新 ----------
    def _check_update(self):
        url = self.ed_update_url.text().strip()
        self.ctl.config["update_url"] = url
        self.ctl.save_config()
        self.ctl.check_update()

    def set_update_status(self, text: str):
        self.lbl_update.setText(text)

    # ---------- 提醒页 ----------
    def _tab_remind(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        box = QGroupBox("番茄钟")
        bl = QVBoxLayout(box)
        self.lbl_tomato = QLabel("未开始")
        self.lbl_tomato.setStyleSheet("font-size:18px;font-weight:bold;")
        bl.addWidget(self.lbl_tomato)
        row = QHBoxLayout()
        for mins in (25, 45, 60):
            b = QPushButton(f"{mins} 分钟")
            b.clicked.connect(lambda _=False, m=mins: self.ctl.start_tomato(m))
            row.addWidget(b)
        self.btn_tomato_stop = QPushButton("停止")
        self.btn_tomato_stop.clicked.connect(self.ctl.stop_tomato)
        row.addWidget(self.btn_tomato_stop)
        bl.addLayout(row)
        lay.addWidget(box)

        box2 = QGroupBox("日常提醒")
        r2 = QVBoxLayout(box2)
        self.chk_water = QCheckBox("喝水提醒（每 45 分钟）")
        self.chk_sedentary = QCheckBox("久坐提醒（每 60 分钟）")
        self.chk_sound = QCheckBox("音效 / 音频")
        self.chk_chatter = QCheckBox("碎碎念（无操作时自言自语）")
        self.chk_water.toggled.connect(self.ctl.toggle_water)
        self.chk_sedentary.toggled.connect(self.ctl.toggle_sedentary)
        self.chk_sound.toggled.connect(self.ctl.toggle_sound)
        self.chk_chatter.toggled.connect(self.ctl.toggle_chatter)
        r2.addWidget(self.chk_water)
        r2.addWidget(self.chk_sedentary)
        r2.addWidget(self.chk_sound)
        r2.addWidget(self.chk_chatter)
        lay.addWidget(box2)
        lay.addStretch()
        return w

    # ---------- 聊天页 ----------
    def _tab_chat(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        # 顶部工具条：导出 / 清屏
        bar = QHBoxLayout()
        self.lbl_chat_hint = QLabel("聊天记录只存在本机")
        self.lbl_chat_hint.setStyleSheet("color:#7c869c;font-size:11px;")
        btn_exp = QPushButton("导出记录")
        btn_exp.setToolTip("把当前聊天导出为 Markdown / TXT 文件")
        btn_exp.clicked.connect(self.export_chat)
        btn_clear = QPushButton("清屏")
        btn_clear.clicked.connect(self.clear_chat)
        bar.addWidget(self.lbl_chat_hint)
        bar.addStretch(1)
        bar.addWidget(btn_exp)
        bar.addWidget(btn_clear)
        lay.addLayout(bar)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet(
            "QScrollArea{background:#131a26;border:1px solid #223046;border-radius:10px;}"
            "QWidget#ChatBox{background:#131a26;}")
        self.chat_box = QWidget()
        self.chat_box.setObjectName("ChatBox")
        self.chat_lay = QVBoxLayout(self.chat_box)
        self.chat_lay.setContentsMargins(8, 8, 8, 8)
        self.chat_lay.setSpacing(10)
        self.chat_lay.addStretch(1)
        self.chat_scroll.setWidget(self.chat_box)
        self._chat_log = []          # [{'t':.., 'role':.., 'text':.., 'attach':..}]
        lay.addWidget(self.chat_scroll, 1)

        self.chat_status = QLabel("")
        self.chat_status.setStyleSheet("color:#888;font-size:11px;")
        lay.addWidget(self.chat_status)

        # 附件预览条（选好文件后显示，可取消）
        self.attach_bar = QHBoxLayout()
        self.lbl_attach = QLabel("")
        self.lbl_attach.setStyleSheet("color:#5fd0ff;font-size:11px;")
        self.btn_attach_x = QPushButton("×")
        self.btn_attach_x.setFixedWidth(26)
        self.btn_attach_x.clicked.connect(self._clear_attach)
        self.attach_bar.addWidget(self.lbl_attach, 1)
        self.attach_bar.addWidget(self.btn_attach_x)
        lay.addLayout(self.attach_bar)
        self._attach = []
        self._clear_attach()

        row = QHBoxLayout()
        self.btn_img = QPushButton("图片")
        self.btn_img.setToolTip("选一张图片发给鲸鱼娘（只在本机显示，不上传）")
        self.btn_img.clicked.connect(self._pick_images)
        self.btn_file = QPushButton("文件")
        self.btn_file.setToolTip("选任意文件发给鲸鱼娘（只记录路径，不上传内容）")
        self.btn_file.clicked.connect(self._pick_files)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("和鲸鱼娘说点什么……（Ctrl+Enter 发送）")
        self.chat_input.setFixedHeight(64)
        self.chat_input.setStyleSheet(
            "QTextEdit{background:#0f1621;border:1px solid #2a3b55;border-radius:8px;padding:5px;}")
        btn = QPushButton("发送")
        btn.setFixedWidth(58)
        btn.clicked.connect(self.send_chat)
        row.addWidget(self.btn_img)
        row.addWidget(self.btn_file)
        row.addWidget(self.chat_input, 1)
        row.addWidget(btn)
        lay.addLayout(row)
        self._install_chat_keys()
        return w

    def _install_chat_keys(self):
        """Ctrl+Enter 发送，Enter 换行。"""
        from PySide6.QtCore import QEvent, QObject

        class _Filter(QObject):
            def __init__(self, panel):
                super().__init__()
                self.panel = panel

            def eventFilter(self, obj, ev):
                if ev.type() == QEvent.KeyPress and obj is self.panel.chat_input:
                    if ev.key() in (Qt.Key_Return, Qt.Key_Enter) and ev.modifiers() & Qt.ControlModifier:
                        self.panel.send_chat()
                        return True
                return False

        self._chat_filter = _Filter(self)
        self.chat_input.installEventFilter(self._chat_filter)

    # ---------- 附件 ----------
    def _pick_images(self):
        types = "图片 (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;所有文件 (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "选图片", "", types)
        if files:
            self._set_attach(files)

    def _pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选文件", "", "所有文件 (*)")
        if files:
            self._set_attach(files)

    def _set_attach(self, files):
        self._attach = list(files)[:6]
        names = "、".join(os.path.basename(f) for f in self._attach)
        self.lbl_attach.setText("待发送：" + names)
        self.btn_attach_x.show()

    def _clear_attach(self):
        self._attach = []
        self.lbl_attach.setText("")
        self.btn_attach_x.hide()

    def send_chat(self):
        text = self.chat_input.toPlainText().strip()
        attach = list(self._attach)
        if not text and not attach:
            return
        self.chat_input.clear()
        for f in attach:
            self.append_chat("user", text, attachment=f)
            kind = "图片" if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")) else "文件"
            self.ctl.send_chat(f"（用户发来{kind}：{os.path.basename(f)}，路径 {f}）" + (("，" + text) if text else ""))
        if text:
            if not attach:
                self.append_chat("user", text)
                self.ctl.send_chat(text)
            else:
                self.append_chat("user", text)
        self._clear_attach()

    def clear_chat(self):
        self._chat_log = []
        while self.chat_lay.count() > 1:
            item = self.chat_lay.takeAt(0)
            wdt = item.widget()
            if wdt is not None:
                wdt.deleteLater()
        self.chat_status.setText("已清屏（本地记录文件保留，导出仍可用）")

    def export_chat(self):
        if not self._chat_log:
            self.chat_status.setText("还没有可导出的聊天记录")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出聊天记录",
            os.path.join(os.path.expanduser("~"), "Desktop", "鲸鱼娘聊天记录.md"),
            "Markdown (*.md);;文本文件 (*.txt)")
        if not path:
            return
        try:
            lines = ["# 与鲸鱼娘的聊天记录", ""]
            for it in self._chat_log:
                who = "我" if it["role"] == "user" else self.ctl.get_name()
                extra = f" 〔附件：{os.path.basename(it['attach'])}〕" if it.get("attach") else ""
                lines.append(f"**[{it['t']}] {who}**{extra}")
                if it.get("text"):
                    lines.append(it["text"])
                lines.append("")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.chat_status.setText(f"已导出 {len(self._chat_log)} 条 → {path}")
        except OSError as e:
            self.chat_status.setText(f"导出失败：{e}")

    # ---------- 设置页 ----------
    def _tab_settings(self):
        w = QWidget()
        root = QVBoxLayout(w)

        # 后端管理
        box_ai = QGroupBox("联网后端管理")
        form = QFormLayout(box_ai)
        self.cb_profiles = QComboBox()
        self.cb_profiles.currentIndexChanged.connect(self._on_profile_switch)
        row_prof = QHBoxLayout()
        row_prof.addWidget(self.cb_profiles)
        btn_new = QPushButton("新建")
        btn_new.clicked.connect(self._new_profile)
        btn_del = QPushButton("删除")
        btn_del.clicked.connect(self._delete_profile)
        row_prof.addWidget(btn_new)
        row_prof.addWidget(btn_del)
        form.addRow("后端", row_prof)

        self.ed_profile_name = QLineEdit()
        self.ed_endpoint = QLineEdit()
        self.ed_endpoint.setPlaceholderText("留空用智谱默认地址；填根地址会自动补 /chat/completions")
        self.ed_model = QLineEdit()
        self.ed_key = QLineEdit()
        self.ed_key.setEchoMode(QLineEdit.Password)
        self.ed_key.setPlaceholderText("留空则读取环境变量 ZHIPU_API_KEY 或 ~/.zhipu_api_key.txt")
        form.addRow("备注名", self.ed_profile_name)
        form.addRow("接口地址", self.ed_endpoint)
        form.addRow("模型名", self.ed_model)
        form.addRow("API Key", self.ed_key)

        row = QHBoxLayout()
        btn_save = QPushButton("保存当前后端")
        btn_save.clicked.connect(self.ctl.save_ai_settings)
        btn_test = QPushButton("测试连接")
        btn_test.clicked.connect(self.ctl.test_ai_connection)
        row.addWidget(btn_save)
        row.addWidget(btn_test)
        form.addRow(row)
        self.lbl_ai_status = QLabel("")
        form.addRow(self.lbl_ai_status)
        root.addWidget(box_ai)

        # 自主行动
        box_auto = QGroupBox("自主行动")
        ra = QVBoxLayout(box_auto)
        self.chk_auto = QCheckBox("允许她自己闲逛、说话、跑动（无操作时触发）")
        self.chk_auto.toggled.connect(self.ctl.set_auto)
        ra.addWidget(self.chk_auto)
        root.addWidget(box_auto)

        # 音频
        box_audio = QGroupBox("音频设置（本地导入）")
        aa = QVBoxLayout(box_audio)
        self.chk_audio = QCheckBox("启用音频")
        self.chk_audio.toggled.connect(self.ctl.toggle_sound)
        aa.addWidget(self.chk_audio)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("音量"))
        self.sl_volume = QSlider(Qt.Horizontal)
        self.sl_volume.setRange(0, 100)
        self.sl_volume.valueChanged.connect(self._on_volume)
        vol_row.addWidget(self.sl_volume)
        self.lbl_volume = QLabel("80")
        vol_row.addWidget(self.lbl_volume)
        aa.addLayout(vol_row)

        self.chk_follow_sys = QCheckBox("音量跟随系统（系统调小时桌宠一起变小）")
        self.chk_follow_sys.toggled.connect(self.ctl.audio.set_follow_system)
        aa.addWidget(self.chk_follow_sys)

        act_row = QHBoxLayout()
        self.cb_audio_action = QComboBox()
        for key, label in AUDIO_ACTIONS:
            self.cb_audio_action.addItem(label, key)
        act_row.addWidget(self.cb_audio_action)
        btn_import = QPushButton("导入音频…")
        btn_import.clicked.connect(self._import_audio)
        btn_clear = QPushButton("清除")
        btn_clear.clicked.connect(self._clear_audio)
        act_row.addWidget(btn_import)
        act_row.addWidget(btn_clear)
        aa.addLayout(act_row)
        self.lbl_audio_file = QLabel("未绑定音频文件")
        self.lbl_audio_file.setStyleSheet("color:#888;font-size:11px;")
        aa.addWidget(self.lbl_audio_file)
        root.addWidget(box_audio)

        # 关于与更新
        box_upd = QGroupBox("关于与更新")
        u = QVBoxLayout(box_upd)
        self.lbl_version = QLabel(f"当前版本 v{APP_VERSION}")
        u.addWidget(self.lbl_version)
        row_url = QHBoxLayout()
        row_url.addWidget(QLabel("清单地址"))
        self.ed_update_url = QLineEdit()
        self.ed_update_url.setPlaceholderText("可选：托管的更新清单 JSON 地址，留空则无法联网检查")
        row_url.addWidget(self.ed_update_url)
        u.addLayout(row_url)
        row_btn = QHBoxLayout()
        btn_upd = QPushButton("检查更新")
        btn_upd.clicked.connect(self._check_update)
        row_btn.addWidget(btn_upd)
        self.lbl_update = QLabel("")
        self.lbl_update.setStyleSheet("color:#888;font-size:11px;")
        row_btn.addWidget(self.lbl_update)
        u.addLayout(row_btn)
        root.addWidget(box_upd)

        root.addStretch()
        return w

    # ---------- 后端交互 ----------
    def _on_profile_switch(self, idx: int):
        if idx >= 0:
            self.ctl.switch_profile(idx)
            self._fill_profile_fields()

    def _new_profile(self):
        self.ctl.new_profile()
        self._reload_profiles()

    def _delete_profile(self):
        if self.ctl.delete_active_profile():
            self._reload_profiles()
        else:
            self.lbl_ai_status.setText("至少保留一套后端。")

    def _reload_profiles(self):
        self.cb_profiles.blockSignals(True)
        self.cb_profiles.clear()
        for i, p in enumerate(self.ctl.profiles()):
            self.cb_profiles.addItem(p.get("name", f"后端 {i + 1}"), i)
        idx = self.ctl.config.get("active_profile", 0)
        self.cb_profiles.setCurrentIndex(max(0, min(idx, self.cb_profiles.count() - 1)))
        self.cb_profiles.blockSignals(False)
        self._fill_profile_fields()

    def _fill_profile_fields(self):
        prof = self.ctl.active_profile()
        self.ed_profile_name.setText(prof.get("name", ""))
        self.ed_endpoint.setText(prof.get("endpoint", ""))
        self.ed_model.setText(prof.get("model", ""))
        self.ed_key.setText(prof.get("api_key", ""))

    # ---------- 音频交互 ----------
    def _on_volume(self, v: int):
        self.lbl_volume.setText(str(v))
        self.ctl.audio.set_volume(v)

    def _current_action(self) -> str:
        return self.cb_audio_action.currentData()

    def _import_audio(self):
        action = self._current_action()
        path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac *.wma)")
        if path:
            saved = self.ctl.audio.import_action(action, path)
            if saved:
                self.lbl_audio_file.setText(saved)
                self.ctl.save_config()
            else:
                self.lbl_audio_file.setText("导入失败，格式不支持或文件被占用。")

    def _clear_audio(self):
        action = self._current_action()
        self.ctl.audio.clear_action(action)
        self.ctl.save_config()
        self.lbl_audio_file.setText("未绑定音频文件")

    def _refresh_audio_label(self):
        action = self._current_action()
        path = self.ctl.audio.action_path(action)
        self.lbl_audio_file.setText(path if path else "未绑定音频文件")

    # ---------- 记忆本地保存（v2.4） ----------
    def _backup_memory(self):
        """把 memory.db / knowledge.db / config.json 复制到用户选的文件夹。"""
        import shutil
        import time

        dst_dir = QFileDialog.getExistingDirectory(self, "选择备份文件夹")
        if not dst_dir:
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = os.path.join(dst_dir, f"WhaleGirlPet-记忆备份-{stamp}")
        try:
            os.makedirs(target, exist_ok=True)
            copied = []
            for name in ("memory.db", "knowledge.db", "config.json"):
                src = os.path.join(paths.account_dir(), name)
                if os.path.exists(src):
                    shutil.copyfile(src, os.path.join(target, name))
                    copied.append(name)
            self.lbl_mem.setText(f"已备份到 {target}（{len(copied)} 个文件）")
        except OSError as e:
            self.lbl_mem.setText(f"备份失败：{e}")

    def _export_memory_readable(self):
        """导出一份人能直接读的清单（TXT）。"""
        import time

        p, _ = QFileDialog.getSaveFileName(
            self, "导出记忆清单", f"记忆清单-{time.strftime('%Y%m%d')}.txt", "文本 (*.txt)")
        if not p:
            return
        try:
            lines = [f"鲸鱼娘桌宠 · 记忆与知识导出", time.strftime("%Y-%m-%d %H:%M:%S"), ""]
            lines.append(f"记住的对话条数：{self.ctl.memory_count()}")
            lines.append("")
            lines.append("【关于你的事实】")
            for f in self.ctl.memory_facts():
                lines.append(f"- {f['key']}：{f['value']}")
            lines.append("")
            lines.append("【知识库文档】")
            for d in self.ctl.kb_docs():
                lines.append(f"- {d['name']}（{d['chars']} 字）")
            lines.append("")
            lines.append(f"数据目录：{paths.account_dir()}")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.lbl_mem.setText(f"已导出到 {p}")
        except OSError as e:
            self.lbl_mem.setText(f"导出失败：{e}")

    # ---------- 音频库（v2.4） ----------
    def _refresh_hw(self):
        """读显卡/内存/线程，按显存给一句话推荐（只读，不动驱动）。"""
        try:
            import hwinfo
        except Exception:  # noqa: BLE001
            return
        h = hwinfo.snapshot()
        item, why = hwinfo.recommend(models_catalog.CATALOG)
        rec = f"推荐：{item['name']}（{item['size_mb'] / 1024:.1f}GB，{item['note']}）" if item else "推荐：无"
        self.lbl_hw.setText(f"你的配置：{hwinfo.summary()}\n{rec}｜理由：{why}")
        try:
            import gpu_guard
            backend = self.ctl.llm.backend
            tag = "Ollama / GPU" if backend == "ollama" else "dafeiyu / CPU"
            on = self.ctl.config.get("gpu_when_idle", True)
            self.lbl_gpu.setText(
                f"空闲算力调度：{'开' if on else '关'}｜{gpu_guard.summary()}｜当前引擎 {tag}")
        except Exception:  # noqa: BLE001
            self.lbl_gpu.setText("空闲算力调度：读取失败")

    def _audio_rows(self):
        """(路径, 文件名, 类别, 绑定动作) 列表：动作音效 + TTS 语音缓存。"""
        maps = self.ctl.config.get("audio", {}).get("mappings", {})
        rev = {str(v).lower(): k for k, v in maps.items()}
        rows = []
        for folder, kind in ((paths.voice_dir(), "音效"),):
            if not os.path.isdir(folder):
                continue
            for n in sorted(os.listdir(folder)):
                p = os.path.join(folder, n)
                if os.path.isfile(p) and n.lower().endswith(panel_v2.AUDIO_EXTS):
                    key = rev.get(p.lower(), "")
                    label = paths.AUDIO_ACTION_LABELS.get(key, "")
                    if not label and n.startswith("sfx_"):
                        # 人格专属：sfx_<动作>_<人格>.mp3，动作部分从文件名反推
                        body = n[4:].rsplit(".", 1)[0]
                        cand = [k for k in paths.AUDIO_ACTION_LABELS if body.startswith(k + "_")]
                        if cand:
                            k2 = max(cand, key=len)
                            pk = body[len(k2) + 1:]
                            pname = pers.get(pk)["name"] if pk else ""
                            label = paths.AUDIO_ACTION_LABELS[k2] + f"（{pname}）"
                    rows.append((p, n, kind, label or "—"))
        cache = os.path.join(paths.account_dir(), "tts_cache")
        if os.path.isdir(cache):
            names = sorted(os.listdir(cache))
            for n in names[:300]:
                p = os.path.join(cache, n)
                if os.path.isfile(p) and n.lower().endswith(panel_v2.AUDIO_EXTS):
                    rows.append((p, n, "语音缓存", "—"))
        return rows

    def _refresh_audio_lib(self):
        rows = self._audio_rows()
        tbl = self.tbl_audio
        tbl.setRowCount(len(rows))
        for i, (p, n, kind, label) in enumerate(rows):
            item = QTableWidgetItem(n)
            item.setData(Qt.UserRole, p)
            tbl.setItem(i, 0, item)
            tbl.setItem(i, 1, QTableWidgetItem(kind))
            tbl.setItem(i, 2, QTableWidgetItem(label))
            try:
                kb = max(1, os.path.getsize(p) // 1024)
                tbl.setItem(i, 3, QTableWidgetItem(f"{kb} KB"))
            except OSError:
                tbl.setItem(i, 3, QTableWidgetItem("?"))
        bindings = len(self.ctl.config.get("audio", {}).get("mappings", {}))
        pk = str(self.ctl.config.get("persona", "sichuan_sweet"))
        pname = pers.get(pk)["name"]
        own = sum(1 for r in rows if r[1].endswith(f"_{pk}.mp3"))
        self.lbl_audio_lib.setText(
            f"共 {len(rows)} 个文件（音效 {sum(1 for r in rows if r[2] == '音效')} / "
            f"语音缓存 {sum(1 for r in rows if r[2] == '语音缓存')}）；已绑定 {bindings} 个动作。\n"
            f"当前语音人格「{pname}」专属音效 {own} 条，播放动作时优先用它，没有才回退通用音效。\n"
            f"目录：{paths.voice_dir()}")

    def _selected_audio_path(self) -> str:
        row = self.tbl_audio.currentRow()
        if row < 0:
            return ""
        item = self.tbl_audio.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item else ""

    def _play_selected_audio(self):
        p = self._selected_audio_path()
        if p:
            self.ctl.audio.play_file(p)

    def _bind_selected_audio(self):
        p = self._selected_audio_path()
        if not p:
            return
        action = self.cmb_lib_action.currentData()
        self.ctl.config.setdefault("audio", {}).setdefault("mappings", {})[action] = p
        self.ctl.save_config()
        self._refresh_audio_lib()
        self._refresh_audio_label()

    def _del_selected_audio(self):
        p = self._selected_audio_path()
        if not p:
            return
        maps = self.ctl.config.get("audio", {}).get("mappings", {})
        for k in [k for k, v in maps.items() if str(v).lower() == p.lower()]:
            maps.pop(k, None)
        try:
            os.remove(p)
        except OSError:
            pass
        self.ctl.save_config()
        self._refresh_audio_lib()

    def _open_voice_dir(self):
        try:
            os.startfile(paths.voice_dir())
        except Exception:  # noqa: BLE001
            pass

    def _import_audio_to_lib(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.m4a *.flac *.aac *.wma)")
        if not path:
            return
        action = self.cmb_lib_action.currentData()
        saved = self.ctl.audio.import_action(action, path)
        if saved:
            self.ctl.save_config()
            self._refresh_audio_lib()
        else:
            self.lbl_audio_lib.setText("导入失败：格式不支持或文件被占用。")

    # ---------- 刷新 ----------
    def refresh(self):
        st = self.ctl.state
        self.ed_name.blockSignals(True)
        self.ed_name.setText(self.ctl.get_name())
        self.ed_name.blockSignals(False)

        self.lbl_level.setText(f"Lv.{st.level}　经验 {st.exp}/{st.exp_need()}")
        self.lbl_coins.setText(f"金币：{st.coins}")
        self._set_bar(self.bar_hunger, "饱食度", st.hunger)
        self._set_bar(self.bar_mood, "心情", st.mood)
        self._set_bar(self.bar_intimacy, "亲密度", st.intimacy)
        for key, s in SNACKS.items():
            self.snack_btns[key].setEnabled(st.coins >= s["cost"])
        skin = self.ctl.config.get("skin", "default")
        idx = self.skin_combo.findData(skin)
        if idx >= 0 and self.skin_combo.currentIndex() != idx:
            self.skin_combo.blockSignals(True)
            self.skin_combo.setCurrentIndex(idx)
            self.skin_combo.blockSignals(False)
        size_label = self.ctl.config.get("size_label", "中")
        idx2 = self.size_combo.findText(size_label)
        if idx2 >= 0 and self.size_combo.currentIndex() != idx2:
            self.size_combo.blockSignals(True)
            self.size_combo.setCurrentIndex(idx2)
            self.size_combo.blockSignals(False)

        self.chk_water.setChecked(self.ctl.config.get("water_on", True))
        self.chk_sedentary.setChecked(self.ctl.config.get("sedentary_on", True))
        self.chk_sound.setChecked(self.ctl.config.get("sound_on", True))
        self.chk_chatter.setChecked(self.ctl.config.get("chatter_on", True))
        self.chk_auto.setChecked(self.ctl.config.get("auto_on", True))
        self.ed_update_url.blockSignals(True)
        self.ed_update_url.setText(self.ctl.config.get("update_url", ""))
        self.ed_update_url.blockSignals(False)

        # 后端
        self._reload_profiles()

        # 音频
        audio = self.ctl.config.get("audio", {})
        self.chk_audio.setChecked(audio.get("on", True))
        self.sl_volume.blockSignals(True)
        self.sl_volume.setValue(int(audio.get("volume", 80)))
        self.sl_volume.blockSignals(False)
        self.lbl_volume.setText(str(audio.get("volume", 80)))
        self.chk_follow_sys.blockSignals(True)
        self.chk_follow_sys.setChecked(bool(audio.get("follow_system", True)))
        self.chk_follow_sys.blockSignals(False)
        self._refresh_audio_label()
        if getattr(self, "tbl_audio", None) is not None:   # 音频库页已不挂载
            try:
                self._refresh_audio_lib()
            except Exception:  # noqa: BLE001
                pass

        self.refresh_tasks()
        self._refresh_v2()

    def _set_bar(self, label, name, v):
        v = max(0, min(100, v))
        # v2.9.3：原先写死 #333 + █░ 字符，深色主题下糊成一片；
        # 改成按主题取色的富文本色块条，浅/深两套主题都清楚
        pal = theme.palette(self.ctl.config.get("theme", theme.DEFAULT))
        fill = pal["bar_fill"] if v > 30 else "#e06c6c"
        num_color = pal["label"] if v > 30 else "#e06c6c"
        cells = 20
        k = int(round(v / (100 / cells)))
        bars = "".join(
            f'<span style="background:{fill if i < k else pal["bar_track"]};'
            f'color:{fill if i < k else pal["bar_track"]};">&nbsp;&nbsp;</span>'
            for i in range(cells))
        label.setText(
            f'<span style="color:{pal["label"]};font-size:12px;">{name}</span>'
            f'&nbsp;&nbsp;{bars}'
            f'&nbsp;&nbsp;<span style="color:{num_color};font-size:12px;">{v:0.0f}</span>')
        label.setStyleSheet("font-family:'Microsoft YaHei';")

    def _avatar_url(self) -> str:
        p = paths.asset_path(os.path.join("ui", "avatar.png")).replace("\\", "/")
        return "file:///" + p

    def _bubble_row(self, role: str, text: str, attachment: str, who: str, now: str):
        """一条 QQ 风格气泡行：头像 / 气泡 / 名字时间。"""
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QFrame

        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        bubble = QFrame()
        bubble.setObjectName("BubbleMe" if role == "user" else "BubblePet")
        bg = "#3f6cf6" if role == "user" else "#e9eef8"
        fg = "#ffffff" if role == "user" else "#1b2434"
        radius = ("border-top-left-radius:10px;border-top-right-radius:10px;"
                  "border-bottom-left-radius:10px;border-bottom-right-radius:2px;"
                  if role == "user" else
                  "border-top-left-radius:10px;border-top-right-radius:10px;"
                  "border-bottom-left-radius:2px;border-bottom-right-radius:10px;")
        bubble.setStyleSheet(f"QFrame{{background:{bg};border:none;{radius}}}")
        bv = QVBoxLayout(bubble)
        bv.setContentsMargins(12, 9, 12, 9)
        bv.setSpacing(5)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(f"color:{fg};font-size:13px;background:transparent;")
        bv.addWidget(lbl)

        if attachment and os.path.exists(attachment):
            name = os.path.basename(attachment)
            if attachment.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                pic = QLabel()
                pm = QPixmap(attachment)
                if not pm.isNull():
                    pic.setPixmap(pm.scaled(170, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                pic.setStyleSheet("background:transparent;")
                bv.addWidget(pic)
                tip = QLabel(name)
                tip.setStyleSheet(f"color:{'#dfe6ff' if role == 'user' else '#5a667c'};font-size:10px;background:transparent;")
                bv.addWidget(tip)
            else:
                f = QLabel(f"📎 {name}  {self._fmt_size(attachment)}")
                f.setStyleSheet(f"color:{'#e8efff' if role == 'user' else '#2b6ea8'};font-size:12px;background:transparent;")
                bv.addWidget(f)

        maxw = max(200, int(self.chat_scroll.viewport().width() * 0.70))
        fm = lbl.fontMetrics()
        natural = fm.horizontalAdvance(text) + 26
        if attachment and os.path.exists(attachment):
            natural = max(natural, 196)
        bubble.setFixedWidth(min(maxw, max(96, natural)))

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        col.addWidget(bubble, 0, Qt.AlignRight if role == "user" else Qt.AlignLeft)
        meta = QLabel(f"{who}   {now}")
        meta.setStyleSheet("color:#7c869c;font-size:10px;background:transparent;")
        col.addWidget(meta, 0, Qt.AlignRight if role == "user" else Qt.AlignLeft)

        if role == "user":
            h.addStretch(1)
            h.addLayout(col, 0)
        else:
            av = QLabel()
            pm = QPixmap(paths.asset_path(os.path.join("ui", "avatar.png")))
            if not pm.isNull():
                av.setPixmap(pm.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            av.setFixedSize(32, 32)
            av.setStyleSheet("background:transparent;")
            h.addWidget(av, 0, Qt.AlignTop)
            h.addLayout(col, 0)
            h.addStretch(1)
        return row

    def append_chat(self, role: str, text: str, attachment: str = ""):
        import datetime
        import json

        who = "我" if role == "user" else self.ctl.get_name()
        now = datetime.datetime.now().strftime("%H:%M")
        row = self._bubble_row(role, text, attachment, who, now)
        self.chat_lay.insertWidget(self.chat_lay.count() - 1, row)
        QTimer.singleShot(0, self._scroll_chat_bottom)

        self._chat_log.append({"t": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                               "role": role, "text": text, "attach": attachment})
        try:
            if not getattr(self, "_loading", False):
                with open(self._chat_file(), "a", encoding="utf-8") as f:
                    f.write(json.dumps(self._chat_log[-1], ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _scroll_chat_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _chat_file(self) -> str:
        return os.path.join(paths.account_dir(""), "chat_log.jsonl")

    @staticmethod
    def _fmt_size(path: str) -> str:
        try:
            n = os.path.getsize(path)
        except OSError:
            return ""
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f}{unit}"
            n /= 1024.0
        return f"{n:.1f}TB"

    def load_chat_history(self, limit: int = 60):
        """启动时把本机聊天天记录读回气泡区（只读最近 limit 条）。"""
        import json
        path = self._chat_file()
        if not os.path.exists(path):
            return
        rows = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            return
        self._loading = True
        try:
            for it in rows[-limit:]:
                self.append_chat(it.get("role", "pet"), it.get("text", ""), it.get("attach", "") or "")
        finally:
            self._loading = False

    def set_chat_status(self, text: str):
        self.chat_status.setText(text)

    def set_tomato(self, text: str):
        self.lbl_tomato.setText(text)

    # ================= v2.0.0：语音人格 / 记忆知识 / 安全 / 账号 / 定时 =================
    def _refresh_v2(self):
        ctl = self.ctl
        # 人格与语音
        try:
            key = ctl.config.get("persona", pers.DEFAULT_PERSONA)
            i = self.cmb_persona.findData(key)
            if i >= 0 and self.cmb_persona.currentIndex() != i:
                self.cmb_persona.blockSignals(True)
                self.cmb_persona.setCurrentIndex(i)
                self.cmb_persona.blockSignals(False)
            p = pers.get(key) or {}
            note = p.get("voice_note", "")
            self.lbl_persona_note.setText(
                "音色：" + pers.voice_label(key) + (f"\n{note}" if note else ""))
            self.chk_tts.setChecked(bool(ctl.config.get("tts_on")))
            self.chk_tts_online.setChecked(bool(ctl.config.get("tts_online", True)))
        except Exception:  # noqa: BLE001
            pass
        # 本地模型
        try:
            info = ctl.local_llm_info()
            if info["running"]:
                state = "运行中"
            elif info["available"]:
                state = "可启动（还没加载）"
            else:
                state = "未找到模型或推理程序"
            backend = {"ollama": "Ollama", "llama_cpp": "dafeiyu.cpp"}.get(
                info.get("backend", ""), info.get("backend", "") or "未定")
            extra = ""
            if info.get("backend") == "ollama":
                extra = "（Ollama 里还有：" + "、".join(
                    m["name"] for m in info.get("ollama", [])[:3]) + "）"
            self.lbl_llm.setText(
                f"状态：{state}｜后端：{backend}｜模型：{info['model'] or '无'}"
                f"｜端口 {info['port']}{extra}")
            self.chk_llm.setChecked(bool(ctl.config.get("llm_on", True)))
        except Exception:  # noqa: BLE001
            pass
        # 硬件与模型推荐
        try:
            self._refresh_hw()
        except Exception:  # noqa: BLE001
            pass
        # 语音命令入口
        try:
            if hasattr(self, "lbl_voice"):
                import voice_cmd
                has = voice_cmd.has_microphone()
                self.lbl_voice.setText(
                    "麦克风：" + ("已检测到，按 Ctrl+Alt+V 或点按钮说一句"
                                if has else "没检测到，检查设备或系统麦克风权限"))
        except Exception:  # noqa: BLE001
            pass
        # 记忆与知识库：面板不再展示，只在托盘「打开数据目录」里本地查看，这里跳过
        if getattr(self, "lbl_mem", None) is not None:
            try:
                facts = ctl.memory_facts()
                self.lbl_mem.setText(
                    f"已记住 {ctl.memory_count()} 条对话、{len(facts)} 条关于你的事实。")
                self.lst_facts.clear()
                for f in facts:
                    self.lst_facts.addItem(f"{f['key']}：{f['value']}")
            except Exception:  # noqa: BLE001
                pass
            try:
                st = ctl.kb_stats()
                self.lbl_kb.setText(
                    f"文档 {st.get('docs', 0)} 篇 / 片段 {st.get('chunks', 0)} 段 / "
                    f"{st.get('chars', 0)} 字")
                self.lst_kb.clear()
                for d in ctl.kb_docs():
                    self.lst_kb.addItem(f"{d['name']}（{d['chars']} 字）")
                    self.lst_kb.item(self.lst_kb.count() - 1).setData(Qt.UserRole, d["id"])
            except Exception:  # noqa: BLE001
                pass
        # 账号
        try:
            cur = ctl.account_name()
            self.lbl_acct.setText(f"当前账号：{cur}（数据只存本机）")
            self.lst_acct.clear()
            for a in ctl.account_list():
                mark = "● " if a["name"] == cur else "○ "
                self.lst_acct.addItem(mark + a["name"])
                self.lst_acct.item(self.lst_acct.count() - 1).setData(Qt.UserRole, a["slug"])
            i = self.cmb_form.findData(ctl.config.get("form", "mature"))
            if i >= 0 and self.cmb_form.currentIndex() != i:
                self.cmb_form.blockSignals(True)
                self.cmb_form.setCurrentIndex(i)
                self.cmb_form.blockSignals(False)
        except Exception:  # noqa: BLE001
            pass
        # 定时
        try:
            self.chk_night.setChecked(ctl.night_on())
            self.lst_sched.clear()
            for t in ctl.schedule_tasks():
                on = "开" if t.get("on", True) else "关"
                self.lst_sched.addItem(f"[{on}] {t.get('kind')} {t.get('when')} — {t.get('text')}")
                self.lst_sched.item(self.lst_sched.count() - 1).setData(Qt.UserRole, t.get("id"))
        except Exception:  # noqa: BLE001
            pass
        try:
            self.txt_usage.setPlainText(ctl.yesterday_report() or "昨天没有使用记录。")
        except Exception:  # noqa: BLE001
            pass
        try:
            self._refresh_models()
        except Exception:  # noqa: BLE001
            pass

    # ---- 模型库 ----
    def _add_model_item(self, text: str, role_id: str, info: dict):
        self.lst_models.addItem(text)
        item = self.lst_models.item(self.lst_models.count() - 1)
        item.setData(Qt.UserRole, role_id)
        item.setData(Qt.UserRole + 1, info)

    def _add_model_header(self, text: str):
        h = QListWidgetItem(text)
        h.setFlags(Qt.NoItemFlags)
        self.lst_models.addItem(h)

    def _refresh_models(self):
        """模型库分两段：已安装（本地真实存在的 .gguf）在上，内置可下载在下。"""
        ctl = self.ctl
        try:
            local = ctl.local_models()
        except Exception:  # noqa: BLE001
            local = []
        by_name = {m["name"]: m for m in local}
        cur = ctl.config.get("llm_model_file", "")
        self.lbl_cur_model.setText(
            "当前模型：" + (cur if cur else "（自动：runtime/models 里第一个 .gguf）")
            + f"　本地已有 {len(local)} 个 .gguf")
        self.lst_models.clear()

        # 一、已安装
        self._add_model_header(f"■ 已安装模型（{len(local)} 个，可直接用）")
        matched = set()
        for it in models_catalog.CATALOG:
            f = it.get("file")
            if f and f in by_name:
                matched.add(f)
                text = (f"[已安装] {it['brand']} · {it['name']}　"
                        f"{'可跑' if it['fits'] else '跑不动'}　"
                        f"{by_name[f]['size_mb']:.0f} MB")
                self._add_model_item(text, "local:" + f, it)
        for m in local:
            if m["name"] in matched:
                continue
            self._add_model_item(
                f"[已安装] 自定义 · {m['name']}　{m['size_mb']:.0f} MB",
                "local:" + m["name"],
                {"id": "custom", "brand": "自定义", "name": m["name"], "file": m["name"],
                 "size_mb": m["size_mb"], "fits": True, "custom": True})
        if not local:
            self._add_model_header("（还没有任何模型。可以下载下面的内置模型，或用「网络地址添加」）")

        # 二、内置可下载（已装的移到上面去了，这里不再重复）
        self._add_model_header("■ 内置模型（一键下载，走 hf-mirror）")
        pending = 0
        for it in models_catalog.CATALOG:
            f = it.get("file")
            if f and f in by_name:
                continue
            pending += 1
            mark = "可跑" if it["fits"] else "跑不动"
            text = (f"[{mark}] {it['brand']} · {it['name']}　"
                    f"{models_catalog.fmt_size(it['size_mb'])}")
            self._add_model_item(text, it["id"], it)
        if not pending:
            self._add_model_header("（内置模型都已装好）")

    def _cur_model_item(self):
        it = self.lst_models.currentItem()
        if it is None or not (it.flags() & Qt.ItemIsSelectable):
            self.lbl_dl.setText("先在上面选一个模型。")
            return None, None
        return it.data(Qt.UserRole), it.data(Qt.UserRole + 1) or {}

    def _dl_model(self):
        item_id, info = self._cur_model_item()
        if item_id is None:
            return
        if str(item_id).startswith("local:"):
            self.lbl_dl.setText("这个模型已经在本地了，直接点「使用此模型」即可。")
            return
        if info.get("custom"):
            self.lbl_dl.setText("自定义模型已经在本地，无需再下载。")
            return
        if not models_catalog.can_download(info):
            self.lbl_dl.setText("这个模型本机跑不动（或只有分片），不提供下载；可以复制链接或打开仓库页。")
            return
        ok = self.ctl.download_model(item_id)
        self.lbl_dl.setText("开始下载…" if ok else "已有下载任务在进行。")

    def _cancel_dl(self):
        if self.ctl.cancel_download():
            self.lbl_dl.setText("正在取消…已下部分会保留，下次续传。")
        else:
            self.lbl_dl.setText("当前没有下载任务。")

    def _use_model(self):
        item_id, info = self._cur_model_item()
        if not item_id:
            return
        name = info.get("file") or ""
        if not name:
            self.lbl_dl.setText("这个模型没有单文件 GGUF，不能直接切换。")
            return
        try:
            ok = self.ctl.use_model(name)
        except Exception as e:  # noqa: BLE001
            self.lbl_dl.setText(f"切换失败：{e}")
            return
        self.lbl_dl.setText("已切换，重启本地模型后生效。" if ok else "本地没有这个文件，先下载。")
        self._refresh_v2()

    def _del_model(self):
        item_id, info = self._cur_model_item()
        if not item_id:
            return
        name = info.get("file") or ""
        if not name:
            self.lbl_dl.setText("这个模型没有单文件，无需删除。")
            return
        try:
            freed = self.ctl.delete_model(name)
        except Exception as e:  # noqa: BLE001
            self.lbl_dl.setText(f"删除失败：{e}")
            return
        self.lbl_dl.setText(f"已删除，释放 {freed:.0f} MB。" if freed else "本地没有这个文件。")
        self._refresh_v2()

    def _copy_link(self):
        item_id, info = self._cur_model_item()
        if item_id is None:
            return
        url = info.get("url") or info.get("repo") or ""
        if not url:
            self.lbl_dl.setText("这个模型没有下载链接（已经在本地）。")
            return
        try:
            self.ctl.app.clipboard().setText(url)
            self.lbl_dl.setText("链接已复制：" + url)
        except Exception:  # noqa: BLE001
            self.lbl_dl.setText(url)

    def _open_repo(self):
        item_id, info = self._cur_model_item()
        if item_id is None:
            return
        url = info.get("repo") or ""
        if url:
            QDesktopServices.openUrl(QUrl(url))
            self.lbl_dl.setText("已在浏览器打开仓库页：" + url)
        else:
            self.lbl_dl.setText("这个条目没有仓库页（本地自定义模型）。")

    def _add_model_url(self):
        """联网添加：把任意 https 直链的 .gguf 下到 runtime/models，自动出现在「已安装」。"""
        url = (self.ed_model_url.text() or "").strip()
        if not url:
            self.lbl_dl.setText("先在输入框粘贴一个 .gguf 直链（https://…），或 hf-mirror 的仓库页地址。")
            return
        ok, msg = self.ctl.download_model_url(url)
        self.lbl_dl.setText(msg)
        if ok:
            self.pbar_model.setVisible(True)
        self.ed_model_url.clear()

    def _open_model_dir(self):
        try:
            p = self.ctl.models_dir()
        except Exception:  # noqa: BLE001
            p = ""
        if p and os.path.isdir(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))
            self.lbl_dl.setText("已打开模型目录：" + p)
        else:
            self.lbl_dl.setText("模型目录还没建出来（先下过任意一个模型就会生成）。")

    def on_model_progress(self, item_id: str, got: int, total: int):
        if not self.pbar_model.isVisible():
            self.pbar_model.setVisible(True)
        self.pbar_model.setMaximum(max(1, total))
        self.pbar_model.setValue(got)
        mb = got / 1048576
        tb = total / 1048576
        sp = float(getattr(self.ctl, "dl_speed", 0.0) or 0.0) / 1048576   # bytes/s -> MB/s
        eta = ""
        if sp > 0 and total > got:
            rest = (total - got) / sp
            eta = f"　剩余约 {int(rest // 60)} 分 {int(rest % 60)} 秒"
        self.lbl_dl.setText(f"下载中 {item_id}：{mb:.0f} / {tb:.0f} MB　{sp:.1f} MB/s{eta}")

    # ---- 语音人格 ----
    def _on_persona_change(self, idx: int):
        key = self.cmb_persona.itemData(idx)
        if key:
            self.ctl.set_persona(key)
            p = pers.get(key) or {}
            if getattr(self, "sl_pitch", None) is not None:
                self.sl_pitch.setValue(int(p.get("pitch", 0)))
                self.sl_rate.setValue(int(p.get("rate", 0)))
                self.sl_vol.setValue(int(p.get("volume", 100)))
            self._refresh_v2()

    # ---- 联网音色实验台：拉取音色 → 试听 → 指令微调 → 存为我的音色 ----
    def _sync_vparams(self):
        try:
            p, r, v = self.sl_pitch.value(), self.sl_rate.value(), self.sl_vol.value()
            self.lbl_vparams.setText(
                f"当前参数：音高 {p:+d}Hz　语速 {r:+d}%　音量 {v}"
                f"　（指令里写「音高 {p}」「语速 {r}」「音量 {v}」可直接定值）")
        except Exception:  # noqa: BLE001
            pass

    def _rebuild_persona_combo(self):
        cur = self.cmb_persona.currentData()
        self.cmb_persona.blockSignals(True)
        self.cmb_persona.clear()
        for key, name in pers.persona_index():
            p = pers.get(key)
            tag = "真音色" if p.get("real_voice") else "近似音色"
            self.cmb_persona.addItem(f"{name}　[{tag}]", key)
        idx = self.cmb_persona.findData(cur)
        if idx >= 0:
            self.cmb_persona.setCurrentIndex(idx)
        self.cmb_persona.blockSignals(False)

    def _fetch_voice_list(self):
        w = getattr(self, "_vl_worker", None)
        if w is not None and w.isRunning():
            self.lbl_vnote.setText("正在拉取音色库，稍等…")
            return
        self.lbl_vnote.setText("正在联网拉取微软音色库…")
        self._vl_worker = _VoiceListWorker()
        self._vl_worker.got.connect(self._on_voice_list)
        self._vl_worker.err.connect(lambda m: self.lbl_vnote.setText("拉取失败：" + m))
        self._vl_worker.start()

    def _on_voice_list(self, voices):
        zh = [v for v in voices if str(v.get("Locale", "")).lower().startswith("zh")]
        other = [v for v in voices if v not in zh]
        self.cmb_net_voice.clear()
        for v in zh + other:
            name = v.get("ShortName") or v.get("Name") or ""
            g = {"Female": "女", "Male": "男"}.get(str(v.get("Gender", "")), "")
            self.cmb_net_voice.addItem(f"{name}　{v.get('Locale', '')}　{g}", name)
        self.lbl_vnote.setText(
            f"拉到 {len(voices)} 个音色（中文 {len(zh)} 个排在最前）。选一个点「试听选中」。")

    def _voice_persona(self):
        spk = self.cmb_net_voice.currentData() or ""
        if not spk:
            # 列表刚拉回来时默认停在占位项，往下找第一个真实音色
            for i in range(self.cmb_net_voice.count()):
                d = self.cmb_net_voice.itemData(i) or ""
                if d:
                    spk = d
                    self.cmb_net_voice.setCurrentIndex(i)
                    break
        if not spk:
            return None
        return {"voice": spk, "rate": int(self.sl_rate.value()),
                "pitch": int(self.sl_pitch.value()),
                "volume": int(self.sl_vol.value()), "real_voice": True}

    def _preview_net_voice(self):
        p = self._voice_persona()
        if not p:
            self.lbl_vnote.setText("先点「拉取音色列表」并选一个音色。")
            return
        if not self.chk_tts.isChecked():
            self.chk_tts.setChecked(True)
        self.ctl.config["tts_online"] = self.chk_tts_online.isChecked()
        text = "我是你的鲸鱼娘。这个声音，你听着顺耳吗？"
        try:
            self.ctl.tts.say(text, p, force=True)
        except Exception as e:  # noqa: BLE001
            self.lbl_vnote.setText(f"合成失败：{e}")
            return
        self.lbl_vnote.setText(
            f"试听：{p['voice']}　音高 {p['pitch']:+d}Hz　语速 {p['rate']:+d}%　"
            f"音量 {p['volume']}")

    def _apply_voice_cmd(self):
        cmd = (self.ed_voice_cmd.text() or "").strip()
        if not cmd:
            self.lbl_vnote.setText("先写一句优化指令，比如「再尖一点」「慢 10%」「音量 60」。")
            return
        p, r, v, notes = voice_tweak.parse(
            cmd, self.sl_pitch.value(), self.sl_rate.value(), self.sl_vol.value())
        self.sl_pitch.setValue(p)
        self.sl_rate.setValue(r)
        self.sl_vol.setValue(v)
        self.lbl_vnote.setText("指令：" + cmd + "\n" + "；".join(notes)
                               + "\n点「试听选中」听效果，满意再「存为我的音色」。")

    def _reset_vparams(self):
        self.sl_pitch.setValue(0)
        self.sl_rate.setValue(0)
        self.sl_vol.setValue(80)
        self.lbl_vnote.setText("参数已还原默认：音高 0 / 语速 0 / 音量 80。")

    def _save_net_voice(self):
        p = self._voice_persona()
        if not p:
            self.lbl_vnote.setText("先拉取音色列表并选一个音色，再保存。")
            return
        short = self.cmb_net_voice.currentText().split("　")[0]
        key = "mine_" + p["voice"].replace("-", "_")
        entry = {"key": key, "name": f"我的 · {short}", "voice": p["voice"],
                 "rate": p["rate"], "pitch": p["pitch"], "volume": p["volume"]}
        items = [x for x in (self.ctl.config.get("custom_voices") or [])
                 if x.get("key") != key]
        items.append(entry)
        self.ctl.config["custom_voices"] = items
        try:
            self.ctl.save_config()
        except Exception:  # noqa: BLE001
            pass
        pers.register_custom(items)
        self._rebuild_persona_combo()
        idx = self.cmb_persona.findData(key)
        if idx >= 0:
            self.cmb_persona.setCurrentIndex(idx)
            self._on_persona_change(idx)
        self.lbl_vnote.setText(
            f"已存为「{entry['name']}」并切过去。参数：音高 {p['pitch']:+d}Hz / "
            f"语速 {p['rate']:+d}% / 音量 {p['volume']}。想再调就输指令，改完重存覆盖。")

    def _preview_persona(self):
        key = self.cmb_persona.currentData() or pers.DEFAULT_PERSONA
        p = pers.get(key) or {}
        text = pers.dialectize(p.get("greeting", "你好呀，我是大肥鱼。"), key)
        if not self.chk_tts.isChecked():
            self.chk_tts.setChecked(True)     # 试听要开语音
        self.ctl.config["tts_online"] = self.chk_tts_online.isChecked()
        try:
            self.ctl.tts.say(text, pers.get(key) or {})
            self.lbl_persona_note.setText(f"试听：{text}")
        except Exception as e:  # noqa: BLE001
            self.lbl_persona_note.setText(f"合成失败：{e}")

    def _on_tts_toggle(self, v: bool):
        self.ctl.set_tts(bool(v), self.chk_tts_online.isChecked())

    def _clear_tts_cache(self):
        try:
            n = self.ctl.tts.clear_cache()
            self.lbl_persona_note.setText(f"已清理语音缓存 {n} 个文件。")
        except Exception as e:  # noqa: BLE001
            self.lbl_persona_note.setText(f"清理失败：{e}")

    def _start_llm(self):
        self.ctl.start_local_llm()
        self.lbl_llm.setText("正在加载模型（首次约 20–60 秒，CPU 推理偏慢）……")

    def _stop_llm(self):
        self.ctl.stop_local_llm()
        self._refresh_v2()

    def _refresh_llm(self):
        self._refresh_v2()

    def _on_llm_toggle(self, v: bool):
        self.ctl.config["llm_on"] = bool(v)
        self.ctl.save_config()

    # ---- 记忆 / 知识库 ----
    def _forget_memory(self):
        n = self.ctl.forget_memory()
        self.lbl_mem.setText(f"已清空 {n} 条记忆。")
        self._refresh_v2()

    def _refresh_memory(self):
        self._refresh_v2()

    def _import_kb(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择导入知识库的文件", "",
            "文本文件 (*.txt *.md *.markdown *.csv *.log);;所有文件 (*)")
        if not path:
            return
        res = self.ctl.import_knowledge(path)
        self.lbl_kb.setText(
            f"{os.path.basename(path)}：导入 {res.get('chunks', 0)} 段 / {res.get('chars', 0)} 字"
            if res.get("ok") else f"导入失败：{res.get('error', '未知原因')}")
        self._refresh_v2()

    def _remove_kb(self):
        it = self.lst_kb.currentItem()
        if it is None:
            return
        self.ctl.remove_kb_doc(it.data(Qt.UserRole))
        self._refresh_v2()

    # ---- 安全体检 ----
    def _run_scan(self):
        self.txt_scan.setPlainText("正在检查……（只读，不改系统）")
        self.ctl.run_scan()

    def _update_signatures(self):
        started = self.ctl.update_signatures(silent=False)
        if started:
            self.txt_scan.append("已开始更新病毒库，完成后会提示……")
        else:
            self.txt_scan.append("更新任务已在运行，或无法启动更新。")

    def _refresh_voice(self):
        try:
            import voice_cmd
            has = voice_cmd.has_microphone()
            self.lbl_voice.setText("麦克风：" + ("已检测到" if has else "没检测到，检查设备或系统权限"))
        except Exception as e:  # noqa: BLE001
            self.lbl_voice.setText("语音模块不可用：" + str(e)[:50])

    def _open_defender(self):
        QDesktopServices.openUrl(QUrl("windowsdefender://threat"))

    def refresh_scan(self, report: dict):
        if not report:
            return
        d = report.get("defender", {})
        dmap = [("ok", "可读取状态"), ("realtime", "实时防护"), ("enabled", "已启用"),
                ("sig_time", "病毒库更新"), ("last_scan", "上次扫描")]
        flags = {"True": "是", "False": "否"}
        lines_ = [f"体检时间：{report.get('checked_at', '')}", "", "【Windows Defender】"]
        for k, label in dmap:
            if k in d:
                v = d[k]
                if isinstance(v, bool):
                    v = flags[str(v)]
                lines_.append(f"  {label}：{v}")
        lines_ += ["", "【病毒库】"]
        av = report.get("av") or {}
        if av.get("ok"):
            stale = "  ⚠ 需更新" if av.get("stale") else "（已是最新）"
            lines_.append(f"  版本：{av.get('sig_ver') or '-'}{stale}")
            if av.get("sig_time"):
                lines_.append(f"  签名时间：{av['sig_time']}（{av.get('sig_age', 0)} 天前）")
            lines_.append(f"  引擎：{av.get('engine') or '-'}　平台：{av.get('platform') or '-'}")
            if av.get("quick"):
                lines_.append(f"  上次快扫：{av['quick']}")
        else:
            lines_.append(f"  读取失败：{av.get('reason') or '未知'}")
        lines_ += ["", "【防火墙】"]
        fw = report.get("firewall") or []
        if not fw:
            lines_.append("  读不到防火墙状态")
        else:
            names = {"Domain": "域网络", "Private": "专用网络", "Public": "公用网络"}
            for f in fw:
                if isinstance(f, dict):
                    lines_.append(f"  {names.get(f.get('name'), f.get('name'))}："
                                  f"{'已开启' if f.get('enabled') else '已关闭'}")
                else:
                    lines_.append(f"  · {f}")
        lines_ += ["", "【近 7 天拦截记录】"]
        th = report.get("threats") or {}
        items = th.get("items") or []
        if items:
            for t in items[:10]:
                lines_.append(f"  · {t.get('time', '')}　{t.get('name', '')}"
                              f"（处置成功={t.get('action', '')}）")
        else:
            lines_.append("  " + (th.get("note") or "没有拦截记录"))
        lines_ += ["", "【开机自启项】"]
        for s in report.get("startup", [])[:20]:
            if isinstance(s, dict):
                scope = "系统级" if s.get("system") else "用户级"
                lines_.append(f"  · {s.get('name', '?')}（{scope}）")
            else:
                lines_.append(f"  · {s}")
        lines_ += ["", "【监听的可疑端口】"]
        ports = report.get("ports", [])
        if ports:
            for p in ports:
                if isinstance(p, dict):
                    lines_.append(f"  · {p.get('port')}　{p.get('desc', '')}（进程 {p.get('pid')}）")
                else:
                    lines_.append(f"  · {p}")
        else:
            lines_.append("  未发现常见后门端口")
        lines_ += ["", "【可疑进程】"]
        procs = report.get("suspect", [])
        if procs:
            for p in procs:
                lines_.append(f"  · {p}")
        else:
            lines_.append("  未发现明显可疑进程")
        lines_ += ["", f"综合评分：{report.get('score', '-')}/100"]
        for issue in report.get("issues", []):
            text = issue.get("text", "") if isinstance(issue, dict) else str(issue)
            level = {"warn": "需注意", "info": "提示"}.get(
                issue.get("level") if isinstance(issue, dict) else "", "")
            lines_.append(f"· {('[' + level + '] ') if level else ''}{text}")
        self.txt_scan.setPlainText("\n".join(lines_))

    # ---- 账号 / 形态 ----
    def _on_form_change(self, idx: int):
        form = self.cmb_form.itemData(idx)
        if form:
            self.ctl.set_form(form)

    def _new_account(self):
        name = self.ed_acct.text().strip()
        if not name:
            self.lbl_acct.setText("先填个账号名字。")
            return
        copy = self.findChild(QCheckBox, "chk_copy_acct")
        ok = self.ctl.new_account(name, bool(copy.isChecked()) if copy else False)
        self.lbl_acct.setText("已创建，选中后点「切换」即可使用。" if ok else "创建失败。")
        self._refresh_v2()

    def _switch_account(self):
        it = self.lst_acct.currentItem()
        if it is None:
            return
        ok = self.ctl.switch_account(it.data(Qt.UserRole))
        self.lbl_acct.setText("切换成功。" if ok else "切换失败。")
        self._refresh_v2()

    def _rename_account(self):
        it = self.lst_acct.currentItem()
        name = self.ed_acct.text().strip()
        if it is None or not name:
            self.lbl_acct.setText("选中一个账号并填新名字。")
            return
        ok = self.ctl.rename_account(it.data(Qt.UserRole), name)
        self.lbl_acct.setText("已改名。" if ok else "改名失败。")
        self._refresh_v2()

    def _delete_account(self):
        it = self.lst_acct.currentItem()
        if it is None:
            return
        ok = self.ctl.delete_account(it.data(Qt.UserRole))
        self.lbl_acct.setText("已删除。" if ok else "至少保留一个账号。")
        self._refresh_v2()

    # ---- 定时 ----
    def _add_sched(self):
        kind = self.cmb_sched_kind.currentData() or "daily"
        when = self.ed_sched_when.text().strip()
        text = self.ed_sched_text.text().strip()
        if not when or not text:
            return
        self.ctl.add_schedule(kind, when, text)
        self.ed_sched_text.clear()
        self._refresh_v2()

    def _del_sched(self):
        it = self.lst_sched.currentItem()
        if it is None:
            return
        self.ctl.remove_schedule(it.data(Qt.UserRole))
        self._refresh_v2()

    def _toggle_sched(self):
        it = self.lst_sched.currentItem()
        if it is None:
            return
        cur_on = it.text().startswith("[开]")
        self.ctl.toggle_schedule(it.data(Qt.UserRole), not cur_on)
        self._refresh_v2()

    def _refresh_usage(self):
        self.txt_usage.setPlainText(self.ctl.yesterday_report() or "昨天没有使用记录。")

