# -*- coding: utf-8 -*-
"""桌宠主窗口：透明无边框置顶，拖拽 / 单击摸头 / 双击面板 / 右键菜单 / 滚轮缩放 / 状态机动画。"""
import math
import random

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (QAction, QCursor, QGuiApplication, QImage, QPainter, QPainterPath,
                           QPixmap, QRegion, qAlpha)
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from paths import (ACTIONS, EXPRESSIONS, FORM_DEFAULT_SKIN, FORM_LABELS, FORM_SKINS,
                   SKINS, SKIN_FORM, asset_path)
from bubble import BubbleWindow
from voice_profile import profile_names as voice_profile_names

FRAME_MS = 33
# v2.9.2 动起来被裁边：窗口比立绘大一圈，给 bob/旋转/缩放留出活动余量
# 0.18 可容下起跳 64px 与中等摆动；摔跤那种 60°+ 翻转仍可能轻擦边（下一步做按动作动态扩容）
PAD_RATIO = 0.18
# 分段步态的关节位置（相对立绘高度，从顶部算）
HIP_RATIO = 0.60      # 髋（腰以下开始摆）
ANKLE_RATIO = 0.88    # 踝（脚再做一次反相）
GAIT_STATES = ("walk", "run", "floatstep", "trot", "crab", "hop")

# 纯代码动作（无专属立绘，复用现有素材 + 位移动画）
CODE_ACTIONS = ["crab", "floatstep", "trot", "look", "eatrice", "tumble", "brawl", "hop"]
# 带专属立绘的动作
SPRITE_ACTIONS = list(ACTIONS.keys())
ALL_ACTIONS = SPRITE_ACTIONS + CODE_ACTIONS
CODE_ACTION_LABELS = {
    "crab": "螃蟹步", "floatstep": "漂浮踏步", "trot": "小跑",
    "look": "左右看", "eatrice": "吃白饭",
    "tumble": "摔一跤", "brawl": "打闹", "hop": "蹦蹦跳",
}


def action_label(key: str) -> str:
    return ACTIONS.get(key, (CODE_ACTION_LABELS.get(key, key),))[0]


