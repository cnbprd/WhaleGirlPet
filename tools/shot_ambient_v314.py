# -*- coding: utf-8 -*-
"""v3.0.14 天气资讯页离屏截图：查分类按钮是否在左、文字字号是否变清楚。

跑法（PowerShell）：
  & "F:/WhaleGirlPet/.venv/Scripts/python.exe" tools/shot_ambient_v314.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtWidgets import QApplication  # noqa: E402

import panel as panel_mod  # noqa: E402


class StubCtl:
    def __init__(self):
        self.config = {"weather_city": "郑州", "news_on": True, "city": "郑州"}
        self._ambient_cache = {}
        self.saved = 0

    def get_name(self):
        return "大肥鱼"

    def save_config(self):
        self.saved += 1

    def voice_listen(self):
        pass


app = QApplication([])
p = panel_mod.ControlPanel.__new__(panel_mod.ControlPanel)
p.ctl = StubCtl()
p._load_weather = lambda: None          # 截图用，别真去联网
page = p._tab_ambient()

# 填一份样例天气，看清字号和配色（真实数据由 WeatherWorker 回填）
p.lbl_w_temp.setText("6°")
p.lbl_w_desc.setText("多云转小雨")
p.lbl_w_detail.setText("体感 4　湿度 78%　风 东北 3 级　降水 0.4mm")
p.lbl_w_today.setText("今日 2 ~ 9°　空气 良（52）")
p.lbl_w_src.setText("中国天气网 · 11-25 21:30 更新")
p.txt_news.setPlainText("\n".join([
    "· 郑州地铁 8 号线今日开通试运营，首末班时间公布",
    "· 河南发布寒潮蓝色预警，明早最低气温将降至 -1℃",
    "· 国产大模型开源周：两家厂商同天放出 30B 级权重",
    "· 国内油价 24 日 24 时起下调，92 号汽油每升降 0.12 元",
    "· 郑州机场新增直飞两条国际航线，春运前上线",
    "· 乒超联赛第三轮：主队 3:2 逆转，决胜盘打到 11:9",
]))
page.resize(760, 560)
img = page.grab()
out = os.path.join(ROOT, "docs", "ambient_v314.png")
img.save(out)

# 用几何位置核对「按钮在左、正文在右」
cat_x = [p.news_cat_btns[k].mapTo(page, p.news_cat_btns[k].rect().topLeft()).x()
         for k in p.news_cat_btns]
news_x = p.txt_news.mapTo(page, p.txt_news.rect().topLeft()).x()
print("分类按钮 x:", cat_x)
print("资讯框 x:", news_x, "| 宽:", p.txt_news.width())
print("按钮都在资讯框左侧:", all(x < news_x for x in cat_x))
print("温度字号:", p.lbl_w_temp.styleSheet())
print("明细字号:", p.lbl_w_detail.styleSheet())
print("截图:", out, os.path.getsize(out), "bytes")
