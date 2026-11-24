# -*- coding: utf-8 -*-
"""v2.9.7 逻辑自检：零食经济、背包、吃法决策、脚本安全检查、硬件变化检测。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))

import companion
import hardware
import maker
import snacks
from state import PetState

ok = True


def check(name, cond, extra=""):
    global ok
    print(("PASS " if cond else "FAIL ") + name + (" | " + extra if extra else ""))
    if not cond:
        ok = False


# 1) 价格护栏
bad = [s for s in snacks.all_items() if not (4 <= s["cost"] <= 45)]
check("价格都在 4~45", not bad, str([(s['name'], s['cost']) for s in bad]))

# 2) 背包链路
st = PetState()
st.coins = 100
buy_ok, buy_msg = st.buy("fish")
check("买一份进背包", buy_ok and st.bag.get("fish") == 1, buy_msg)
check("买完扣钱", st.coins == 100 - snacks.by_key("fish")["cost"], str(st.coins))
eat_ok, eat_msg = st.eat("fish", auto_buy=False)
check("从背包吃一份", eat_ok and "fish" not in st.bag, eat_msg)
# 再吃一次（背包空了，且禁止自动买）应失败
again_ok, again_msg = st.eat("fish", auto_buy=False)
check("背包空了就不再凭空吃", not again_ok, again_msg)
# 旧接口仍可用（自动买）
st.coins = 50
old_ok, old_msg = st.feed("rice")
check("旧 feed 接口兼容", old_ok, old_msg)

# 3) 口渴与需求
st2 = PetState()
st2.hunger = 20
check("饿 → need hungry", st2.need_kind() == "hungry", st2.need_kind())
st2.hunger = 90
st2.thirst = 10
check("渴 → need thirsty", st2.need_kind() == "thirsty", st2.need_kind())
st2.thirst = 90
st2.mood = 10
check("心情差 → need mood", st2.need_kind() == "mood", st2.need_kind())
st2.mood = 90
st2.coins = 10
check("没钱 → need coins", st2.need_kind() == "coins", st2.need_kind())
check("喝水回水", st2.drink()[0] and st2.thirst > 10, str(st2.thirst))

# 4) 吃法决策：很饿必吃
st3 = PetState()
st3.hunger = 10
check("很饿 → eat", companion.decide_food_destiny(st3) == "eat")
st3.hunger = 70
st3.mood = 30
check("不太饿心情一般 → bag", companion.decide_food_destiny(st3) == "bag")

# 5) 脚本风险检查
danger = "import os\nos.system('del /f C:\\\\*')\n"
check("危险脚本被拦", maker.check_code(danger), str(maker.check_code(danger)))
safe = "import os\nprint(os.path.expanduser('~'))\n"
check("普通脚本放行", not maker.check_code(safe), str(maker.check_code(safe)))
check("代码块抽取", "print" in maker.extract_code("说明\n```python\nprint(1)\n```"), "")
check("本机有 python 可运行", maker.can_run(), maker._python_exe())

# 6) 硬件变化检测
old = {"gpu": "GTX 1060", "vram_gb": 6.0, "ram_gb": 32.0, "threads": 8}
new = dict(old, vram_gb=12.0)
d = hardware.diff(old, new)
check("显存变化被识别", bool(d) and "显存" in d[0], str(d))
check("没变化不报", not hardware.diff(old, dict(old)), "")

print("\nRESULT:", "ALL PASS" if ok else "HAS FAIL")
sys.exit(0 if ok else 1)
