import cProfile, pstats, sys, os, io
sys.path.insert(0, os.path.abspath("app"))
from PySide6.QtWidgets import QApplication
import main as m
app = QApplication([]); app.setQuitOnLastWindowClosed(False)
ctl = m.Controller(app)
pr = cProfile.Profile(); pr.enable()
ctl.open_panel()
pr.disable()
s = io.StringIO()
pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(24)
txt = s.getvalue()
print("\n".join([l for l in txt.splitlines() if l.strip()][:40]))
app.quit()
