# -*- coding: utf-8 -*-
"""v2.3.0 联调：步态、任务动作、每分钟定时、语音入口、绘制耗时。"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

from main import Controller  # noqa: E402

ctl = Controller(app)
pet = ctl.pet
pet.show()
app.processEvents()

print("--- 1) 步态 ---")
pet.do_walk()
app.processEvents()
t0 = time.time()
frames = 0
while time.time() - t0 < 2.0:
    app.processEvents()
    time.sleep(0.033)
    frames += 1
print("walk state:", pet.state, "| gait_on:", pet.gait_on, "| gait:",
      round(pet.gait, 2), "| frames:", frames)
pet.finish_state()
app.processEvents()

print("--- 2) 单帧绘制耗时（步态开启）---")
pet.gait_on = True
t0 = time.time()
for i in range(30):
    pet.gait = i / 30.0
    pet.repaint()
print(f"30 帧 repaint: {time.time()-t0:.3f}s -> {(time.time()-t0)/30*1000:.1f} ms/帧")
pet.gait_on = False

print("--- 3) 任务动作 ---")
ctl.start_task("wipe")
app.processEvents()
print("task_active:", ctl.task_active, "| pet.state:", pet.state, "| action_key:", pet.action_key)
ctl.task_timer.stop()
ctl.task_active = None
pet.finish_state()
ctl.pet.restore_base_expression()

print("--- 4) 每分钟定时（病毒库槽位 / 防火墙周检）---")
ctl.config["av_slots_done"] = ""
ctl.config["fw_check_day"] = ""
ctl._on_minute()
app.processEvents()
print("fw_check_day:", ctl.config.get("fw_check_day"), "| fw_worker:",
      getattr(ctl, "fw_worker", None))

print("--- 5) 语音入口（无麦克风输入，4 秒应回 no_speech）---")
ctl.voice_listen()
t0 = time.time()
while time.time() - t0 < 25:
    app.processEvents()
    time.sleep(0.1)
    if ctl.voice_worker is not None and not ctl.voice_worker.isRunning():
        break
print("voice result:", ctl._last_voice if hasattr(ctl, "_last_voice") else "见气泡/状态栏")
print("chat status:", ctl.panel.get_chat_status() if ctl.panel and hasattr(ctl.panel, "get_chat_status") else "-")

print("--- 6) 后端 ---")
print(ctl.local_llm_info().get("backend"), ctl.local_llm_info().get("model"))
print("DONE")
