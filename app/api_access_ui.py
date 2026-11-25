# -*- coding: utf-8 -*-
"""模型 API 接入卡片（v3.0.15）。

界面参照两张参考图：
  · 配置态：标题 + 状态点 + 名称/API 地址/API 格式（OpenAI·Anthropic·Gemini 药丸）
    + API Key（带眼睛）+ 高级设置折叠 + 模型列表（+ 添加模型）
    + 底部「获取模型列表」「保存」
  · 接入态：已接入列表每项一行：名称 + 绿点「已连接」+ 编辑/断开

只负责界面与配置读写；请求怎么拼交给 api_access。
"""
import json

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QToolButton, QVBoxLayout, QWidget,
)

import api_access
import theme


def card_qss(mode: str = "auto") -> str:
    """v3.0.23（第 3 条）：卡片配色跟着面板主题走，不再写死紫粉。

    原来整套 #221F2B / #E8447F 是照着深色参考图调的，放到蓝黑主题里就发紫、
    输入框像一块脏棕色；浅色主题下更糟。这里统一取 theme.palette() 的字段。
    """
    p = theme.palette(mode)
    return f"""
#ApiCard {{ background:{p['chat_bg']}; border:1px solid {p['chat_border']}; border-radius:14px; }}
#ApiCard QLabel {{ color:{p['label']}; }}
#ApiCard QLabel#H1 {{ color:{p['label']}; font-size:16px; font-weight:600; }}
#ApiCard QLabel#Sub {{ color:{p['hint']}; font-size:12px; }}
#ApiCard QLabel#Field {{ color:{p['hint']}; font-size:12px; }}
#ApiCard QLabel#Rule {{ color:{p['accent']}; font-size:11px; }}
#ApiCard QLabel#Hint {{ color:{p['hint']}; font-size:11px; }}
#ApiCard QLineEdit, #ApiCard QComboBox {{
    background:{p['input_bg']}; border:1px solid {p['input_border']}; border-radius:10px;
    color:{p['label']}; padding:8px 12px; font-size:13px;
}}
#ApiCard QLineEdit:focus, #ApiCard QComboBox:focus {{ border:1px solid {p['accent']}; }}
#ApiCard QComboBox QAbstractItemView {{
    background:{p['input_bg']}; color:{p['label']}; selection-background-color:{p['accent']};
    border:1px solid {p['input_border']};
}}
#ApiCard QPushButton#Pill {{
    background:{p['input_bg']}; border:1px solid {p['input_border']}; border-radius:14px;
    color:{p['label']}; padding:5px 16px; font-size:12px;
}}
#ApiCard QPushButton#Pill:checked {{
    background:{p['chat_bg']}; border:1px solid {p['accent']}; color:{p['accent']}; font-weight:600;
}}
#ApiCard QPushButton#Primary {{
    background:{p['accent']}; border:none; border-radius:10px;
    color:#FFFFFF; padding:8px 24px; font-size:13px; font-weight:600;
}}
#ApiCard QPushButton#Primary:hover {{ background:{p['accent']}; }}
#ApiCard QPushButton#Ghost {{
    background:transparent; border:none; color:{p['accent']}; font-size:12px; padding:4px 6px;
}}
#ApiCard QPushButton#GhostSmall {{
    background:transparent; border:none; color:{p['accent']}; font-size:11px; padding:2px 4px;
}}
#ApiCard QPushButton#RowBtn {{
    background:transparent; border:1px solid {p['input_border']}; border-radius:8px;
    color:{p['hint']}; font-size:11px; padding:3px 10px;
}}
#ApiCard QPushButton#RowBtn:hover {{ border:1px solid {p['accent']}; color:{p['accent']}; }}
#ApiCard QPushButton#Danger {{
    background:transparent; border:1px solid #C0554B; border-radius:8px;
    color:#E88A80; font-size:11px; padding:3px 10px;
}}
#ApiCard QToolButton#Adv {{
    background:transparent; border:none; color:{p['hint']}; font-size:12px;
}}
#ApiCard QToolButton#Adv:hover {{ color:{p['accent']}; }}
#ApiCard QFrame#Rule2 {{ background:{p['input_border']}; max-height:1px; border:none; }}
"""


class FetchModelsWorker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, fmt: str, endpoint: str, api_key: str):
        super().__init__()
        self.fmt, self.endpoint, self.api_key = fmt, endpoint, api_key

    def run(self):
        try:
            self.done.emit(api_access.list_models(self.fmt, self.endpoint, self.api_key))
        except api_access.Unsupported as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"拉取失败：{type(e).__name__}")


