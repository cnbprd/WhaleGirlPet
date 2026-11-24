# -*- coding: utf-8 -*-
"""v2.9.4 自检：面板去掉音频库/记忆知识、模型库「已安装」分区、音色联网实验台与指令解析。

    .venv/Scripts/python.exe test_v294.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication

import main as m
import persona as pers
import voice_tweak

FAIL = []


def check(name, cond, detail=""):
    print(("  OK   " if cond else "  FAIL ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(name)


app = QApplication([])
ctl = m.Controller(app)
old_persona = ctl.config.get("persona")
old_custom = list(ctl.config.get("custom_voices") or [])

print("== 1. 页面结构 ==")
ctl.open_panel()
p = ctl.panel
labels = [p.side.item(i).text() for i in range(p.side.count())]
check("页面数 10", p.side.count() == 10, str(labels))
check("没有音频库", "音频库" not in labels)
check("没有记忆知识", "记忆知识" not in labels)
check("还有模型库", "模型库" in labels, str(labels))
check("还有语音人格", "语音人格" in labels)

print("== 2. 模型库分区 ==")
p._refresh_models()
rows = [p.lst_models.item(i).text() for i in range(p.lst_models.count())]
local = [r for r in rows if r.startswith("[已安装]")]
check("有「已安装模型」分区标题", any("已安装模型" in r for r in rows))
check("已安装条数 = 本地 gguf 条数", len(local) == len(ctl.local_models()),
      f"{len(local)} / {len(ctl.local_models())}")
check("有「内置模型」分区标题", any("内置模型" in r for r in rows))
check("分区顺序：已安装在内置之前",
      rows.index(next(r for r in rows if "已安装模型" in r))
      < rows.index(next(r for r in rows if "内置模型" in r)))
print("  前 4 行：", rows[:4])

print("== 3. 音色实验台控件 ==")
check("音色下拉", hasattr(p, "cmb_net_voice"))
check("指令输入框", hasattr(p, "ed_voice_cmd"))
check("音高/语速/音量滑块",
      all(hasattr(p, x) for x in ("sl_pitch", "sl_rate", "sl_vol")))
p._reset_vparams()
check("重置后参数归零", (p.sl_pitch.value(), p.sl_rate.value(), p.sl_vol.value()) == (0, 0, 80))

print("== 4. 指令解析（纯规则，不联网）==")
cases = [
    ("尖一点", 8, 0, 80),
    ("沉一点", -8, 0, 80),
    ("慢一点", 0, -6, 80),
    ("快一点", 0, 6, 80),
    ("音高 20", 20, 0, 80),
    ("音量 60", 0, 0, 60),
    ("慢 10%", 0, -10, 80),
    ("快 20%", 0, 20, 80),
]
for cmd, ep, er, ev in cases:
    gp, gr, gv, notes = voice_tweak.parse(cmd, 0, 0, 80)
    check(f"「{cmd}」→ ({ep},{er},{ev})", (gp, gr, gv) == (ep, er, ev),
          f"实际 ({gp},{gr},{gv})｜{'；'.join(notes)}")

gp, gr, gv, notes = voice_tweak.parse("默认", 30, 20, 40)
check("「默认」还原", (gp, gr, gv) == (0, 0, 80), f"实际 ({gp},{gr},{gv})")
gp, gr, gv, notes = voice_tweak.parse("今天天气不错", 0, 0, 80)
check("听不懂的指令不改参数", (gp, gr, gv) == (0, 0, 80))
check("听不懂时给出提示", "没听懂" in notes[0], notes[0])

print("== 5. 界面指令一起生效 ==")
p._reset_vparams()
p.ed_voice_cmd.setText("尖一点，慢 10%，音量 70")
p._apply_voice_cmd()
check("滑块被指令改写", (p.sl_pitch.value(), p.sl_rate.value(), p.sl_vol.value()) == (8, -10, 70),
      f"{p.sl_pitch.value()}, {p.sl_rate.value()}, {p.sl_vol.value()}")

print("== 6. 存为我的音色（不试听，只验证落库与人格可选）==")
p.cmb_net_voice.addItem("zh-CN-XiaoyiNeural　zh-CN　女", "zh-CN-XiaoyiNeural")
p.sl_pitch.setValue(5)
p.sl_rate.setValue(3)
p.sl_vol.setValue(75)
p._save_net_voice()
key = "mine_zh_CN_XiaoyiNeural"
check("config 里存下 custom_voices", any(x.get("key") == key for x in (ctl.config.get("custom_voices") or [])))
check("人格下拉里出现自定义音色", p.cmb_persona.findData(key) >= 0)
check("已切到自定义音色", ctl.config.get("persona") == key, str(ctl.config.get("persona")))
check("自定义音色能被 pers.get 读到", pers.get(key).get("voice") == "zh-CN-XiaoyiNeural")
check("音色参数带过去", pers.get(key).get("pitch") == 5 and pers.get(key).get("rate") == 3)

print("== 7. 托盘与本地查看入口 ==")
menu = ctl.tray.contextMenu()
labels2 = [a.text() for a in menu.actions() if a.text()]
check("托盘有「打开数据目录」", any("打开数据目录" in x for x in labels2), str(labels2))
import paths as _paths
check("账号数据目录可本地查看", os.path.isdir(_paths.account_dir()), _paths.account_dir())

# 还原用户配置，别把测试音色留在存档里
ctl.config["custom_voices"] = old_custom
ctl.config["persona"] = old_persona or pers.DEFAULT_PERSONA
pers.register_custom(old_custom)
ctl.save_config()

print()
print("RESULT:", "ALL PASS" if not FAIL else f"{len(FAIL)} FAIL -> {FAIL}")
sys.exit(0 if not FAIL else 1)
