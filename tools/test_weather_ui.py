# -*- coding: utf-8 -*-
"""v3.0.10 天气资讯页冒烟：天气卡片渲染 + 资讯框是否顶到页面底部。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"F:\WhaleGirlPet\app")

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

import ambient  # noqa: E402
import panel as panel_mod  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"weather_city": "郑州", "weather_on": True, "news_on": True}
        self._ambient_cache = {"city": "郑州",
                               "weather": {"t": 15.6, "text": "晴", "hum": 33.0,
                                           "tmax": 21.0, "tmin": 3.0, "air": "优",
                                           "src": "itboy", "feels": None, "wind": None,
                                           "pop": None},
                               "news": []}
        self.saved = 0

    def save_config(self):
        self.saved += 1

    def set_weather_city(self, city):
        self.config["weather_city"] = city

    def _on_ambient_tick(self, force=False):
        return None


app = QApplication([])
p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)
p.ctl = StubCtl()
page = p._tab_ambient()
page.resize(760, 560)
page.show()
app.processEvents()

print("温度大字:", p.lbl_w_temp.text())
print("描述:", p.lbl_w_desc.text())
print("详情:", p.lbl_w_detail.text())
print("今日:", p.lbl_w_today.text())
print("来源行:", p.lbl_w_src.text())
print("城市框:", p.ed_city.text())
print("资讯框最小高:", p.txt_news.minimumHeight(), "最大高:", p.txt_news.maximumHeight())
print("页面高:", page.height(), "资讯框高:", p.txt_news.height(),
      "资讯框底边:", p.txt_news.geometry().bottom(), "页面内容底:", page.contentsRect().bottom())

# 真联网再拉一次（不要缓存）验证 WeatherWorker
w = ambient.WeatherWorker("郑州")
res = {}
w.done.connect(lambda d: res.update(d))
w.failed.connect(lambda e: res.update({"err": e}))
w.start()
w.wait(20000)
for _ in range(30):
    app.processEvents()
print("WeatherWorker 结果:", res)
if res and not res.get("err"):
    p._show_weather(res, "郑州")
    print("联网后 温度/描述/详情:", p.lbl_w_temp.text(), "|", p.lbl_w_desc.text(), "|", p.lbl_w_detail.text())
    print("联网后 今日/来源:", p.lbl_w_today.text(), "|", p.lbl_w_src.text())
page.close()
