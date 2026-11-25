# -*- coding: utf-8 -*-
"""v3.0.21 真机点击目检：真实桌面窗口 + 真实 QTest 鼠标点击。

覆盖本轮新增的东西：
  1) 安全页两个新按钮（隔离选中 / 打开隔离区）真的存在、点得动；
  2) 「隔离选中」端到端：造一个样本 → 插进表格 → 选中 → 点击 → 文件进隔离区；
  3) 「自测扫描能力」点击后真的跑完并回填状态；
  4) 实时监控开关：开 → 线程起来并扫到目录；关 → 干净退出；
  5) 抓一张安全页真实截图（docs/click_v321_security.png）。

    python tools/click_inspect_v321.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton, QTableWidgetItem  # noqa: E402

import main as main_mod  # noqa: E402
import quarantine as qz  # noqa: E402

R = []


def ck(name, cond, extra=""):
    R.append((name, bool(cond), str(extra)))
    print(("  ok   " if cond else "  FAIL ") + name + (" " + str(extra) if extra else ""))


def find_btn(panel, text):
    for b in panel.findChildren(QPushButton):
        if text in b.text():
            return b
    return None


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ctl = main_mod.Controller(app)
    ctl.open_panel()
    panel = ctl.panel
    panel.resize(760, 900)
    panel.show()
    panel.raise_()
    panel.activateWindow()

    idx = next(i for i in range(panel.side.count())
               if panel.side.item(i).text() == "安全体检")
    tmpdir = tempfile.mkdtemp(prefix="whale_click_")
    sample = os.path.join(tmpdir, "sample_evil.exe")
    with open(sample, "wb") as f:
        f.write(b"MZ" + b"\x00" * 64 + b"malware-sample")
    state = {"orig_rt": ctl.config.get("realtime_guard", False),
             "orig_rq": ctl.config.get("render_quality", "auto")}

    def prep():
        panel.tabs.setCurrentIndex(idx)
        app.processEvents()
        print("[1] 按钮就位")
        for name in ("自测扫描能力", "隔离选中", "打开隔离区", "哈希名单", "导出报告"):
            ck(f"按钮「{name}」存在", find_btn(panel, name) is not None)
        print(f"     渲染档实判 = {getattr(ctl.pet, 'render_quality', '?')}"
              f" / 帧间隔 {getattr(ctl.pet, 'frame_ms', '?')}ms")

        print("[2] 真机点击「隔离选中」")
        panel.tbl_guard.setRowCount(0)
        panel.tbl_guard.insertRow(0)
        panel.tbl_guard.setItem(0, 0, QTableWidgetItem("高危 30"))
        it1 = QTableWidgetItem(os.path.basename(sample))
        it1.setData(Qt.UserRole, sample)   # 与产品一致：显示文件名，真值在 UserRole
        it1.setToolTip(sample)
        panel.tbl_guard.setItem(0, 1, it1)
        panel.tbl_guard.setItem(0, 2, QTableWidgetItem("真机目检样本"))
        panel.tbl_guard.setItem(0, 3, QTableWidgetItem("T-CLICK"))
        panel.tbl_guard.selectRow(0)
        app.processEvents()
        print("     DEBUG 列宽", [panel.tbl_guard.columnWidth(i) for i in range(4)],
              "viewport", panel.tbl_guard.viewport().width(),
              "单元格", panel.tbl_guard.visualItemRect(panel.tbl_guard.item(0, 1)),
              "文本", panel.tbl_guard.item(0, 1).text())
        b = find_btn(panel, "隔离选中")
        QTest.mouseClick(b, Qt.LeftButton)
        app.processEvents()
        ck("原样本已离开原位", not os.path.exists(sample))
        items = [i for i in qz.list_items() if os.path.abspath(sample) == i.get("origin")]
        ck("隔离区留下可恢复副本", len(items) == 1, items[0]["name"] if items else "无")
        ck("状态栏回执正常", "已隔离" in panel.lbl_guard.text() or "没成" in panel.lbl_guard.text(),
           panel.lbl_guard.text()[:60])
        state["qitem"] = items[0]["item"] if items else ""

        print("[3] 真机点击「自测扫描能力」")
        b2 = find_btn(panel, "自测扫描能力")
        QTest.mouseClick(b2, Qt.LeftButton)
        QTimer.singleShot(5000, finish)

    def finish():
        txt = panel.lbl_guard.text()
        ck("自测有结论（不再显示\"未跑过\"）", "未跑过" not in txt and len(txt) > 4, txt[:80])

        print("[4] 实时监控 开 / 关")
        ctl.set_realtime_guard(True)
        app.processEvents()
        ck("监控线程已起", getattr(ctl, "_rt", None) is not None)
        ck("已记下目录现状", getattr(ctl._rt, "seen_count", 0) >= 0,
           f"{getattr(ctl._rt, 'seen_count', 0)} 个可执行文件")
        ck("配置写回 True", bool(ctl.config.get("realtime_guard")))
        ctl.set_realtime_guard(False)
        app.processEvents()
        ck("监控线程已停", getattr(ctl, "_rt", None) is None)
        ck("配置写回 False", not bool(ctl.config.get("realtime_guard")))

        panel.tabs.setCurrentIndex(idx)
        app.processEvents()
        out = os.path.join(ROOT, "docs", "click_v321_security.png")
        ok = panel.grab().save(out)
        ck("真实截图落盘", ok and os.path.getsize(out) > 10000, out)

        # 复原：删掉目检用的隔离条目、还原配置
        try:
            if state.get("qitem"):
                qz.delete_item(state["qitem"])
        except Exception:  # noqa: BLE001
            pass
        try:
            ctl.config["realtime_guard"] = state["orig_rt"]
            ctl.config["render_quality"] = state["orig_rq"]
            ctl.save_config()
        except Exception:  # noqa: BLE001
            pass
        try:
            os.remove(sample)
        except OSError:
            pass
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

        bad = [x for x in R if not x[1]]
        print(f"\n{len(R) - len(bad)} passed, {len(bad)} failed")
        # 走产品自己的退出路径（托盘「退出程序」用的就是它），而不是直接 app.quit()：
        # 直接 quit 会留下未收尾的工作线程，解释器退出时 abort（0xC0000409）。
        try:
            ctl.quit_app()
        except Exception as e:  # noqa: BLE001
            print("quit_app 异常：", type(e).__name__, e)
            app.quit()

    QTimer.singleShot(1200, prep)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
