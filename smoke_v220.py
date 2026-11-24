# -*- coding: utf-8 -*-
"""v2.2.0 联调：真实启动 Controller，验证安全页新数据 + 开机早报安全段 + 能力层。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

root = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(root, "assets", "_matting")
ctl = Controller(app)
ctl.open_panel()
p = ctl.panel
p.resize(600, 780)
p.show()
app.processEvents()

idx = [i for i in range(p.tabs.count()) if p.tabs.tabText(i) == "安全体检"][0]
p.tabs.setCurrentIndex(idx)
app.processEvents()

print("--- 1) 安全摘要（开机早报用） ---")
ctl._on_boot_security(__import__("secscan").defense_summary())
app.processEvents()
print("security_line:", ctl.security_line())
app.processEvents()
p.grab().save(os.path.join(out_dir, "v22-tab-security-summary.png"))

print("--- 2) 全量体检 ---")
ctl.run_scan()
t0 = time.time()
while time.time() - t0 < 20:
    app.processEvents()
    time.sleep(0.1)
    if ctl.last_scan():
        break
r = ctl.last_scan()
print("scan done:", bool(r), "score:", r.get("score"))
print("keys:", sorted(r.keys()))
app.processEvents()
p.grab().save(os.path.join(out_dir, "v22-tab-security-full.png"))
print("--- 3) 安全页文本 ---")
print(p.txt_scan.toPlainText()[:520])

print("--- 4) 能力层状态 ---")
print("llm info:", ctl.local_llm_info())
print("DONE")
