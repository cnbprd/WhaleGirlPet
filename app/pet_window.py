# -*- coding: utf-8 -*-
"""桌宠主窗口：透明无边框置顶，拖拽 / 单击摸头 / 双击面板 / 右键菜单 / 滚轮缩放 / 状态机动画。"""
import math
import os
import random
import time

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import (QAction, QColor, QCursor, QGuiApplication, QImage, QPainter,
                           QPainterPath, QPen, QPixmap, QRegion, qAlpha)
from PySide6.QtWidgets import QInputDialog, QMenu, QWidget

from paths import (ACTIONS, EXPRESSIONS, FORM_DEFAULT_SKIN, FORM_LABELS, FORM_SKINS,
                   SKINS, SKIN_FORM, asset_path)
import anim_engine as anim
import rig as rig_mod
import skeletal as sk_mod
from bubble import BubbleWindow
from voice_profile import profile_names as voice_profile_names


def supersampled(src, bw: int, bh: int, factor: int = 2):
    """2 倍超采样缩放：先放大 2 倍再压回目标尺寸，让 alpha 边缘有中间值。

    直接把 267×512 的立绘画到 1.5~2 倍大小时，Qt 的平滑缩放只做一次采样，
    半透明边缘会出现 1px 台阶；先上采样再下采样等于对 alpha 做了一次平均。
    """
    f = max(2, int(factor))
    mid = src.scaled(max(1, bw * f), max(1, bh * f),
                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return mid.scaled(bw, bh, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def jelly_scale(age: float, dur: float = 0.55, amp: float = 0.06, freq: float = 3.2):
    """形态/换装切换的果冻回弹：阻尼正弦，横向拉伸同时纵向压扁（体积近似不变）。

    age 秒：0 → (1,1)；峰值约 ±amp；dur 之后恒为 (1,1)。
    """
    if age is None or age < 0 or age >= dur:
        return (1.0, 1.0)
    k = 1.0 - age / dur
    osc = math.sin(age * 2 * math.pi * freq)
    j = amp * k * osc
    return (1.0 + j, 1.0 - j)

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

# v3.0.0 打工专用动作：每个工种一套持续表演，任务开始到结束一直在做，
# 不再是「播 4.2 秒 → 回 idle」，并配一个手边道具（书 / 扫帚 / 抹布 / 箱子）。
TASK_STATES = ("work_study", "work_rest", "work_clean", "work_wipe", "work_chores")


def action_label(key: str) -> str:
    return ACTIONS.get(key, (CODE_ACTION_LABELS.get(key, key),))[0]


class PetWindow(QWidget):
    def __init__(self, controller, show_now: bool = True):
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
        # v3.0.22 果冻回弹：切形态/换装时给一个短促的挤压-拉伸，抵消「硬切」感
        self._jelly_t0 = None
        self._jelly_dur = 0.55
        self._jelly_amp = 0.06

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

        # v3.0.21：按机器能力选渲染档 + 帧间隔（无独显/远程桌面自动降档）
        try:
            import perf as perf_mod
            cfgq = self._controller.config.get("render_quality", "auto")
            self.render_quality = perf_mod.resolve_quality(cfgq)
            self.frame_ms = perf_mod.frame_ms_for(
                self.render_quality, self._controller.config.get("frame_ms", 0))
        except Exception:  # noqa: BLE001
            self.render_quality = "high"
            self.frame_ms = FRAME_MS
        self.anim = QTimer(self)
        self.anim.setInterval(self.frame_ms)
        self.anim.timeout.connect(self._tick)
        self.anim.start()
        # v3.0.11：关键帧时间轴（档 A）—— 八个代码动作改由轨道 + 缓动演出，
        # config["anim_timeline"] 关掉就退回原来的手写公式。
        self.tl = anim.Timeline()
        # v3.0.12：档 B 网格蒙皮骨骼（腿部真屈膝），config["rig_mesh"] 可关
        self._rig = None
        self._rig_key = None
        # v3.0.13：游戏引擎式骨骼（骨架+蒙皮+动作剪辑），优先于 rig 单段方案
        self._skel = None
        self._skel_key = None

        self.bubble = BubbleWindow(self)

        self._update_pix()
        self._load_position()
        self._clamp_to_screen()
        # v2.9.5：启动屏需要先盖住这一帧，等 Controller 初始化完再 show_pet()
        if show_now:
            self.show()

    # ================= 素材 =================
    def _load_pix(self, rel: str) -> QPixmap:
        """放大超过 1.2 倍时优先用 `@2x` 超采样版本（离线 Lanczos 生成）。

        实测：直接放大 267×512，alpha 过渡只有 ~4px；用 2× 源压回来是 ~8.8px，
        斜边台阶肉眼可见地消失。找不到 @2x 就退回原图，不影响功能。
        """
        scale = float(getattr(self, "scale", 1.0))
        two = scale > 1.2 and os.path.exists(asset_path(rel[:-4] + "@2x.png"))
        key = (rel, "2x" if two else "1x")
        if key not in self.pix_cache:
            path = asset_path(rel[:-4] + "@2x.png") if two else asset_path(rel)
            self.pix_cache[key] = QPixmap(path)
        self.base_is_2x = two
        return self.pix_cache[key]

    def _load_skin(self, skin_key: str) -> QPixmap:
        rel = SKINS.get(skin_key, SKINS["default"])[1]
        return self._load_pix(rel)

    def set_skin(self, skin_key: str):
        self._controller.config["skin"] = skin_key
        self.base = self._load_skin(skin_key)
        self.restore_base_expression()
        self._update_pix()
        self._jelly_t0 = time.monotonic()

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
        self._jelly_t0 = time.monotonic()
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

    def _update_pix(self, base=None):
        base = base if base is not None else self.base
        # v2.8 脚底对齐：裁掉底部透明边，窗口底边即脚底，换皮肤不再上下漂
        if self._controller.config.get("anchor_crop", True):
            foot = self._foot_row(base)
            if 0 < foot < base.height():
                base = base.copy(0, 0, base.width(), foot)
        bw = max(1, int(base.width() * self.scale / (2 if getattr(self, "base_is_2x", False) else 1)))
        bh = max(1, int(base.height() * self.scale / (2 if getattr(self, "base_is_2x", False) else 1)))
        # v3.0.22：放大超过 1.2 倍时走 2 倍超采样源，消除 alpha 边缘台阶（可关）
        if (self.scale > 1.2 and not getattr(self, "base_is_2x", False)
                and bool(self._controller.config.get("alpha_supersample", True))):
            self._pix = supersampled(base, bw, bh, 2)
        else:
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
        # 切到不属于时间轴的状态时，把正在播的 clip 停掉（否则姿态会被旧 clip 拖着）
        if getattr(self, "tl", None) is not None and st not in anim.TIMELINE_STATES:
            self.tl.stop()
        if st == "jump":
            self.jump_x0 = self.x()
            self.jump_y0 = self.y()

    def finish_state(self):
        if self._run_timer is not None:
            self._run_timer.stop()
        if self._action_timer is not None:
            self._action_timer.stop()
        if getattr(self, "tl", None) is not None:
            self.tl.stop()
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
        self.state_t += self.frame_ms / 1000.0
        st = self.state
        if self.tl.playing:
            self.tl.step(self.frame_ms / 1000.0)

        # 步态相位：走路 1 循环/秒，奔跑 1.8 倍速、摆幅更大
        self.gait_on = st in GAIT_STATES
        if self.gait_on:
            self.gait_amp = 11.0 if st == "run" else 6.0
            step = (self.frame_ms / 1000.0) * (1.8 if st == "run" else 1.0)
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
            # v3.0.23：起伏跟步态同相位（一步一沉），别和抬脚节奏打架
            self.bob = -3.5 * abs(math.sin(self.gait * 2 * math.pi)) * self.scale
            # 步态已经在弯身体了，整图旋转要收着，否则像在"摇"
            self.rot = 1.2 * math.sin(self.gait * 2 * math.pi)
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
            # v2.9.9：站着打盹不像睡。改成"蹲坐抱膝、身子压扁下沉、头慢慢歪倒"，
            # 呼吸做成 5 秒一轮的起伏，换装形态下没有闭眼差分包，靠姿态也能看出睡了。
            breath = 0.5 + 0.5 * math.sin(self.state_t * 0.55)   # 0~1，约 11 秒一轮
            self.alpha = 0.68
            self.sy = 0.72 + 0.045 * breath                      # 上限 0.765，永远低于站姿
            self.sx = 1.06 - 0.025 * breath                      # 压扁同时略变宽，像缩成一团
            self.bob = -(1.0 + 3.2 * breath) * self.scale        # 贴地，只随呼吸轻微上浮
            self.rot = 8 * math.sin(self.state_t * 0.35)         # 约 18 秒慢慢歪一次头

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

        # ---------- 打工专用动作（v3.0.0）：每个工种一直做，配道具 ----------
        elif st == "work_study":
            # 听课看书：身体前倾，按阅读节奏点头
            self.rot = 4.5 + 2.0 * math.sin(self.state_t * 1.8)
            self.bob = -1.2 * abs(math.sin(self.state_t * 3.6)) * self.scale
            self.sy = 1 - 0.006 * abs(math.sin(self.state_t * 3.6))

        elif st == "work_rest":
            # 摸鱼休息：靠在那儿慢悠悠晃
            self.rot = 3.5 * math.sin(self.state_t * 1.1)
            self.bob = -3.5 * abs(math.sin(self.state_t * 1.3)) * self.scale

        elif st == "work_clean":
            # 清理垃圾：左右大幅摆手，扫帚跟着扫
            swing = math.sin(self.state_t * 5.0)
            self.rot = 8 * swing
            self.bob = -2.0 * abs(math.sin(self.state_t * 10.0)) * self.scale
            self.mirror = swing < 0

        elif st == "work_wipe":
            # 擦桌面：小幅高频画圈，肩膀跟着动
            self.rot = 4 * math.sin(self.state_t * 4.0)
            self.bob = -2.2 * abs(math.sin(self.state_t * 16.0)) * self.scale
            self.sx = 1 + 0.012 * math.sin(self.state_t * 8.0)

        elif st == "work_chores":
            # 做家务：抱着箱子一趟一趟往前挪
            v = 1.6 * self.scale
            scr = QGuiApplication.primaryScreen().availableGeometry()
            over = self._edge_over()
            x = self.x() + int(self.run_dir * v)
            if x <= scr.left() - over:
                self.run_dir = 1
            elif x + self.width() >= scr.right() + over:
                self.run_dir = -1
            self.mirror = self.run_dir < 0
            self.move(x, self.y())
            self.bob = -7 * abs(math.sin(self.state_t * 3.2)) * self.scale
            self.rot = 3 * math.sin(self.state_t * 3.2)

        elif st == "look":
            self.rot = 8 * math.sin(self.state_t * 2.5)
            self.mirror = math.sin(self.state_t * 2.5) > 0

        elif st == "panic":
            self.rot = 12 * math.sin(self.state_t * 30)
            self.bob = -2 * abs(math.sin(self.state_t * 30)) * self.scale
            self.sy = 1 - 0.04 * abs(math.sin(self.state_t * 30))

        # v3.0.11：时间轴姿态覆盖（放在所有分支之后，引擎优先）
        if self.tl.playing and self.tl.covers(st):
            pose = self.tl.pose_now()
            if pose is not None:
                self.bob = pose.bob * self.scale
                self.rot = pose.rot
                if pose.sx is not None:
                    self.sx = pose.sx
                if pose.sy is not None:
                    self.sy = pose.sy
                if pose.alpha is not None:
                    self.alpha = pose.alpha
                if pose.flip is not None:
                    self.mirror = bool(round(pose.flip))
            for ev in self.tl.pop_events():
                self._on_anim_event(ev)

        self.update()

    def _on_anim_event(self, name: str):
        """时间轴事件点（落脚 / 恢复）：现在用来配脚步音和落地的一顿。"""
        if name == "land":
            try:
                self._controller.audio.play("step", priority=1)
            except Exception:  # noqa: BLE001
                pass
            self.bob += 1.5 * self.scale

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

    def _sleep_rel(self) -> str:
        """v3.0.22：各皮肤都有 `<名>_sleep.png`（闭眼差分），找不到就靠姿态装睡。"""
        skin = self._controller.config.get("skin", "default")
        rel = SKINS.get(skin, SKINS["default"])[1]
        cand = rel[:-4] + "_sleep.png"
        return cand if os.path.exists(asset_path(cand)) else ""

    def _set_sleep_face(self, on: bool):
        if on:
            rel = self._sleep_rel()
            if not rel:
                return False
            self._update_pix(base=self._load_pix(rel))
            return True
        self.base = self._load_skin(self._controller.config.get("skin", "default"))
        self._update_pix()
        return True

    def do_sleep(self):
        self.follow = False
        # v2.9.8：先收掉正在播的动作，别让动作帧盖在睡眠姿态上
        if getattr(self, "_action_timer", None) is not None:
            self._action_timer.stop()
        self._action_timer = None
        self.action_key = ""
        # v3.0.22：优先换闭眼差分；默认装仍走表情（兼容旧素材逻辑）
        if not self._set_sleep_face(True):
            if self._controller.config.get("skin", "default") == "default":
                self.set_expression("sleep", 0)
        self.set_state("sleep")
        self._controller.on_sleep()

    def wake(self):
        if self.state == "sleep":
            self._controller.on_wake()
        self.follow = False
        self._set_sleep_face(False)
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

    def do_action(self, key: str, duration_ms: int = 0, then: str = "", mix: float = 0.30):
        """播动作。v3.0.21：`mix` 是切过去的淡入时长（秒），`then` 是接着排队的下一个动作。

        0.30s 是实测出来的：0.15s 只能压住位置（速度突变仍 10.30px/帧），
        0.30s 配合 Hermite 才把速度突变压到 1.14px/帧（硬切 15.20）。
        """
        if key not in ALL_ACTIONS:
            return
        if duration_ms <= 0:
            duration_ms = self.DEFAULT_ACTION_MS.get(key, 3000)
        self.follow = False
        self.action_key = key
        skin_now = self._controller.config.get("skin", "default")
        rel = ACTIONS.get(key, (None, None))[1]
        # v2.9.8：动作帧只有默认女仆装那一套。换装或萝莉形态下套动作帧，
        # 人物会瞬间变回女仆装（用户反馈「做动作怎么换衣服了」），
        # 所以只在默认皮肤用帧，其他皮肤保持当前立绘，靠 _tick 里的程序化动作表演。
        use_sprite = bool(rel) and skin_now == "default" and self.current_form() != "loli"
        if use_sprite:
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
        # v3.0.11：八个代码动作交给时间轴引擎演出（config 可关，退回旧公式）
        # v3.0.20：切动作默认给 0.15s 交叉淡入；`then` 交给引擎排队，动作之间不再硬切
        try:
            if key in anim.CLIPS and self._controller.config.get("anim_timeline", True):
                self.tl.play(key, mix=mix)
                if then and then in anim.CLIPS:
                    self.tl.queue(then)
            else:
                self.tl.stop()
        except Exception:  # noqa: BLE001
            pass
        self._controller.on_action(key)
        if duration_ms > 0:
            self._action_timer = QTimer(self)
            self._action_timer.setSingleShot(True)
            self._action_timer.timeout.connect(self.finish_action)
            self._action_timer.start(duration_ms)

    def do_task_work(self, state: str):
        """打工动作入口：进专用状态并一直表演到任务结束（不设自动收回计时器）。

        v3.0.0：原来任务里调 do_action(..., 4200)，4.2 秒后自动回 idle，
        中间 6 秒空档看上去就是「点开始没反应」；改成整套动作做到完工。
        """
        if state not in TASK_STATES:
            return
        self.follow = False
        if getattr(self, "_action_timer", None) is not None:
            self._action_timer.stop()
        self._action_timer = None
        self.action_key = ""
        self.set_expression("curious", 0)
        self.set_state(state)

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

        # v3.0.0：原「陪我聊聊天」已合并到「设置 → 聊天」页，右键菜单不再单独占一项
        menu.addAction("摸摸头", self.do_pat)

        menu.addAction("表演一个", ctl.perform_random)
        # v2.9.7：动作清单与喂零食不再摆菜单（动作她自己随机来；饿了会自己讨）
        menu.addAction("打开背包", ctl.open_backpack)
        menu.addAction("零食商城", ctl.open_shop)
        menu.addAction("去打工", ctl.offer_work)

        menu.addSeparator()
        menu.addAction("散步一会儿", self.do_walk)
        menu.addAction("满屏跑一圈", lambda: ctl.begin_run(8000))
        menu.addAction("让她睡觉", self.do_sleep)
        menu.addSeparator()
        # v2.9.7：跟随 / 形态 / 换装 / 大小 / 音色 / 置顶 / 碎碎念 统一收进「设置 → 桌宠行为」
        menu.addAction("设置…", ctl.open_settings_page)

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
        if self._jelly_t0 is not None:
            age = time.monotonic() - self._jelly_t0
            jx, jy = jelly_scale(age, self._jelly_dur, self._jelly_amp)
            if jx != 1.0 or jy != 1.0:
                p.scale(jx, jy)
            else:
                self._jelly_t0 = None
        p.scale(self.sx, self.sy)
        if (self.state in ("walk", "run")
                and self._controller.config.get("skeletal", True)):
            self._paint_skeletal(p, pw, ph)
        elif (self.gait_on and self.state in ("walk", "run", "trot")
                and self._controller.config.get("rig_mesh", True)):
            self._paint_rig(p, pw, ph)
        elif self.gait_on and self._leg is not None:
            self._paint_gait(p, pw, ph)
        else:
            p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), self._pix)
        if self.state in TASK_STATES:
            self._paint_work_prop(p, pw, ph)

    def _paint_work_prop(self, p: QPainter, pw: int, ph: int):
        """任务道具：书 / 扫帚 / 抹布 / 箱子 / 泡泡，纯代码绘制，不新增素材。"""
        st = self.state
        t = self.state_t
        s = self.scale
        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)

        if st == "work_study":
            # 书：捧在胸前，微微倾斜，像在低头看
            bw = max(24.0, pw * 0.32)
            bh = bw * 0.70
            p.save()
            p.translate(pw * 0.05, -ph * 0.58)
            p.rotate(-6)
            p.setBrush(QColor(240, 244, 250, 242))
            p.drawRoundedRect(QRectF(-bw / 2, -bh / 2, bw, bh), 3 * s, 3 * s)
            p.setBrush(QColor(72, 112, 182, 240))
            p.drawRect(QRectF(-bw / 2, -bh / 2, bw, bh * 0.14))
            p.setPen(QPen(QColor(148, 160, 182, 190), max(1.0, 1.1 * s)))
            for i in range(3):
                yy = -bh * 0.18 + i * bh * 0.16
                p.drawLine(QPointF(-bw * 0.36, yy), QPointF(bw * 0.36, yy))
            p.restore()
        elif st == "work_clean":
            # 扫帚：握在右手，帚头朝下，随摆手左右扫
            swing = math.sin(t * 5.0)
            hx = pw * 0.20 + swing * pw * 0.05
            hy = -ph * 0.60
            tx = hx + pw * 0.10 + swing * pw * 0.06
            ty = -ph * 0.16
            p.setPen(QPen(QColor(168, 124, 72, 240), max(2.0, 2.8 * s)))
            p.drawLine(QPointF(hx, hy), QPointF(tx, ty))
            p.setPen(Qt.NoPen)
            path = QPainterPath()
            path.moveTo(tx - pw * 0.05, ty)
            path.lineTo(tx + pw * 0.05, ty)
            path.lineTo(tx + pw * 0.13, ty + ph * 0.10)
            path.lineTo(tx - pw * 0.13, ty + ph * 0.10)
            path.closeSubpath()
            p.setBrush(QColor(226, 190, 128, 240))
            p.drawPath(path)
            p.setBrush(QColor(198, 160, 96, 245))
            p.drawRoundedRect(QRectF(tx - pw * 0.12, ty + ph * 0.075, pw * 0.24, ph * 0.035),
                              2 * s, 2 * s)
        elif st == "work_wipe":
            # 抹布：在腰前偏右画小圈
            cx = pw * 0.14 + math.cos(t * 4.0) * pw * 0.09
            cy = -ph * 0.46 + math.sin(t * 8.0) * ph * 0.02
            p.setBrush(QColor(120, 200, 232, 230))
            p.drawRoundedRect(QRectF(cx - pw * 0.08, cy - ph * 0.03, pw * 0.16, ph * 0.06),
                              4 * s, 4 * s)
            p.setBrush(QColor(255, 255, 255, 80))
            p.drawRoundedRect(QRectF(cx - pw * 0.08, cy - ph * 0.03, pw * 0.055, ph * 0.06),
                              4 * s, 4 * s)
        elif st == "work_chores":
            # 箱子：抱在肚子前面，带顶面和胶带，不像一块扁板
            bw = pw * 0.36
            bh = ph * 0.10
            bx = -bw * 0.5
            by = -ph * 0.52
            p.setBrush(QColor(206, 158, 96, 245))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 3 * s, 3 * s)
            p.setBrush(QColor(228, 186, 128, 245))
            p.drawRect(QRectF(bx, by, bw, bh * 0.18))
            p.setBrush(QColor(238, 214, 164, 235))
            p.drawRect(QRectF(bx + bw * 0.46, by, bw * 0.08, bh))
            p.drawRect(QRectF(bx, by + bh * 0.44, bw, bh * 0.12))
        elif st == "work_rest":
            # 休息：头顶偏右飘泡泡
            for i in range(3):
                u = (t * 0.6 + i / 3.0) % 1.0
                r = pw * (0.028 + 0.02 * u)
                cx = pw * 0.18 + math.sin(t * 1.2 + i) * pw * 0.04
                cy = -ph * 0.78 - u * ph * 0.16
                aa = int(120 * (1.0 - u))
                p.setBrush(QColor(180, 220, 255, aa))
                p.drawEllipse(QPointF(cx, cy), r, r)
        p.restore()

    def _skel_for(self):
        """按当前立绘懒建骨骼精灵（换皮肤/表情/形态时重建）。"""
        pix = self._pix
        if pix.isNull() or pix.width() < 8 or pix.height() < 8:
            return None
        key = (pix.cacheKey(), pix.width(), pix.height(),
               getattr(self, "render_quality", "high"))
        if self._skel is None or self._skel_key != key:
            self._skel = sk_mod.SkeletalSprite(pix, getattr(self, "render_quality", "high"))
            self._skel_key = key
        return self._skel

    def _paint_skeletal(self, p: QPainter, pw: int, ph: int):
        """游戏引擎式动画：骨架 + 蒙皮 + 动作剪辑（walk / run）。"""
        sprite = self._skel_for()
        if sprite is None:
            p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), self._pix)
            return
        name = "run" if self.state == "run" else "walk"
        clip = sk_mod.CLIPS[name]
        t = (self.state_t % clip.duration) if clip.loop else min(self.state_t, clip.duration)
        pose = clip.pose(t)
        offsets = None
        if name == "walk":
            # v3.0.23（第 11 条）：正面立绘不能靠大腿大幅左右摆来"走"（会像腿被拧变形）。
            # 改成左右腿交替上提 + 身体上下起伏 + 小角度屈膝，读起来才是迈步。
            phase = self.gait * 2 * math.pi
            lift = ph * 0.011
            l = max(0.0, math.sin(phase))
            r = max(0.0, -math.sin(phase))
            offsets = {"thigh_l": (0.0, -lift * l),
                       "thigh_r": (0.0, -lift * r)}
        frame = sprite.render(pose, offsets)
        p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), frame)

    def _rig_for(self):
        """按当前立绘懒建 Rig（换皮肤/表情/形态时重建）。"""
        pix = self._pix
        if pix.isNull() or pix.width() < 8 or pix.height() < 8:
            return None
        key = (pix.cacheKey(), pix.width(), pix.height())
        if self._rig is None or self._rig_key != key:
            self._rig = rig_mod.Rig(pix)
            self._rig_key = key
        return self._rig

    def _paint_rig(self, p: QPainter, pw: int, ph: int):
        """档 B：网格蒙皮骨骼走路——两条腿真的绕髋/膝转，不是整段横移。"""
        rig = self._rig_for()
        if rig is None:
            p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), self._pix)
            return
        st = self.state
        phase = self.gait * 2 * math.pi
        if st == "run":
            ang = rig_mod.Rig.walk_angles(phase, amp_thigh=15.0, amp_shin=34.0)
        elif st == "trot":
            ang = rig_mod.Rig.walk_angles(phase, amp_thigh=12.0, amp_shin=26.0)
        else:
            ang = rig_mod.Rig.walk_angles(phase, amp_thigh=3.0, amp_shin=12.0)
        frame = rig.frame(*ang)
        p.drawPixmap(QRect(-pw // 2, -ph, pw, ph), frame)

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