class PetWindow(QWidget):
    def __init__(self, controller):
        self._controller = controller
        flags = Qt.FramelessWindowHint | Qt.Tool
        self._topmost = True
        flags |= Qt.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("鲸鱼娘桌宠")

        self.pix_cache = {}
        self.base = self._load_skin(controller.config.get("skin", "default"))
        self._foot_cache = {}          # 脚底行缓存：切皮肤/表情后按底边对齐地面（v2.8）
        self.night = False             # 夜间模式：呼吸幅度收窄（v2.8）
        self._pix = QPixmap()
        self._pad = 0
        self.scale = float(controller.config.get("scale", 1.0))

        # 动画状态
        self.state = "idle"
        self.state_t = 0.0
        self.rot = 0.0
        self.sx = 1.0
        self.sy = 1.0
        self.bob = 0.0
        self.mirror = False
        self.alpha = 1.0
        self.jump_x0 = 0
        self.jump_y0 = 0

        # 表情
        self.expr = "idle"
        self._expr_timer = QTimer(self)
        self._expr_timer.setSingleShot(True)
        self._expr_timer.timeout.connect(self.restore_base_expression)

        # 拟人动作物理量
        self._vel_x = 0.0
        self._lean = 0.0        # 重心前倾角，跟随速度
        self._spin = 0.0        # 摔跤翻转累计角
        self._airborne = 0.0    # 腾空高度
        self._bounce_t = 0.0

        self._run_timer = None
        self._action_timer = None
        self.action_key = ""
        # 分段步态状态
        self.gait = 0.0
        self.gait_on = False
        self.gait_amp = 6.0
        self._upper = None
        self._leg = None
        self._foot = None
        self._hip_y = 0
        self._ank_y = 0

        # 拖拽
        self.drag_active = False
        self.drag_offset = QPoint()
        self.drag_moved = 0
        self.last_gp = QPoint()
        self.vx = self.vy = 0

        # 行走 / 跟随
        self.walk_dir = 1
        self.run_dir = 1
        self.follow = False

        self.anim = QTimer(self)
        self.anim.setInterval(FRAME_MS)
        self.anim.timeout.connect(self._tick)
        self.anim.start()

        self.bubble = BubbleWindow(self)

        self._update_pix()
        self._load_position()
        self._clamp_to_screen()
        self.show()

    # ================= 素材 =================
    def _load_pix(self, rel: str) -> QPixmap:
        if rel not in self.pix_cache:
            pm = QPixmap(asset_path(rel))
            self.pix_cache[rel] = pm
        return self.pix_cache[rel]

    def _load_skin(self, skin_key: str) -> QPixmap:
        rel = SKINS.get(skin_key, SKINS["default"])[1]
        return self._load_pix(rel)

    def set_skin(self, skin_key: str):
        self._controller.config["skin"] = skin_key
        self.base = self._load_skin(skin_key)
        self.restore_base_expression()
        self._update_pix()

    # ---------- 形态（成熟 / 萝莉） ----------
    def current_form(self) -> str:
        return SKIN_FORM.get(self._controller.config.get("skin", "default"), "mature")

    def set_form(self, form: str):
        if form not in FORM_DEFAULT_SKIN:
            return
        self._controller.config["form"] = form
        skin = self._controller.config.get("skin", "default")
        if SKIN_FORM.get(skin) != form:
            skin = FORM_DEFAULT_SKIN[form]
            self._controller.config["skin"] = skin
        self.base = self._load_skin(skin)
        self.restore_base_expression()
        self._update_pix()
        self._controller.on_form_change(form, skin)

    def set_expression(self, expr: str, revert_ms: int = 2600):
        rel = EXPRESSIONS.get(expr)
        skin_now = self._controller.config.get("skin", "default")
        if rel and skin_now == "default":
            # 表情差分只有默认女仆装有；其他皮肤保留自身立绘，避免切装后被表情跳回女仆装
            self.base = self._load_pix(rel)
            self._update_pix()
        elif rel:
            self.bob -= 5.0 * self.scale      # 轻微一顿，表示有反应
        if rel:
            self.expr = expr
        if revert_ms > 0:
            self._expr_timer.start(revert_ms)

    def restore_base_expression(self):
        self._expr_timer.stop()
        skin = self._controller.config.get("skin", "default")
        self.base = self._load_skin(skin)
        self.expr = "idle"
        self._update_pix()

    # ================= 基础几何 =================
    def _foot_row(self, pm: QPixmap) -> int:
        """alpha 最低的不透明行（脚底），用于让窗口底边对齐地面；结果按 pixmap 缓存。"""
        key = pm.cacheKey()
        hit = self._foot_cache.get(key)
        if hit is not None:
            return hit
        img = pm.toImage()
        w, h = img.width(), img.height()
        step_x = max(1, w // 32)
        row = h
        for y in range(h - 1, -1, -1):
            for x in range(0, w, step_x):
                if img.pixelColor(x, y).alpha() > 8:
                    row = y + 1
                    break
            if row != h:
                break
        self._foot_cache[key] = row
        return row

    def _update_pix(self):
        base = self.base
        # v2.8 脚底对齐：裁掉底部透明边，窗口底边即脚底，换皮肤不再上下漂
        if self._controller.config.get("anchor_crop", True):
            foot = self._foot_row(base)
            if 0 < foot < base.height():
                base = base.copy(0, 0, base.width(), foot)
        bw = max(1, int(base.width() * self.scale))
        bh = max(1, int(base.height() * self.scale))
        self._pix = base.scaled(bw, bh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pw, ph = self._pix.width(), self._pix.height()
        # 活动余量：动作时人物会 bob/旋转/横向摆出立绘边界，窗口必须比立绘大一圈
        pad = max(12, int(ph * PAD_RATIO))
        self._pad = pad
        self.resize(pw + 2 * pad, ph + 2 * pad)
        self._apply_mask()
        self._split_limbs()

    def _apply_mask(self):
        """可选蒙版（默认关闭，仅作兜底）。

        v2.9.1 用蒙版去黑框，但蒙版是 1-bit 硬边：立绘边缘出现锯齿，动作帧变化后
        蒙版不跟着变，人物一晃出边界就被裁掉。v2.9.2 实测透明合成本身没有黑框，
        所以默认走真透明；这里保留开关，开启时用 2px 网格并加上活动余量偏移。
        """
        if not self._controller.config.get("alpha_mask", False):
            self.clearMask()
            return
        if self._pix.isNull():
            return
        step = 2
        img = self._pix.toImage()
        sw = max(1, img.width() // step)
        sh = max(1, img.height() // step)
        img = img.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        pad = getattr(self, "_pad", 0)
        rgn = QRegion()
        for y in range(sh):
            start = -1
            for x in range(sw):
                solid = qAlpha(img.pixel(x, y)) > 24
                if solid and start < 0:
                    start = x
                elif not solid and start >= 0:
                    rgn = rgn.united(QRegion(pad + start * step, pad + y * step,
                                             (x - start) * step, step))
                    start = -1
            if start >= 0:
                rgn = rgn.united(QRegion(pad + start * step, pad + y * step,
                                         (sw - start) * step, step))
        self.setMask(rgn)

    # ---- v2.3.0 分段步态：把立绘按髋/踝切成三段，走路时各段独立摆动 ----
    def _split_limbs(self):
        ph, pw = self._pix.height(), self._pix.width()
        hip = max(2, int(ph * HIP_RATIO))
        ank = max(hip + 2, int(ph * ANKLE_RATIO))
        self._upper = self._pix.copy(0, 0, pw, hip)
        self._leg = self._pix.copy(0, hip, pw, ank - hip)
        self._foot = self._pix.copy(0, ank, pw, ph - ank)
        self._hip_y, self._ank_y = hip, ank

    def set_pet_scale(self, s: float, anchor_bottom=True):
        s = max(0.35, min(2.2, s))
        if abs(s - self.scale) < 0.01:
            return
        if anchor_bottom:
            bc = self.frameGeometry().bottomLeft()
            bc.setX(bc.x() + self.width() // 2)
        self.scale = s
        self._controller.config["scale"] = round(s, 3)
        self._update_pix()
        if anchor_bottom:
            self.move(bc.x() - self.width() // 2, bc.y() - self.height() + self._pad)
        self._clamp_to_screen()
        self.bubble.update_position()

    def is_topmost(self):
        return bool(self.windowFlags() & Qt.WindowStaysOnTopHint)

    def set_topmost(self, on: bool):
        self._topmost = bool(on)
        self._controller.config["topmost"] = self._topmost
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._topmost)
        if visible:
            self.show()
        self.bubble.setWindowFlag(Qt.WindowStaysOnTopHint, self._topmost)
        if self.bubble.isVisible():
            self.bubble.show()

    # ================= 状态机 =================
    def set_state(self, st: str):
        self.state = st
        self.state_t = 0.0
        if st == "jump":
            self.jump_x0 = self.x()
            self.jump_y0 = self.y()

    def finish_state(self):
        if self._run_timer is not None:
            self._run_timer.stop()
        if self._action_timer is not None:
            self._action_timer.stop()
        self.restore_base_expression()
        self.rot = 0.0
        self.sx = 1.0
        self.sy = 1.0
        self.bob = 0.0
        self._lean = 0.0
        self._airborne = 0.0
        self.mirror = False
        self.set_state("follow" if self.follow else "idle")

    def _tick(self):
        self.state_t += FRAME_MS / 1000.0
        st = self.state

        # 步态相位：走路 1 循环/秒，奔跑 1.8 倍速、摆幅更大
        self.gait_on = st in GAIT_STATES
        if self.gait_on:
            self.gait_amp = 11.0 if st == "run" else 6.0
            step = (FRAME_MS / 1000.0) * (1.8 if st == "run" else 1.0)
            self.gait = (self.gait + step) % 1.0

        if st in ("idle", "walk", "follow", "sleep", "run", "wave", "dance", "type",
                  "balloon", "fireworks", "lion", "change", "floatstep", "look", "panic",
                  "brawl", "hop"):
            self.rot = 0.0
            self.mirror = False

        if st == "idle":
            self.alpha = 1.0
            self.bob = 0.0
            amp = 0.003 if self.night else 0.006    # 夜间呼吸收一半，像在打盹
            self.sy = 1 + amp * math.sin(self.state_t * 2.5)
            self.sx = 1 - (amp * 0.5) * math.sin(self.state_t * 2.5)

        elif st == "drag":
            self.alpha = 1.0
            if abs(self.vx) > 2:
                self.mirror = self.vx < 0
            self.bob = -4 * abs(math.sin(self.state_t * 12)) * self.scale
            self.rot = 5 * math.sin(self.state_t * 12)
            self.sy = 1 + 0.03 * math.sin(self.state_t * 12)
            self.sx = 1 - 0.02 * math.sin(self.state_t * 12)

        elif st == "jump":
            dur = 0.7
            t = min(self.state_t / dur, 1.0)
            height = 150 * self.scale
            y = -height * math.sin(math.pi * t)
            self.move(self.jump_x0, self.jump_y0 + int(y))
            self.rot = 15 * math.sin(math.pi * t)
            if t > 0.82:
                u = (t - 0.82) / 0.18
                self.sy = 1 - 0.13 * math.sin(math.pi * u)
                self.sx = 1 + 0.11 * math.sin(math.pi * u)
            else:
                self.sy = self.sx = 1.0
            if t >= 1.0:
                self.move(self.jump_x0, self.jump_y0)
                self.finish_state()

        elif st == "squish":
            if self.state_t < 0.25:
                u = self.state_t / 0.25
                self.sy = 1 - 0.42 * u
                self.sx = 1 + 0.30 * u
            else:
                u = self.state_t - 0.25
                self.sy = 1 + 0.13 * math.exp(-5 * u) * math.cos(14 * u)
                self.sx = 1 - 0.10 * math.exp(-5 * u) * math.cos(14 * u)
            if self.state_t >= 1.3:
                self.finish_state()

        elif st == "shake":
            dur = 0.5
            t = self.state_t
            env = max(0.0, 1.0 - t / dur)
            self.rot = 13 * math.sin(2 * math.pi * 9 * t) * env
            self.bob = -3 * abs(math.sin(2 * math.pi * 9 * t)) * env
            if t >= dur:
                self.finish_state()

        elif st == "walk":
            # v2.6：不再靠近边缘减速；允许探出屏 12% 再回头
            v = 2.4 * self.scale
            scr = QGuiApplication.primaryScreen().availableGeometry()
            over = self._edge_over()
            x = self.x() + int(self.walk_dir * v)
            if x <= scr.left() - over:
                self.walk_dir = 1
            elif x + self.width() >= scr.right() + over:
                self.walk_dir = -1
            self.mirror = self.walk_dir < 0
            self.move(x, self.y())
            self.bob = -4 * abs(math.sin(self.state_t * 8)) * self.scale
            # 步态已经在弯身体了，整图旋转要收着，否则像在"摇"
            self.rot = 1.8 * math.sin(self.state_t * 8)
            if self.state_t >= 8.0:
                self.finish_state()

        elif st == "run":
            # 拟人奔跑：起步加速、匀速、身位前倾、落脚有上下起伏
            speed_ramp = min(1.0, self.state_t / 0.45)
            v = (4.0 + 2.2 * speed_ramp) * self.scale
            scr = QGuiApplication.primaryScreen().availableGeometry()
            over = self._edge_over()
            x = self.x() + int(self.run_dir * v)
            if x <= scr.left() - over:
                self.run_dir = 1
            elif x + self.width() >= scr.right() + over:
                self.run_dir = -1
            self.mirror = self.run_dir < 0
            # 纵向在屏幕中上部区间内缓慢游走，实现满屏跑动
            y = self.y()
            y_target = scr.top() + int((scr.height() - self.height()) * (0.25 + 0.5 * ((self.state_t * 0.13) % 1.0)))
            y += (y_target - y) // 12
            self.move(x, y)
            self._lean = 7.0 * speed_ramp
            self.rot = self._lean + 1.2 * math.sin(self.state_t * 11)
            self.bob = -(8 * abs(math.sin(self.state_t * 10.5)) + 2) * self.scale
            self.sy = 1 + 0.025 * math.sin(self.state_t * 21)
            self.sx = 1 - 0.015 * math.sin(self.state_t * 21)

        elif st == "tumble":
            # 摔一跤：失衡前扑 -> 侧滑腾空 -> 落地压缩 -> 爬起抖两下
            # v2.9.3：原先 rot 一路转到 360°，整张立绘在屏幕上变成横躺（录屏里"躺着的人立起来"），
            # 现在限制在 22° 以内的失衡摆动，保留踩空的观感又不至于躺平
            t = self.state_t
            scr = QGuiApplication.primaryScreen().availableGeometry()
            if t < 0.32:
                u = t / 0.32
                self.rot = 16 * u * u
                self._airborne = -6 * u
                self.bob = self._airborne * self.scale
                self.sy = 1 - 0.06 * u
            elif t < 0.92:
                u = (t - 0.32) / 0.60
                self.rot = 16 + 6 * math.sin(math.pi * u)
                self._airborne = -26 * math.sin(math.pi * u)
                self.bob = self._airborne * self.scale
                self.sy = 1 + 0.04 * math.sin(math.pi * u)
                self.move(self.x() + int(self.run_dir * 2.2 * self.scale), self.y())
                if self.x() <= scr.left() + 10 or self.x() + self.width() >= scr.right() - 10:
                    self.run_dir *= -1
            elif t < 1.45:
                u = (t - 0.92) / 0.53
                self.rot = 16 * (1 - u)
                self.bob = 0
                # 落地压扁再回弹
                self.sy = 1 - 0.30 * math.exp(-3.2 * u) * abs(math.cos(9 * u))
                self.sx = 1 + 0.24 * math.exp(-3.2 * u) * abs(math.cos(9 * u))
            else:
                u = min(1.0, (t - 1.45) / 0.75)
                self.rot = 4 * math.sin(t * 22) * (1 - u)
                self.sy = 1 + 0.02 * math.sin(t * 18)
                self.sx = 1 - 0.01 * math.sin(t * 18)
                if u >= 1.0:
                    self.rot = 0
                    self.finish_state()

        elif st == "brawl":
            # 打闹：忽左忽右快速窜动，身体随加速度歪，抬手比划
            t = self.state_t
            scr = QGuiApplication.primaryScreen().availableGeometry()
            swing = math.sin(t * 6.4)
            v = 5.0 * swing * self.scale
            x = self.x() + int(v)
            if x <= scr.left():
                x = scr.left()
            elif x + self.width() >= scr.right():
                x = scr.right() - self.width()
            self.move(x, self.y())
            self.mirror = swing < 0
            self.rot = -9 * swing + 3.5 * math.sin(t * 18)
            self.bob = -4 * abs(math.sin(t * 18)) * self.scale
            self.sy = 1 + 0.03 * math.sin(t * 13)
            self.sx = 1 - 0.02 * math.sin(t * 13)

        elif st == "hop":
            # 蹦蹦跳：连跳三下，一下比一下矮，落地有压缩
            t = self.state_t
            period = 0.68
            idx = int(t / period)
            u = (t % period) / period
            scales = (1.0, 0.72, 0.5)
            if idx < 3:
                h = 92 * scales[idx] * self.scale
                self.bob = -h * math.sin(math.pi * u)
                if u > 0.78:
                    k = (u - 0.78) / 0.22
                    self.sy = 1 - 0.16 * math.sin(math.pi * k)
                    self.sx = 1 + 0.14 * math.sin(math.pi * k)
                else:
                    self.sy = 1 + 0.05 * math.sin(math.pi * u)
                    self.sx = 1 - 0.04 * math.sin(math.pi * u)
                self.rot = 3 * math.sin(math.pi * u) * (1 if idx % 2 == 0 else -1)
            else:
                self.bob = 0
                self.sy = self.sx = 1.0
                self.rot = 0
                self.finish_state()

        elif st == "sleep":
            self.alpha = 0.85
            self.bob = 0.0
            self.sy = 1 + 0.012 * math.sin(self.state_t * 1.8)
            self.sx = 1 - 0.006 * math.sin(self.state_t * 1.8)

        elif st == "follow":
            c = QCursor.pos()
            dx = c.x() - (self.x() + self.width() // 2)
            dy = c.y() - (self.y() + self.height() // 2)
            self.move(self.x() + int(dx * 0.12), self.y() + int(dy * 0.12))
            self._clamp_to_screen()   # v2.9.4：光标跑到副屏时别把桌宠一并带出主屏
            self.alpha = 1.0
            self.bob = -3 * abs(math.sin(self.state_t * 6)) * self.scale
            self.rot = 4 * math.sin(self.state_t * 6)
            if abs(dx) < 10 and abs(dy) < 10:
                self.bob = 0.0
                self.rot = 0.0

        # ---------- 动作立绘 ----------
        elif st == "wave":
            self.rot = 4 * math.sin(self.state_t * 10)
            self.sy = 1 + 0.02 * math.sin(self.state_t * 10)
            self.sx = 1 - 0.01 * math.sin(self.state_t * 10)
            self.bob = 0.0

        elif st == "dance":
            self.rot = 10 * math.sin(self.state_t * 6)
            self.bob = -5 * abs(math.sin(self.state_t * 6)) * self.scale
            self.sy = 1 + 0.02 * math.sin(self.state_t * 6)

        elif st == "type":
            self.bob = -1 * abs(math.sin(self.state_t * 16)) * self.scale

        elif st == "balloon":
            self.bob = -9 * abs(math.sin(self.state_t * 2.2)) * self.scale
            self.rot = 3 * math.sin(self.state_t * 2.2)

        elif st == "fireworks":
            self.bob = -4 * abs(math.sin(self.state_t * 8)) * self.scale
            self.rot = 3 * math.sin(self.state_t * 8)

        elif st == "lion":
            self.bob = -24 * self.scale * abs(math.sin(self.state_t * 10))
            self.rot = 6 * math.sin(self.state_t * 10)

        elif st == "change":
            self.rot = 3 * math.sin(self.state_t * 3)
            self.sy = 1 + 0.01 * math.sin(self.state_t * 3)

        elif st == "crab":
            crab_dir = 1 if int(self.state_t * 2) % 2 == 0 else -1
            v = 2.6 * self.scale
            scr = QGuiApplication.primaryScreen().availableGeometry()
            over = self._edge_over()
            x = self.x() + int(crab_dir * v)
            if x <= scr.left() - over or x + self.width() >= scr.right() + over:
                crab_dir *= -1
            self.mirror = crab_dir < 0
            self.move(x, self.y())
            self.bob = -3 * abs(math.sin(self.state_t * 10)) * self.scale
            self.rot = 4 * math.sin(self.state_t * 10)

        elif st == "floatstep":
            self.bob = -8 * abs(math.sin(self.state_t * 3)) * self.scale
            self.rot = 3 * math.sin(self.state_t * 3)

        elif st == "trot":
            v = 3.4 * self.scale
            scr = QGuiApplication.primaryScreen().availableGeometry()
            over = self._edge_over()
            x = self.x() + int(self.run_dir * v)
            if x <= scr.left() - over:
                self.run_dir = 1
            elif x + self.width() >= scr.right() + over:
                self.run_dir = -1
            self.mirror = self.run_dir < 0
            self.move(x, self.y())
            self.bob = -5 * abs(math.sin(self.state_t * 10)) * self.scale
            self.rot = 5 * math.sin(self.state_t * 10)

        elif st == "look":
            self.rot = 8 * math.sin(self.state_t * 2.5)
            self.mirror = math.sin(self.state_t * 2.5) > 0

        elif st == "panic":
            self.rot = 12 * math.sin(self.state_t * 30)
            self.bob = -2 * abs(math.sin(self.state_t * 30)) * self.scale
            self.sy = 1 - 0.04 * abs(math.sin(self.state_t * 30))

        self.update()

    # ================= 互动入口（由 controller 转发） =================
    def do_pat(self):
        self.set_expression("pat")
        self.set_state("squish")
        self._controller.on_pat()

    def do_feed(self, snack_key: str):
        self.set_expression("eat")
        self.set_state("squish")
        self._controller.on_feed(snack_key)

    def do_walk(self):
        self.follow = False
        self.set_expression("walk", 8000)
        self.set_state("walk")
        self._controller.on_walk()

    def do_run(self, duration_ms: int = 60000):
        self.follow = False
        self.run_dir = random.choice([-1, 1])
        self.set_expression("walk", 0)
        self.set_state("run")
        self._controller.on_run()
        if duration_ms > 0:
            self._run_timer = QTimer(self)
            self._run_timer.setSingleShot(True)
            self._run_timer.timeout.connect(self.finish_state)
            self._run_timer.start(duration_ms)

    def do_sleep(self):
        self.follow = False
        self.set_expression("sleep", 0)
        self.set_state("sleep")
        self._controller.on_sleep()

    def wake(self):
        if self.state == "sleep":
            self._controller.on_wake()
        self.follow = False
        self.restore_base_expression()
        self.set_state("idle")

    def _edge_factor(self, x: int, dirn: int) -> float:
        """v2.6：去掉 140px 减速带（用户反馈像一堵看不见的空气墙），不再压速度。

        现在只在真的探出屏幕 12% 时才回头，不再提前刹车。
        """
        return 1.0

    def _edge_over(self) -> int:
        """允许探出屏幕宽度的 12%，避免"贴边就掉头"的撞墙感。"""
        return max(8, int(self.width() * 0.12))

    def set_follow(self, on: bool):
        self.follow = bool(on)
        if on:
            self.set_state("follow")
        elif self.state == "follow":
            self.set_state("idle")

    def trigger_random(self):
        action = random.choice(["jump", "squish", "shake"])
        {"jump": self.do_jump, "squish": self.do_squish, "shake": self.do_shake}[action]()

    def do_jump(self):
        self.set_state("jump")
        self._controller.on_jump()

    def do_squish(self):
        self.set_state("squish")
        self._controller.on_squish()

    def do_shake(self):
        self.set_state("shake")
        self._controller.on_shake()

    # ================= 动作体系 =================
    DEFAULT_ACTION_MS = {"tumble": 2400, "brawl": 2600, "hop": 2200}

    def do_action(self, key: str, duration_ms: int = 0):
        if key not in ALL_ACTIONS:
            return
        if duration_ms <= 0:
            duration_ms = self.DEFAULT_ACTION_MS.get(key, 3000)
        self.follow = False
        self.action_key = key
        rel = ACTIONS.get(key, (None, None))[1]
        if rel:
            self.base = self._load_pix(rel)
            self._update_pix()
        elif key == "eatrice":
            self.set_expression("eat", 0)
        elif key == "tumble":
            self.set_expression("angry", 0)
            self.run_dir = random.choice([-1, 1])
            self.rot = 0.0
        elif key in ("brawl", "hop"):
            self.set_expression("happy", 0)
        self.set_state(key)
        self._controller.on_action(key)
        if duration_ms > 0:
            self._action_timer = QTimer(self)
            self._action_timer.setSingleShot(True)
            self._action_timer.timeout.connect(self.finish_action)
            self._action_timer.start(duration_ms)

    def finish_action(self):
        if self._action_timer is not None:
            self._action_timer.stop()
        self.action_key = ""
        self.finish_state()

    def do_panic(self, duration_ms: int = 2600):
        self.set_expression("angry", 0)
        self.set_state("panic")
        self._controller.on_panic()
        if duration_ms > 0:
            self._action_timer = QTimer(self)
            self._action_timer.setSingleShot(True)
            self._action_timer.timeout.connect(self.finish_action)
            self._action_timer.start(duration_ms)

    # ================= 鼠标事件 =================
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.drag_active = True
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.drag_moved = 0
            self.last_gp = event.globalPosition().toPoint()
            self.vx = self.vy = 0
            if self.state == "sleep":
                self.wake()
            self.set_state("drag")
            event.accept()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self.drag_active and (event.buttons() & Qt.LeftButton):
            gp = event.globalPosition().toPoint()
            delta = gp - self.last_gp
            self.vx, self.vy = delta.x(), delta.y()
            self.last_gp = gp
            self.drag_moved += abs(delta.x()) + abs(delta.y())
            self.move(gp - self.drag_offset)
            self._clamp_to_screen(margin=0)
            self.bubble.update_position()
            event.accept()

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton and self.drag_active:
            self.drag_active = False
            if self.drag_moved < 6:
                self.do_pat()
            else:
                self.finish_state()
            event.accept()

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._controller.open_panel()
            event.accept()

    def wheelEvent(self, event):  # noqa: N802
        delta = event.angleDelta().y()
        if delta != 0:
            self.set_pet_scale(self.scale * (1.1 if delta > 0 else 1 / 1.1))
            event.accept()

    def contextMenuEvent(self, event):  # noqa: N802
        self.show_menu(event.globalPos())
        event.accept()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.bubble.update_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.bubble.update_position()

    # ================= 右键菜单 =================
    def show_menu(self, gpos: QPoint):
        ctl = self._controller
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#ffffff;border:1px solid #d8d8dc;border-radius:8px;"
            "padding:6px;font-family:'Microsoft YaHei';font-size:13px;}"
            "QMenu::item{padding:7px 26px 7px 18px;border-radius:5px;color:#333;}"
            "QMenu::item:selected{background:#4a6cf7;color:#fff;}"
            "QMenu::separator{height:1px;background:#ececf0;margin:5px 8px;}")

        menu.addAction("陪我聊聊天", ctl.open_panel_chat)
        menu.addAction("语音说一句（Ctrl+Alt+V）", ctl.voice_listen)
        menu.addAction("今天天气", ctl.speak_weather)
        menu.addAction("说条科技新闻", ctl.speak_news)
        menu.addAction("换天气城市…", self._pick_weather_city)
        menu.addAction("摸摸头", self.do_pat)

        menu.addAction("表演一个", ctl.perform_random)
        act_menu = menu.addMenu("做个动作")
        for key in ALL_ACTIONS:
            act = act_menu.addAction(action_label(key))
            act.triggered.connect(lambda _=False, k=key: self.do_action(k))

        feed_menu = menu.addMenu("喂点零食")
        for key, snack in ctl.snacks().items():
            act = feed_menu.addAction(f"{snack['emoji']} {snack['name']}（{snack['cost']} 金币）")
            act.triggered.connect(lambda _=False, k=key: self.do_feed(k))
        menu.addSeparator()
        menu.addAction("散步一会儿", self.do_walk)
        menu.addAction("满屏跑一圈", lambda: ctl.begin_run(8000))
        menu.addAction("让她睡觉", self.do_sleep)

        follow_act = QAction("跟随鼠标", self)
        follow_act.setCheckable(True)
        follow_act.setChecked(self.follow)
        follow_act.toggled.connect(self.set_follow)
        menu.addAction(follow_act)

        form_menu = menu.addMenu("形态")
        cur_form = self.current_form()
        for fk, flabel in FORM_LABELS.items():
            act = form_menu.addAction(("✓ " if fk == cur_form else "　") + flabel)
            act.triggered.connect(lambda _=False, f=fk: self.set_form(f))

        skin_menu = menu.addMenu("换装")
        for key, (label, _) in SKINS.items():
            if SKIN_FORM.get(key) != cur_form:
                continue
            act = skin_menu.addAction(label)
            act.triggered.connect(lambda _=False, k=key: self.set_skin(k))

        size_menu = menu.addMenu("大小")
        for label, s in {"小": 0.7, "中": 1.0, "大": 1.35}.items():
            act = size_menu.addAction(label)
            act.triggered.connect(lambda _=False, v=s: self.set_pet_scale(v))

        voice_menu = menu.addMenu("音色")
        cur_prof = str(ctl.config.get("voice_profile", "") or "")
        for key, title in voice_profile_names():
            act = voice_menu.addAction(("✓ " if key == cur_prof else "　") + title)
            act.triggered.connect(lambda _=False, k=key: ctl.set_voice_profile(k))
        act = voice_menu.addAction(("✓ " if (not cur_prof or cur_prof == "off") else "　") + "关（原生音色）")
        act.triggered.connect(lambda _=False: ctl.set_voice_profile("off"))

        top_act = QAction("始终置顶", self)
        top_act.setCheckable(True)
        top_act.setChecked(self.is_topmost())
        top_act.toggled.connect(self.set_topmost)
        menu.addAction(top_act)

        sound_act = QAction("点击音效", self)
        sound_act.setCheckable(True)
        sound_act.setChecked(self._controller.config.get("sound_on", True))
        sound_act.toggled.connect(self._controller.toggle_sound)
        menu.addAction(sound_act)

        chatter_act = QAction("碎碎念", self)
        chatter_act.setCheckable(True)
        chatter_act.setChecked(self._controller.config.get("chatter_on", True))
        chatter_act.toggled.connect(self._controller.toggle_chatter)
        menu.addAction(chatter_act)

        menu.addSeparator()
        # v2.9.2 打开控制面板/隐藏桌宠/退出 已合并到任务栏图标右键菜单，这里不再重复
        menu.exec(gpos)

    def _pick_weather_city(self):
        cur = self._controller.config.get("weather_city", "郑州")
        city, ok = QInputDialog.getText(self, "天气城市", "城市名（中文或拼音都行）：", text=str(cur))
        if ok and city.strip():
            self._controller.set_weather_city(city.strip())
            self._controller.pet.bubble.show_text(f"记住了，以后报「{city.strip()}」的天气。", 2600)

    # ================= 位置持久化 =================
    def _load_position(self):
        cfg = self._controller.config
        try:
            self.move(int(cfg["x"]), int(cfg["y"]))
            self._topmost = bool(cfg.get("topmost", True))
            self.setWindowFlag(Qt.WindowStaysOnTopHint, self._topmost)
        except (KeyError, TypeError, ValueError):
            scr = QGuiApplication.primaryScreen().availableGeometry()
            self.move(scr.right() - self.width() - 120, scr.bottom() - self.height() + self._pad - 60)

    def _default_pos(self):
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.right() - self.width() - 120, scr.bottom() - self.height() + self._pad - 60)

    def _clamp_to_screen(self, margin: int = 0):
        scr = QGuiApplication.primaryScreen().availableGeometry()
        # v2.9.4：原先把 _pad 加到右边界，双屏时窗口能被推出主屏（人跑到副屏，主屏倒像"凭空消失"）。
        # 现在保证窗口至少 65% 留在主屏内，既保留探边的自然感，也不会整只跑出画面。
        keep = max(24, int(self.width() * 0.65))
        x = max(scr.left() - (self.width() - keep) - margin,
                min(self.x(), scr.right() - keep + margin))
        y = max(scr.top() - self._pad, min(self.y(), scr.bottom() - self.height() + self._pad))
        self.move(x, y)

    def save_position(self):
        self._controller.config["x"] = self.x()
        self._controller.config["y"] = self.y()

    # ================= 绘制 =================
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.alpha < 1.0:
            p.setOpacity(self.alpha)
        w, h = self.width(), self.height()
        pw, ph = self._pix.width(), self._pix.height()
        p.translate(w / 2.0, h - self._pad + self.bob)
        if self.mirror:
            p.scale(-1.0, 1.0)
        p.rotate(self.rot)
        p.scale(self.sx, self.sy)
        if self.gait_on and self._leg is not None:
            self._paint_gait(p, pw, ph)
        else:
            p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), self._pix)

    def _paint_gait(self, p: QPainter, pw: int, ph: int):
        """条带弯曲步态（strip warp）。

        硬切图会在腰上留一条横缝（实测很难看），这里改成按 8px 一条横带逐条
        绘制，相邻条带共享边缘，所以永远不会露出断口；偏移从髋部为 0 逐渐
        放大到脚部最大，形成"腿在摆、上身反向配平"的连续弯曲。
        """
        strip = 8
        amp = 0.030 * ph                       # 脚部最大横移（691 高约 21px）
        hip = self._hip_y or int(ph * HIP_RATIO)
        g2 = self.gait * 2 * math.pi
        for y in range(0, ph, strip):
            hh = min(strip, ph - y)
            if y + hh <= hip:
                # 上半身：头顶反向小幅摆，越靠头越大，髋部归零
                u_up = 1.0 - (y + hh) / max(1, hip)
                dx = -0.35 * amp * u_up * math.sin(g2)
                dy = 0.0
            else:
                # 下半身：髋部 0 → 脚底最大，相位略微滞后（波浪感）
                u = ((y + hh) - hip) / max(1, ph - hip)
                dx = amp * (u ** 1.3) * math.sin(g2 - u * 1.1)
                dy = -0.004 * ph * (u ** 2) * abs(math.cos(g2))
            # 目标矩形比源多 1px：相邻条带重叠，避免取整后在身上留下横向细缝
            sh = min(hh + 1, ph - y)
            p.drawPixmap(QRect(int(-pw // 2 + dx), int(-ph + y + dy), pw, sh),
                         self._pix, QRect(0, y, pw, sh))
