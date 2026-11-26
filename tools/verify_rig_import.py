# -*- coding: utf-8 -*-
"""B 路线迁移层验收：Spine 兼容 JSON → 自研 RigModel → 多 slot 静态渲染。

运行：.venv\\Scripts\\python.exe tools\\verify_rig_import.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PIL import Image, ImageChops  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from rig_runtime import RigRenderer  # noqa: E402
from spine_import import load_rig  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond)))
    print(("  ok   " if cond else "  FAIL ") + name + ("  " + str(extra) if extra else ""))


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    rig_path = os.path.join(ROOT, "assets", "skins", "rig", "default_rig.json")
    rig = load_rig(rig_path)
    ck("Spine 版本解析", rig.spine == "4.0.0", rig.spine)
    ck("骨骼树 7 根", len(rig.bones) == 7, [b.name for b in rig.bones])
    ck("slot 顺序 body→hair→tail→skirt",
       [s.name for s in rig.slots] == ["body", "hair_l", "hair_r", "tail", "skirt"],
       [s.name for s in rig.slots])
    ck("父子链 hair_l→head→spine→root",
       rig.bone_map()["hair_l"].parent == "head"
       and rig.bone_map()["head"].parent == "spine"
       and rig.bone_map()["spine"].parent == "root",
       [b.parent for b in rig.bones])

    rest = rig.world({})
    ck("root 落点", abs(rest["root"][0] - 133.5) < 0.1 and abs(rest["root"][1] - 300.03) < 0.1,
       rest["root"])
    ck("hair_l 静止枢轴", abs(rest["hair_l"][0] - 37.38) < 0.2
       and abs(rest["hair_l"][1] - 117.76) < 0.2, rest["hair_l"])
    ck("tail 静止枢轴", abs(rest["tail"][0] - 168.21) < 0.2
       and abs(rest["tail"][1] - 281.6) < 0.2, rest["tail"])

    for slot in rig.slots:
        path = rig.path_for(slot)
        ck("附件路径存在 %s" % slot.name, bool(path) and os.path.exists(path), path)

    rr = RigRenderer(rig)
    static = rr.render({})
    static.save(os.path.join(ROOT, "docs", "_rig_static.png"))
    src = Image.open(os.path.join(ROOT, "assets", "skins", "default.png")).convert("RGBA")
    shot = Image.open(os.path.join(ROOT, "docs", "_rig_static.png")).convert("RGBA")
    diff = ImageChops.difference(shot, src)
    mean = sum(diff.convert("L").getdata()) / (src.width * src.height)
    ck("静止位多 slot 渲染原图", mean < 0.5, "mean_abs=%.4f bbox=%s" % (mean, diff.getbbox()))

    head8 = rig.world({"head": 8.0})
    ck("头转 8° 带动左右发束", abs(head8["hair_l"][0] - rest["hair_l"][0]) > 0.5
       and abs(head8["hair_l"][1] - rest["hair_l"][1]) > 0.5, (rest["hair_l"], head8["hair_l"]))
    ck("头转不带动尾巴/裙摆",
       head8["tail"][0] == rest["tail"][0] and head8["tail"][1] == rest["tail"][1]
       and head8["skirt"][0] == rest["skirt"][0], (head8["tail"], head8["skirt"]))
    rr.render({"head": 8.0}).save(os.path.join(ROOT, "docs", "_rig_head8.png"))

    hair4 = rig.world({"hair_l": 4.0})
    ck("单束发 4° 只改自己角度", abs(hair4["hair_l"][2] - 4.0) < 1e-6
       and abs(hair4["hair_r"][2]) < 1e-6, (hair4["hair_l"], hair4["hair_r"]))

    print("\n===== %d/%d =====" % (sum(1 for _, ok in R if ok), len(R)))
    for name, ok in R:
        if not ok:
            print("FAIL:", name)


if __name__ == "__main__":
    main()
