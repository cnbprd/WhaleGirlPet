# -*- coding: utf-8 -*-
"""P3 学习路线索引回归：只读目录名/文件名，不读取正文。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import security_learning

data = security_learning.scan_library()
assert "sections" in data and "total_files" in data
assert data["total_files"] >= 1, "no indexed files"
assert len(data["sections"]) >= 4, "route sections too few"
assert all("files" in s and "count" in s for s in data["sections"])
text = security_learning.route_text()
assert "只索引" in text and "不提供攻击步骤" in text
assert "F:\\数据" in text or "F:/数据" in text
print("security_learning_ok", data["total_files"], "files /",
      data["total_mb"], "MB /", len(data["sections"]), "sections")