class ApiAccessCard(QWidget):
    """模型 API 接入卡片。ctl 需提供 profiles() / config / save_config()。"""

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.setObjectName("ApiCard")
        self._pal = theme.palette(ctl.config.get("theme", "auto"))
        self.setStyleSheet(card_qss(ctl.config.get("theme", "auto")))
        self._fmt = "openai"
        self._idx = 0
        self._fetch_worker = None
        self._dirty = False          # v3.0.23：正在填的草稿，别被 refresh/自动更新冲掉
        self._loading = False
        self._build()
        self.refresh()

    def apply_theme(self):
        """面板切主题时跟着换色（v3.0.23）。"""
        mode = self.ctl.config.get("theme", "auto")
        self._pal = theme.palette(mode)
        self.setStyleSheet(card_qss(mode))
        self.refresh()

    # ---------------- 界面 ----------------
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 16)
        root.setSpacing(9)

        head = QHBoxLayout()
        head.setSpacing(8)
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color:#8F8A9C;font-size:12px;")
        head.addWidget(self.dot)
        self.lbl_title = QLabel("模型 API 接入")
        self.lbl_title.setObjectName("H1")
        head.addWidget(self.lbl_title)
        self.lbl_state = QLabel("未连接")
        self.lbl_state.setObjectName("State")
        self.lbl_state.setStyleSheet("color:#8F8A9C;font-size:12px;")
        head.addWidget(self.lbl_state)
        head.addStretch(1)
        self.btn_new = QPushButton("+ 新增接入")
        self.btn_new.setObjectName("Ghost")
        self.btn_new.clicked.connect(self._new_profile)
        head.addWidget(self.btn_new)
        root.addLayout(head)

        self.lbl_sub = QLabel("AI 模型决定她的说话水平，接一个高质量的会明显不一样")
        self.lbl_sub.setObjectName("Sub")
        root.addWidget(self.lbl_sub)

        line1 = QFrame()
        line1.setObjectName("Rule2")
        root.addWidget(line1)

        # 已接入列表
        self.list_host = QWidget()
        self.list_box = QVBoxLayout(self.list_host)
        self.list_box.setContentsMargins(0, 0, 0, 2)
        self.list_box.setSpacing(6)
        root.addWidget(self.list_host)

        line2 = QFrame()
        line2.setObjectName("Rule2")
        root.addWidget(line2)

        # 名称
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("名称（例如 我的 GPT 中转）")
        root.addWidget(self.ed_name)

        # API 地址
        self.ed_endpoint = QLineEdit()
        self.ed_endpoint.setPlaceholderText("API 地址（如 https://open.bigmodel.cn/api/paas/v4）")
        root.addWidget(self.ed_endpoint)

        # API 格式
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(8)
        lbl_fmt = QLabel("API 格式")
        lbl_fmt.setObjectName("Field")
        fmt_row.addWidget(lbl_fmt)
        self.fmt_btns = {}
        for key in api_access.FORMATS:
            b = QPushButton(api_access.FORMAT_LABELS[key])
            b.setObjectName("Pill")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.clicked.connect(lambda _=False, k=key: self._set_fmt(k))
            fmt_row.addWidget(b)
            self.fmt_btns[key] = b
        fmt_row.addStretch(1)
        root.addLayout(fmt_row)

        self.lbl_rule = QLabel("ⓘ 查看填写规则")
        self.lbl_rule.setObjectName("Rule")
        self.lbl_rule.setCursor(Qt.PointingHandCursor)
        self.lbl_rule.mousePressEvent = lambda _e: self._show_rule()
        root.addWidget(self.lbl_rule)

        # API Key + 眼睛
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self.ed_key = QLineEdit()
        self.ed_key.setEchoMode(QLineEdit.Password)
        self.ed_key.setPlaceholderText("API Key")
        key_row.addWidget(self.ed_key, 1)
        self.btn_eye = QPushButton("👁")
        self.btn_eye.setObjectName("RowBtn")
        self.btn_eye.setFixedWidth(38)
        self.btn_eye.setCheckable(True)
        self.btn_eye.setToolTip("显示 / 隐藏 Key")
        self.btn_eye.clicked.connect(self._toggle_eye)
        key_row.addWidget(self.btn_eye)
        root.addLayout(key_row)

        # 高级设置
        self.btn_adv = QToolButton()
        self.btn_adv.setObjectName("Adv")
        self.btn_adv.setText("▸ 高级设置")
        self.btn_adv.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_adv.clicked.connect(self._toggle_adv)
        root.addWidget(self.btn_adv)

        self.adv_box = QWidget()
        adv = QVBoxLayout(self.adv_box)
        adv.setContentsMargins(0, 2, 0, 2)
        adv.setSpacing(6)
        self.ed_proxy = QLineEdit()
        self.ed_proxy.setPlaceholderText("代理（可留空，如 http://127.0.0.1:7890）")
        adv.addWidget(self.ed_proxy)
        self.ed_headers = QLineEdit()
        self.ed_headers.setPlaceholderText('自定义请求头（JSON，可留空，如 {"X-Title":"whale"}）')
        adv.addWidget(self.ed_headers)
        self.ed_params = QLineEdit()
        self.ed_params.setPlaceholderText('参数覆盖（JSON，如 {"top_p":0.9}）')
        adv.addWidget(self.ed_params)
        self.adv_box.setVisible(False)
        root.addWidget(self.adv_box)

        # 模型列表
        ml_head = QHBoxLayout()
        lbl_m = QLabel("模型列表")
        lbl_m.setObjectName("Field")
        ml_head.addWidget(lbl_m)
        ml_head.addStretch(1)
        self.btn_add_model = QPushButton("+ 添加模型")
        self.btn_add_model.setObjectName("GhostSmall")
        self.btn_add_model.clicked.connect(self._add_model)
        ml_head.addWidget(self.btn_add_model)
        root.addLayout(ml_head)

        self.cb_model = QComboBox()
        self.cb_model.setEditable(True)
        self.cb_model.setPlaceholderText("还没选模型：点下方「获取模型列表」自动带出，或直接手填")
        root.addWidget(self.cb_model)
        self.lbl_models_hint = QLabel("暂无模型：可手动添加，或点下方「获取模型列表」自动带出")
        self.lbl_models_hint.setObjectName("Hint")
        root.addWidget(self.lbl_models_hint)

        foot = QHBoxLayout()
        self.btn_fetch = QPushButton("获取模型列表")
        self.btn_fetch.setObjectName("Ghost")
        self.btn_fetch.clicked.connect(self._fetch)
        foot.addWidget(self.btn_fetch)
        self.btn_test = QPushButton("测试连接")
        self.btn_test.setObjectName("Ghost")
        self.btn_test.clicked.connect(self._on_test)
        foot.addWidget(self.btn_test)
        foot.addStretch(1)
        self.btn_save = QPushButton("保存")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self._save)
        foot.addWidget(self.btn_save)
        root.addLayout(foot)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("Hint")
        self.lbl_status.setWordWrap(True)
        root.addWidget(self.lbl_status)

        # 第 4 条：任何输入都记为草稿，刷新/更新/重开面板都不会把已填的冲没
        for ed in (self.ed_name, self.ed_endpoint, self.ed_key,
                   self.ed_proxy, self.ed_headers, self.ed_params):
            ed.textChanged.connect(self._mark_dirty)
        self.cb_model.currentTextChanged.connect(self._mark_dirty)

    # ---------------- 数据 ----------------
    def _profiles(self) -> list:
        try:
            return self.ctl.profiles()
        except Exception:  # noqa: BLE001
            return []

    def _current(self) -> dict:
        ps = self._profiles()
        if not ps:
            return {}
        self._idx = max(0, min(self._idx, len(ps) - 1))
        prof = ps[self._idx]
        prof.setdefault("api_format", "openai")
        prof.setdefault("models", [])
        return prof

    def refresh(self):
        """外部（panel.refresh）会调用：重建已接入列表 + 回填当前档。"""
        self._idx = int(self.ctl.config.get("active_profile", 0) or 0)
        self._rebuild_list()
        self._fill()

    def _rebuild_list(self):
        while self.list_box.count():
            item = self.list_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        ps = self._profiles()
        if not ps:
            return
        for i, p in enumerate(ps):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(8)
            connected = bool(p.get("connected"))
            dot = QLabel("●")
            dot.setStyleSheet("color:%s;font-size:11px;" % ("#3DDC84" if connected else self._pal["hint"]))
            h.addWidget(dot)
            name = QLabel(str(p.get("name") or f"接入 {i + 1}"))
            name.setStyleSheet(f"color:{self._pal['label']};font-size:13px;font-weight:600;")
            h.addWidget(name)
            badge = QLabel("已连接" if connected else "未连接")
            badge.setStyleSheet("color:%s;font-size:11px;" % ("#3DDC84" if connected else self._pal["hint"]))
            h.addWidget(badge)
            mdl = QLabel(str(p.get("model") or ""))
            mdl.setStyleSheet(f"color:{self._pal['hint']};font-size:11px;")
            h.addWidget(mdl)
            h.addStretch(1)
            if i != self._idx:
                b_use = QPushButton("使用")
                b_use.setObjectName("RowBtn")
                b_use.clicked.connect(lambda _=False, k=i: self._use(k))
                h.addWidget(b_use)
            b_edit = QPushButton("编辑")
            b_edit.setObjectName("RowBtn")
            b_edit.clicked.connect(lambda _=False, k=i: self._use(k))
            h.addWidget(b_edit)
            b_del = QPushButton("断开")
            b_del.setObjectName("Danger")
            b_del.clicked.connect(lambda _=False, k=i: self._disconnect(k))
            h.addWidget(b_del)
            self.list_box.addWidget(row)

    def _fill(self, force: bool = False):
        prof = self._current()
        if not prof:
            return
        # 用户正在编辑（或上次没保存就退出）时，不要用存档覆盖屏幕上的字
        if self._dirty and not force:
            self._update_state()
            return
        draft = self.ctl.config.get("api_draft") or {}
        use_draft = (draft and draft.get("idx") == self._idx
                     and draft.get("endpoint"))
        src = draft if use_draft else prof
        self._loading = True
        try:
            self.ed_name.setText(str(src.get("name", "")))
            self.ed_endpoint.setText(str(src.get("endpoint", "")))
            self._set_fmt(str(src.get("api_format", "openai")))
            self.ed_key.setText(str(src.get("api_key", "")))
            self.ed_proxy.setText(str(src.get("proxy", "")))
            self.ed_headers.setText(str(src.get("headers", "")))
            self.ed_params.setText(str(src.get("params", "")))
            self.cb_model.clear()
            models = list(prof.get("models") or [])
            if prof.get("model") and prof["model"] not in models:
                models.insert(0, prof["model"])
            self.cb_model.addItems(models)
            self.cb_model.setCurrentText(str(src.get("model", "") or prof.get("model", "")))
        finally:
            self._loading = False
        if use_draft:
            self._dirty = True
        self._update_state()

    def _mark_dirty(self, *_args):
        if self._loading:
            return
        self._dirty = True
        try:
            self.ctl.config["api_draft"] = {
                "idx": self._idx,
                "name": self.ed_name.text(),
                "endpoint": self.ed_endpoint.text(),
                "api_format": self._fmt,
                "api_key": self.ed_key.text(),
                "proxy": self.ed_proxy.text(),
                "headers": self.ed_headers.text(),
                "params": self.ed_params.text(),
                "model": self.cb_model.currentText(),
            }
            self.ctl.save_config()
        except Exception:  # noqa: BLE001
            pass

    def _update_state(self):
        prof = self._current()
        connected = bool(prof.get("connected"))
        has_key = bool(str(prof.get("api_key", "")).strip())
        if connected:
            self.dot.setStyleSheet("color:#3DDC84;font-size:12px;")
            self.lbl_state.setText("已连接")
            self.lbl_state.setStyleSheet("color:#3DDC84;font-size:12px;")
        elif has_key:
            self.dot.setStyleSheet("color:#E8B93F;font-size:12px;")
            self.lbl_state.setText("已配置·未验证")
            self.lbl_state.setStyleSheet("color:#E8B93F;font-size:12px;")
        else:
            self.dot.setStyleSheet("color:#8F8A9C;font-size:12px;")
            self.lbl_state.setText("未连接")
            self.lbl_state.setStyleSheet("color:#8F8A9C;font-size:12px;")
        n = len(prof.get("models") or [])
        if self.cb_model.currentText().strip() or n:
            self.lbl_models_hint.setVisible(False)
        else:
            self.lbl_models_hint.setVisible(True)

    # ---------------- 交互 ----------------
    def _set_fmt(self, fmt: str):
        self._fmt = fmt if fmt in api_access.FORMATS else "openai"
        for k, b in self.fmt_btns.items():
            b.setChecked(k == self._fmt)

    def _on_test(self):
        try:
            self.ctl.test_ai_connection()
        except Exception:  # noqa: BLE001
            self.lbl_status.setText("测试连接没跑起来（控制器未就绪）。")

    def _show_rule(self):
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, f"{api_access.FORMAT_LABELS[self._fmt]} 填写规则",
                                    api_access.test_rule_text(self._fmt))
        except Exception:  # noqa: BLE001
            self.lbl_status.setText(api_access.test_rule_text(self._fmt))

    def _toggle_eye(self):
        self.ed_key.setEchoMode(
            QLineEdit.Normal if self.btn_eye.isChecked() else QLineEdit.Password)

    def _toggle_adv(self):
        on = not self.adv_box.isVisible()
        self.adv_box.setVisible(on)
        self.btn_adv.setText(("▾ 高级设置" if on else "▸ 高级设置"))

    def _add_model(self):
        self.cb_model.setEditable(True)
        self.cb_model.setCurrentText("")
        self.cb_model.lineEdit().setFocus()
        self.lbl_status.setText("直接输入模型名，再点保存。")

    def _use(self, idx: int):
        self._idx = idx
        self._dirty = False
        if hasattr(self.ctl, "config"):
            self.ctl.config["active_profile"] = idx
            try:
                self.ctl.save_config()
            except Exception:  # noqa: BLE001
                pass
        self._rebuild_list()
        self._fill()

    def _new_profile(self):
        try:
            self.ctl.new_profile()
        except Exception:  # noqa: BLE001
            ps = self._profiles()
            ps.append({"name": f"接入 {len(ps) + 1}", "endpoint": "", "model": "",
                       "api_key": "", "api_format": "openai", "models": []})
            self.ctl.config["active_profile"] = len(ps) - 1
        self.refresh()
        self.lbl_status.setText("已新增一个接入点，填完点保存。")

    def _disconnect(self, idx: int):
        ps = self._profiles()
        if not (0 <= idx < len(ps)):
            return
        ps[idx]["connected"] = False
        ps[idx]["api_key"] = ""
        try:
            self.ctl.save_config()
        except Exception:  # noqa: BLE001
            pass
        self.refresh()
        self.lbl_status.setText("已断开并清空 Key（配置其余字段保留）。")

    def _fetch(self):
        if self._fetch_worker is not None and self._fetch_worker.isRunning():
            return
        key = self.ed_key.text().strip()
        if not key:
            self.lbl_status.setText("先填 API Key 才能拉模型列表。")
            return
        self.lbl_status.setText("正在拉取模型列表……")
        self.btn_fetch.setEnabled(False)
        self._fetch_worker = FetchModelsWorker(self._fmt, self.ed_endpoint.text(), key)
        self._fetch_worker.done.connect(self._on_fetch_done)
        self._fetch_worker.failed.connect(self._on_fetch_fail)
        self._fetch_worker.start()

    def _on_fetch_done(self, models: list):
        self.btn_fetch.setEnabled(True)
        if not models:
            self.lbl_status.setText("对方返回了空列表，手动填模型名吧。")
            return
        cur = self.cb_model.currentText().strip()
        self.cb_model.clear()
        self.cb_model.addItems(models)
        if cur:
            self.cb_model.setCurrentText(cur)
        else:
            self.cb_model.setCurrentIndex(0)
        self.lbl_models_hint.setVisible(False)
        self.lbl_status.setText(f"拉到 {len(models)} 个模型，选一个后点保存。")

    def _on_fetch_fail(self, msg: str):
        self.btn_fetch.setEnabled(True)
        self.lbl_status.setText(msg)

    def _save(self):
        prof = self._current()
        if not prof:
            return
        fmt = self._fmt
        prof["name"] = self.ed_name.text().strip() or "未命名接入"
        prof["endpoint"] = self.ed_endpoint.text().strip()
        prof["api_format"] = fmt
        prof["api_key"] = self.ed_key.text().strip()
        prof["proxy"] = self.ed_proxy.text().strip()
        prof["headers"] = self.ed_headers.text().strip()
        prof["params"] = self.ed_params.text().strip()
        model = self.cb_model.currentText().strip()
        prof["model"] = model
        models = [self.cb_model.itemText(i) for i in range(self.cb_model.count())]
        if model and model not in models:
            models.insert(0, model)
        prof["models"] = models
        # 填了 Key 且地址像样，先按「已配置」算；真正的已连接由测试连接成功后置位
        prof["connected"] = bool(prof["api_key"]) and bool(
            prof["endpoint"] or fmt != "openai")
        for line, key in (("headers", "自定义请求头"), ("params", "参数覆盖")):
            raw = prof.get(line) or ""
            if raw:
                try:
                    json.loads(raw)
                except ValueError:
                    self.lbl_status.setText(f"{key}不是合法 JSON，已保存但不会生效。")
                    break
        try:
            self.ctl.save_config()
        except Exception:  # noqa: BLE001
            pass
        self._dirty = False
        try:
            self.ctl.config.pop("api_draft", None)
        except Exception:  # noqa: BLE001
            pass
        self.refresh()
        self.lbl_status.setText("已保存。")

    def set_connected(self, ok: bool, msg: str = ""):
        """测试连接回调：main.test_ai_connection 成功时调用。"""
        prof = self._current()
        if prof:
            prof["connected"] = bool(ok)
            try:
                self.ctl.save_config()
            except Exception:  # noqa: BLE001
                pass
        self._update_state()
        if msg:
            self.lbl_status.setText(msg)
