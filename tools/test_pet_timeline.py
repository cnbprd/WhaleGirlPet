# -*- coding: utf-8 -*-
"""pet_window 集成冒烟：do_action 播放 clip → _tick 输出被时间轴接管 → 收尾停播。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import QApplication  # noqa: E402

import pet_window as pw  # noqa: E402

app = QApplication([])


class Ctl:
    def __init__(self):
        self.config = {"skin": "default", "anim_timeline": True, "scale": 1.0}

    def on_action(self, key):
        pass

    def on_panic(self):
        pass

    def on_walk(self):
        pass

    def on_run(self):
        pass

    def on_pat(self):
        pass

    def on_feed(self, k):
        pass

    def get_name(self):
        return "鲸鱼娘"


ctl = Ctl()
pet = pw.PetWindow(ctl, show_now=False)
print("PetWindow 建好，初始 state=", pet.state, "tl.playing=", pet.tl.playing)

for key in ("hop", "tumble", "crab", "look"):
    pet.do_action(key)
    print(f"\n[{key}] do_action 后 tl.playing={pet.tl.playing} clip={pet.tl.clip.name if pet.tl.clip else None}")
    samples = []
    for i in range(0, 80):
        pet._tick()
        if i % 10 == 0:
            samples.append((round(i * 33 / 1000.0, 2), round(pet.bob, 1),
                            round(pet.rot, 1), round(pet.sy, 3), pet.mirror, pet.state))
    for s in samples:
        print("   t,bob,rot,sy,mirror,state:", s)
    print("   结束 state=", pet.state, "tl.playing=", pet.tl.playing)

# 关掉开关时应回到旧公式（tl 不播）
ctl.config["anim_timeline"] = False
pet.do_action("hop")
print("\n关闭开关后 tl.playing=", pet.tl.playing)
pet._tick()
print("  旧公式 bob=", round(pet.bob, 1), "state=", pet.state)
pet.anim.stop()
pet.bubble.close()
