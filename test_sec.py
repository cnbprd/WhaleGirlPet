# -*- coding: utf-8 -*-
"""验证新增的安全体检项：病毒库 / 防火墙 / 拦截记录 / 早报摘要。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import secscan  # noqa: E402

t = time.time()
av = secscan.av_health()
print("AV:", av, f"({time.time()-t:.1f}s)")

t = time.time()
fw = secscan.firewall_status()
print("FW:", fw, f"({time.time()-t:.1f}s)")

t = time.time()
th = secscan.threat_history(7)
print("THREATS:", th, f"({time.time()-t:.1f}s)")

t = time.time()
print("SUMMARY:", secscan.defense_summary(), f"({time.time()-t:.1f}s)")

t = time.time()
rep = secscan.build_report()
print(f"REPORT {time.time()-t:.1f}s score={rep['score']}")
for i in rep["issues"]:
    print("  ", i["level"], i["text"])
print("keys:", sorted(rep.keys()))
