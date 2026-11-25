# -*- coding: utf-8 -*-
"""轻量 UI 冒烟：只构造「自定义模型」页那几个控件，验证新扫描逻辑能在面板里正确渲染。

不启动桌宠、不写用户 config（stub controller 完全是内存对象）。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import (QApplication, QLabel, QLineEdit, QListWidget,  # noqa: E402
                               QProgressBar, QWidget)

import local_llm  # noqa: E402
import panel as panel_mod  # noqa: E402
import models_catalog  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"llm_model_file": r"F:\WhaleGirlPet\runtime\models\gemma4-e2b-it.gguf"}
        self.saved = 0

    def local_models(self):
        return local_llm.scan_models(self.config)

    def model_search_dirs(self):
        return local_llm.model_dirs(self.config)

    def save_config(self):
        self.saved += 1

    def use_model(self, name):
        return bool(local_llm.resolve_model(name, self.config))

    def delete_model(self, name):
        return 0.0


app = QApplication([])
p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)   # 绕开 __init__，不建整窗
p.ctl = StubCtl()
p.lbl_cur_model = QLabel()
p.lst_models = QListWidget()
p.lbl_dl = QLabel()
p.pbar_model = QProgressBar()
p.ed_model_url = QLineEdit()

p._refresh_models()
print("当前模型行:", p.lbl_cur_model.text())
print("tooltip 首行:", p.lbl_cur_model.toolTip().splitlines()[0])
print("列表条数:", p.lst_models.count())
for i in range(p.lst_models.count()):
    it = p.lst_models.item(i)
    print(f"  [{i}] {it.text()[:90]}")
print("模型页控件构建:", type(panel_mod.__dict__.get("ControlPanel")).__name__)
print("添加文件夹方法存在:", hasattr(p, "_add_model_dir"))
