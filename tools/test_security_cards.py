# -*- coding: utf-8 -*-
"""P2 知识卡回归：字段完整、可按 issue 命中、不含攻击工具/命令名。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import security_cards

cards = security_cards.all_cards()
assert len(cards) >= 10
ids = [c["id"] for c in cards]
assert len(ids) == len(set(ids)), "duplicate card id"
for c in cards:
    for key in ("id", "title", "summary", "signals", "defense", "source", "tags"):
        assert key in c and c[key], f"{c.get('id')} missing {key}"
    text = security_cards.card_text(c)
    assert "怎么防：" in text and "看什么：" in text
    low = text.lower()
    for bad in ("sqlmap", "msfconsole", "meterpreter", "mimikatz",
                "nc -e", "bash -i", "hping3", "loic"):
        assert bad not in low, f"attack tool leaked in {c['id']}: {bad}"

hit = security_cards.relevant_cards({
    "issues": [
        {"level": "warn", "text": "远程桌面 RDP 已开启；不用时建议关闭 3389"},
        {"level": "high", "text": "Office 宏设为“启用所有宏”：Excel 16.0"},
    ]
})
assert any(c["id"] == "rdp" for c in hit)
assert any(c["id"] == "office" for c in hit)
print("security_cards_ok", len(cards), "cards; hit", [c["id"] for c in hit])
