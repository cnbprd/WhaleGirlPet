# -*- coding: utf-8 -*-
"""Focused test: 2D action routing calls the asset bridge without Qt event loop."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import main  # noqa: E402


class DummyEmotion:
    def apply(self, *args, **kwargs):
        pass


class FakeAssetBridge:
    def __init__(self):
        self.calls = []

    def action(self, name, ttl_ms=2600, source="P_2D", priority=3):
        self.calls.append((name, ttl_ms, source, priority))
        return True


class FakeEmotionBridge:
    def __init__(self):
        self.holds = []

    def hold_cards(self, seconds):
        self.holds.append(seconds)


class ActionWiringTests(unittest.TestCase):
    def setUp(self):
        self.ctl = main.Controller.__new__(main.Controller)
        self.ctl.emotion = DummyEmotion()
        self.ctl.asset_bridge = FakeAssetBridge()
        self.ctl.emotion_bridge = FakeEmotionBridge()
        self.ctl.beep = lambda key: None
        self.ctl._speak = lambda text, ms=2400, priority=0: None

    def test_user_action_sends_card_and_holds_emotion_cards(self):
        self.ctl.on_action("wave", duration_ms=3000, source="user")
        call = self.ctl.asset_bridge.calls[-1]
        self.assertEqual(call[0], "wave")
        self.assertEqual(call[1], 3400)
        self.assertEqual(call[3], main.asset_mod.P_ACTION)
        self.assertEqual(self.ctl.emotion_bridge.holds[-1], 3.4)

    def test_auto_action_uses_expression_priority(self):
        self.ctl.on_action("dance", duration_ms=3000, source="auto")
        call = self.ctl.asset_bridge.calls[-1]
        self.assertEqual(call[3], main.asset_mod.P_EXPRESSION)

    def test_change_is_silent_but_still_sends_card(self):
        self.ctl.on_action("change", duration_ms=3000, source="user")
        self.assertEqual(self.ctl.asset_bridge.calls[-1][0], "change")

    def test_non_card_action_does_not_send(self):
        self.ctl.on_action("run", duration_ms=3000, source="user")
        self.assertEqual(self.ctl.asset_bridge.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
