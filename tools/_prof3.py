import cProfile, pstats, sys, os, io
sys.path.insert(0, os.path.abspath("app"))
from PySide6.QtWidgets import QApplication
import main as m
app = QApplication([]); app.setQuitOnLastWindowClosed(False)
ctl = m.Controller(app)
pr = cProfile.Profile(); pr.enable()
ctl.open_panel()
pr.disable()
st = pstats.Stats(pr)
for key in ("read","recv_into","setStyleSheet","connect"):
    s = io.StringIO()
    st.stream = s
    st.print_callers(key)
    lines = [l.rstrip() for l in s.getvalue().splitlines() if l.strip()]
    print("=====", key)
    for l in lines[:14]:
        print(l)
app.quit()
