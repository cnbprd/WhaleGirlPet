# -*- coding: utf-8 -*-
"""轻量 UI 冒烟：只构造「自定义模型」页那几个控件，验证新扫描逻辑能在面板里正确渲染。

不启动桌宠、不写用户 config（stub controller 完全是内存对象）。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import (QApplication, QComboBox, QLabel, QLineEdit,  # noqa: E402
                               QListWidget, QProgressBar, QWidget)

import local_llm  # noqa: E402
import panel as panel_mod  # noqa: E402
import models_catalog  # noqa: E402


class StubLlm:
    """假引擎：只有 status()，用来验证面板状态行，不真起进程。"""

    ollama_broken = False

    def status(self):
        return {"backend": "dafeiyu_cpp", "model": "qwen3.5-4b.gguf",
                "model_path": r"F:\WhaleGirlPetApp\models\qwen3.5-4b.gguf",
                "running": True, "ready": True, "port": 8085, "port_auto": True,
                "fallback": "首选 _bad.gguf 起不来，已自动换成 qwen3.5-4b.gguf",
                "last_error": "", "busy": False, "idle_min": 3.2}


class StubCtl:
    def __init__(self):
        # v3.0.9：配置里故意留一个老的 "ollama"，验证会自动归成「自动」
        self.config = {"llm_model_file": r"F:\WhaleGirlPet\runtime\models\gemma4-e2b-it.gguf",
                       "llm_backend": "ollama"}
        self.llm = StubLlm()
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
p.lbl_engine = QLabel()
p.lst_models = QListWidget()
p.lbl_dl = QLabel()
p.pbar_model = QProgressBar()
p.ed_model_url = QLineEdit()
p.cmb_backend = QComboBox()
p.cmb_backend.addItem("自动", "auto")
p.cmb_backend.addItem("只用自带引擎 dafeiyu", "dafeiyu_cpp")

p._refresh_models()
print("当前模型行:", p.lbl_cur_model.text())
print("调度状态行:", p.lbl_engine.text())
print("下拉现在停在:", p.cmb_backend.currentData(),
      "| 配置已归一为:", p.ctl.config.get("llm_backend"))
print("tooltip 首行:", p.lbl_cur_model.toolTip().splitlines()[0])
print("列表条数:", p.lst_models.count())
for i in range(p.lst_models.count()):
    it = p.lst_models.item(i)
    print(f"  [{i}] {it.text()[:90]}")
print("添加文件夹方法存在:", hasattr(p, "_add_model_dir"))
