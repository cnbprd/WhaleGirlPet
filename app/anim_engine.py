# -*- coding: utf-8 -*-
"""关键帧时间轴动画引擎（v3.0.11 · 档 A）

设计目标：把「动作 = 一段手写 if/else 公式」变成「动作 = 轨道 × 关键帧 × 缓动曲线」，
让每个动作的加减速、落地压缩、回弹都能单独调，不用改状态机代码。

- 一条轨道（Track）= 一个通道（bob/rot/sx/sy/alpha/dx/dy/flip）的关键帧序列
- 关键帧 = (时间秒, 数值, 到达该帧所用的缓动)
- 一个动作（Clip）= 若干轨道 + 时长 + 是否循环 + 事件点（落脚/腾空等）
- 播放器（Timeline）= 推进时间、按通道求值、吐出 Pose、把事件排队交给调用方

只用标准库，不引入第三方依赖；后续要加动作，往 CLIPS 里加一条即可。
"""
import math

# ---------------- 缓动 ----------------
def linear(t: float) -> float:
    return t


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_sine(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def ease_out_back(t: float) -> float:
    s = 1.70158
    return 1.0 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def ease_out_bounce(t: float) -> float:
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def ease_out_elastic(t: float) -> float:
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    c4 = (2 * math.pi) / 3
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


EASINGS = {
    "linear": linear,
    "in": ease_in_quad,
    "out": ease_out_quad,
    "sine": ease_in_out_sine,
    "back": ease_out_back,
    "bounce": ease_out_bounce,
    "elastic": ease_out_elastic,
}

CHANNELS = ("bob", "rot", "sx", "sy", "alpha", "dx", "dy", "flip")
DEFAULT_VALUES = {"bob": 0.0, "rot": 0.0, "sx": 1.0, "sy": 1.0,
                  "alpha": 1.0, "dx": 0.0, "dy": 0.0, "flip": None}


class Track:
    """一条通道的关键帧：keys = [(t, value, ease), ...]，ease 描述"从上一帧到这一帧"。"""

    __slots__ = ("keys", "default")

    def __init__(self, keys, default=0.0):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.default = default

    def value(self, t: float) -> float:
        if not self.keys:
            return self.default
        if t <= self.keys[0][0]:
            return self.keys[0][1]
        for i in range(1, len(self.keys)):
            t1, v1, e = self.keys[i]
            t0, v0, _ = self.keys[i - 1]
            if t <= t1:
                if t1 <= t0:
                    return v1
                u = (t - t0) / (t1 - t0)
                fn = EASINGS.get(e or "linear", linear)
                return v0 + (v1 - v0) * fn(u)
        return self.keys[-1][1]


class Pose:
    """某一时刻的完整姿态。flip 为 None 表示本帧不改朝向。"""

    __slots__ = CHANNELS

    def __init__(self, values: dict):
        for ch in CHANNELS:
            setattr(self, ch, values.get(ch))

    def __repr__(self):
        return (f"Pose(bob={self.bob:.1f}, rot={self.rot:.1f}, "
                f"sx={self.sx:.3f}, sy={self.sy:.3f}, alpha={self.alpha:.2f}, flip={self.flip})")


class Clip:
    """一个动作：轨道 + 时长 + 循环 + 事件点。"""

    __slots__ = ("name", "duration", "loop", "tracks", "events", "states", "label")

    def __init__(self, name, duration, tracks: dict, loop=False,
                 events=None, states=None, label=""):
        self.name = name
        self.duration = float(duration)
        self.loop = bool(loop)
        self.tracks = {ch: Track(k, 0.0 if ch != "flip" else 0.0)
                       for ch, k in (tracks or {}).items() if ch in CHANNELS}
        self.events = sorted(events or [], key=lambda x: x[0])
        self.states = states or [name]
        self.label = label or name

    def pose(self, t: float) -> Pose:
        values = {}
        for ch in CHANNELS:
            tr = self.tracks.get(ch)
            if tr is not None:
                values[ch] = tr.value(t)
            else:
                # 没有 flip 轨道时保持 None：表示"本动作不改朝向"，别把镜像强行清掉
                values[ch] = None if ch == "flip" else DEFAULT_VALUES[ch]
        return Pose(values)

    def done(self, t: float) -> bool:
        return (not self.loop) and t >= self.duration


class Timeline:
    """播放器：一次放一个动作；step() 推进时间并累计事件。"""

    def __init__(self):
        self.clip = None
        self.t = 0.0
        self.playing = False
        self._events = []
        # 已触发过的事件（不随 pop 清空，避免同一事件每帧重复触发）
        self._fired = set()

    # ---- 控制 ----
    def play(self, clip) -> None:
        if isinstance(clip, str):
            clip = CLIPS.get(clip)
        if clip is None:
            return
        self.clip = clip
        self.t = 0.0
        self.playing = True
        self._events = []
        self._fired = set()

    def stop(self) -> None:
        self.clip = None
        self.t = 0.0
        self.playing = False
        self._events = []
        self._fired = set()

    # ---- 查询 ----
    def covers(self, state: str) -> bool:
        return bool(self.playing and self.clip and state in self.clip.states)

    def progress(self) -> float:
        if not self.clip or self.clip.duration <= 0:
            return 0.0
        p = self.t / self.clip.duration
        return p - math.floor(p) if self.clip.loop else min(p, 1.0)

    # ---- 推进 ----
    def step(self, dt: float) -> Pose | None:
        if not self.playing or self.clip is None:
            return None
        self.t += dt
        clip = self.clip
        # 循环动作：时间回卷，已触发集合一并清空（下一轮该再响一次）
        if clip.loop and clip.duration > 0:
            new_t = self.t % clip.duration
            if new_t < self.t:
                self._fired = set()
            self.t = new_t
        for (et, name) in clip.events:
            if et <= self.t and (et, name) not in self._fired:
                self._fired.add((et, name))
                self._events.append((et, name))
        if (not clip.loop) and self.t >= clip.duration:
            # 单次动作播完后停在末帧，由状态机负责收尾
            self.t = clip.duration
        return clip.pose(self.t)

    def pose_now(self) -> Pose | None:
        return self.clip.pose(self.t) if self.clip else None

    def pop_events(self) -> list:
        out = [name for _, name in self._events]
        self._events = []
        return out


# ---------------- 动作库（8 个代码动作迁到时间轴） ----------------
CLIPS = {}


def _add(clip: Clip):
    CLIPS[clip.name] = clip
    return clip


# 螃蟹步：横向挪，身子一跳一跳、左右歪
_add(Clip("crab", 0.628, loop=True, label="螃蟹步", tracks={
    "bob": [(0, 0, "linear"), (0.157, -3, "out"), (0.314, 0, "in"),
            (0.471, -3, "out"), (0.628, 0, "in")],
    "rot": [(0, 0, "sine"), (0.157, 4, "sine"), (0.471, -4, "sine"), (0.628, 0, "sine")],
}))

# 漂浮踏步：慢升慢降，像踩在棉花上
_add(Clip("floatstep", 2.094, loop=True, label="漂浮踏步", tracks={
    "bob": [(0, 0, "sine"), (0.523, -8, "sine"), (1.047, 0, "sine"),
            (1.57, -8, "sine"), (2.094, 0, "sine")],
    "rot": [(0, 0, "sine"), (0.523, 3, "sine"), (1.57, -3, "sine"), (2.094, 0, "sine")],
}))

# 小跑：快起快落，身体随步子前倾
_add(Clip("trot", 0.628, loop=True, label="小跑", tracks={
    "bob": [(0, 0, "linear"), (0.157, -5, "out"), (0.314, 0, "in"),
            (0.471, -5, "out"), (0.628, 0, "in")],
    "rot": [(0, 0, "sine"), (0.157, 5, "sine"), (0.471, -5, "sine"), (0.628, 0, "sine")],
}))

# 左右看：头先右歪、再看左，间隔有停顿（flip 通道控制朝向）
_add(Clip("look", 2.4, loop=True, label="左右看", tracks={
    "flip": [(0, 1, "linear"), (1.0, 1, "linear"), (1.06, 0, "linear"),
             (2.2, 0, "linear"), (2.26, 1, "linear"), (2.4, 1, "linear")],
    "rot": [(0, 0, "sine"), (0.5, 3, "sine"), (1.06, 3, "sine"),
            (1.7, -3, "sine"), (2.26, -3, "sine"), (2.4, 0, "sine")],
}))

# 吃白饭：低头一口一口，身体轻微前倾
_add(Clip("eatrice", 1.2, loop=True, label="吃白饭", tracks={
    "rot": [(0, 4, "linear"), (0.4, 7.5, "out"), (0.8, 4, "in"), (1.2, 4, "linear")],
    "sy": [(0, 1, "linear"), (0.4, 0.985, "out"), (0.8, 1, "back"), (1.2, 1, "linear")],
    "bob": [(0, 0, "linear"), (0.4, -1.5, "out"), (0.8, 0, "in"), (1.2, 0, "linear")],
}))

# 摔一跤：失衡前扑 → 侧滑腾空 → 落地压扁回弹 → 爬起抖两下
_add(Clip("tumble", 2.2, label="摔一跤", tracks={
    "rot": [(0, 0, "in"), (0.32, 16, "linear"), (0.6, 22, "sine"), (0.92, 16, "sine"),
            (1.45, 0, "out"), (1.75, 4, "sine"), (1.95, -3, "sine"), (2.2, 0, "sine")],
    "bob": [(0, 0, "in"), (0.32, -6, "linear"), (0.6, -26, "sine"), (0.92, 0, "in"),
            (2.2, 0, "linear")],
    "sy": [(0, 1, "linear"), (0.32, 0.94, "out"), (0.6, 1.04, "sine"), (0.92, 1.0, "in"),
           (1.1, 0.70, "out"), (1.25, 1.02, "elastic"), (1.45, 1.0, "sine"),
           (1.8, 1.02, "sine"), (2.2, 1.0, "sine")],
    "sx": [(0, 1, "linear"), (0.32, 1.03, "out"), (0.6, 0.98, "sine"), (0.92, 1.0, "in"),
           (1.1, 1.24, "out"), (1.25, 0.98, "elastic"), (1.45, 1.0, "sine"),
           (2.2, 1.0, "linear")],
}, events=[(0.92, "land"), (1.45, "recover")]))

# 打闹：忽左忽右窜，身体跟着加速度歪
_add(Clip("brawl", 0.98, loop=True, label="打闹", tracks={
    "rot": [(0, -9, "sine"), (0.245, 9, "sine"), (0.49, -9, "sine"),
            (0.735, 9, "sine"), (0.98, -9, "sine")],
    "bob": [(0, 0, "in"), (0.175, -4, "out"), (0.35, 0, "in"),
            (0.525, -4, "out"), (0.7, 0, "in"), (0.875, -4, "out"), (0.98, 0, "in")],
    "sy": [(0, 1, "sine"), (0.245, 1.03, "sine"), (0.49, 1, "sine"), (0.735, 1.03, "sine"),
           (0.98, 1, "sine")],
    "sx": [(0, 1, "sine"), (0.245, 0.98, "sine"), (0.49, 1, "sine"), (0.735, 0.98, "sine"),
           (0.98, 1, "sine")],
}))

# 蹦蹦跳：连跳三下，一下比一下矮，每跳落地有压缩
_add(Clip("hop", 2.04, label="蹦蹦跳", tracks={
    "bob": [(0, 0, "linear"), (0.34, -92, "out"), (0.68, 0, "in"),
            (1.02, -66, "out"), (1.36, 0, "in"),
            (1.70, -46, "out"), (2.04, 0, "in")],
    "rot": [(0, 0, "linear"), (0.34, 3, "sine"), (0.68, 0, "linear"),
            (1.02, -3, "sine"), (1.36, 0, "linear"),
            (1.70, 3, "sine"), (2.04, 0, "linear")],
    "sy": [(0, 1, "linear"), (0.34, 1.05, "out"), (0.53, 0.84, "in"), (0.68, 1, "back"),
           (1.02, 1.04, "out"), (1.21, 0.86, "in"), (1.36, 1, "back"),
           (1.70, 1.03, "out"), (1.88, 0.90, "in"), (2.04, 1, "back")],
    "sx": [(0, 1, "linear"), (0.34, 0.96, "out"), (0.53, 1.14, "in"), (0.68, 1, "back"),
           (1.02, 0.97, "out"), (1.21, 1.12, "in"), (1.36, 1, "back"),
           (1.70, 0.98, "out"), (1.88, 1.08, "in"), (2.04, 1, "back")],
}, events=[(0.68, "land"), (1.36, "land"), (2.04, "land")]))


def names() -> list:
    return list(CLIPS.keys())


# 哪些状态归时间轴管（pet_window 切到别状态时会停播）
TIMELINE_STATES = tuple({s for c in CLIPS.values() for s in c.states})


def describe(name: str) -> str:
    c = CLIPS.get(name)
    if not c:
        return f"{name}: 无时间轴动作"
    return (f"{name}（{c.label}）时长 {c.duration}s"
            f"{'，循环' if c.loop else '，单次'}，{len(c.tracks)} 条轨道，"
            f"{len(c.events)} 个事件点")
