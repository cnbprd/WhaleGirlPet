# -*- coding: utf-8 -*-
"""v3.0.10 安全页冒烟：安全管家区块 + 表格渲染 + 主控方法齐全。"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import QApplication  # noqa: E402
import guard_core as g  # noqa: E402
import panel as panel_mod  # noqa: E402
import panel_v2  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {}
        self.guard_report = {}

    def run_scan(self):
        return None

    def update_signatures(self, silent=False):
        return False

    def run_guard_scan(self):
        return True


app = QApplication([])
p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)
p.ctl = StubCtl()

w = panel_v2.tab_security(p)
w.resize(720, 620)
w.show()
app.processEvents()
print("安全页控件:", [x for x in ("btn_guard", "lbl_guard", "tbl_guard", "txt_scan")
                     if hasattr(p, x)])

rep = g.deep_scan(roots=[r"F:\WhaleGirlPet\tools\_guard_samples"])
rep["files"] = {"md": r"F:\WhaleGirlPetApp\reports\guard_demo.md"}
p.refresh_guard(rep)
print("状态行:", p.lbl_guard.text())
print("表格行数:", p.tbl_guard.rowCount(), "列数:", p.tbl_guard.columnCount())
for r in range(min(3, p.tbl_guard.rowCount())):
    print("  行:", " | ".join((p.tbl_guard.item(r, c).text() if p.tbl_guard.item(r, c) else "")[:42]
                              for c in range(4)))
p.on_guard_progress(60, "已解析 120/244")
print("进度行:", p.lbl_guard.text())
print("Defender 回调:", end=" ")
p.on_defender_done({"ok": True, "msg": "Scan starting... Scan finished. found no threats."})
print(p.lbl_guard.text()[:80])

import main as main_mod  # noqa: E402
for name in ("run_guard_scan", "guard_defender", "_on_guard_done", "_on_defender_done"):
    print(f"主控方法 {name}:", hasattr(main_mod.ControlPanel, name))
print("guard_core worker:", g.GuardWorker is not None, g.DefenderWorker is not None)
