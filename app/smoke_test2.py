# -*- coding: utf-8 -*-
"""第二轮扩展功能离屏测试：动作、新任务、清理扫描、图标布局、更新检查、气泡。"""
import os
import sys
import faulthandler
faulthandler.enable()

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

import cleanup
import desktop_icons
import main
import pet_window

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
ctl = main.Controller(app)
ctl.open_panel()
ctl.refresh_panel()

# 1. 全部动作切换一遍
for key in pet_window.ALL_ACTIONS:
    ctl.pet.do_action(key, 80)
print("actions ok:", len(pet_window.ALL_ACTIONS))

# 2. 新任务与旧任务逐个结算
for key in ["cleanup", "wipe", "chores", "study", "patrol", "stretch"]:
    ctl.start_task(key)
    assert ctl.task_active is not None, key
    ctl._finish_task()
print("tasks ok")

# 3. 清理扫描（不删除）
scan = cleanup.scan()
print("scan files:", scan["files"], "bytes:", scan["bytes"])

# 4. 桌面图标布局读取
lay = desktop_icons.IconLayout()
lay.reload()
print("icons backed up:", len(lay.backup), "available:", desktop_icons.available())

# 5. 更新检查（未配置地址）
ctl.check_update()

# 6. 碎碎念开关
ctl.toggle_chatter(False)
assert ctl.config["chatter_on"] is False
ctl.toggle_chatter(True)

# 7. 聊天气泡
ctl.panel.append_chat("user", "测试消息一行")
ctl.panel.append_chat("assistant", "回复气泡第二行")

QTimer.singleShot(1000, ctl.quit_app)
sys.exit(app.exec())
