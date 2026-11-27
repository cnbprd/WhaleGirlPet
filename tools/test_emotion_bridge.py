# -*- coding: utf-8 -*-
"""Unit tests for the v3.2 Python-side emotion bridge (stdlib only)."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import emotion_bridge as eb  # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class DummyState:
    def __init__(self, hint, mood):
        self._hint = hint
        self._mood = mood

    def expression_hint(self):
        return self._hint

    def mood_score(self):
        return self._mood


class BridgeTests(unittest.TestCase):
    def setUp(self):
        os.environ["WHALE3D_EMOTION_BRIDGE"] = "0"
        self.clock = FakeClock()
        self.bridge = eb.EmotionBridge(enabled=True, clock=self.clock)
        self.bridge.sender.enabled = False

    def tearDown(self):
        self.bridge.close()

    def test_priority_user_masks_auto(self):
        self.bridge.auto_state(DummyState("happy", 80))
        self.bridge.user_text("别难过，笑一个")
        self.assertEqual(self.bridge.arbiter.current().source, "P_USER")
        self.assertEqual(self.bridge.arbiter.current().emotion, "happy")

    def test_lower_priority_does_not_overwrite_user_until_expiry(self):
        self.bridge.user_text("笑一个")
        self.bridge.auto_state(DummyState("sleepy", 10))
        self.assertEqual(self.bridge.arbiter.current().source, "P_USER")
        self.clock.t += 9.0
        self.bridge.auto_state(DummyState("sleepy", 10))
        self.assertEqual(self.bridge.arbiter.current().source, "P_AUTO")
        self.assertEqual(self.bridge.arbiter.current().emotion, "tired")

    def test_llm_tag_and_strip(self):
        text = "好呀，我最喜欢你了。[[emo:happy:0.8]]"
        self.assertEqual(eb.parse_tag(text), ("happy", 0.8))
        self.assertEqual(eb.strip_tag(text), "好呀，我最喜欢你了。")
        self.bridge.llm_reply(text)
        self.assertEqual(self.bridge.last_emitted.source, "P_LLM")
        self.assertEqual(self.bridge.last_emitted.emotion, "happy")

    def test_unknown_tag_is_ignored(self):
        self.assertIsNone(eb.parse_tag("[[emo:nope:0.8]]"))
        self.assertEqual(eb.strip_tag("a[[emo:nope:0.8]]b"), "ab")

    def test_auto_mapping(self):
        self.bridge.auto_state(DummyState("sleepy", 20))
        self.assertEqual(self.bridge.last_emitted.emotion, "tired")
        self.assertGreaterEqual(self.bridge.last_emitted.intensity, 0.15)

    def test_unknown_render_emotion_rejected(self):
        self.assertIsNone(self.bridge._submit_and_emit("not-an-emotion", 0.5, "P_USER", 3, 8))

    def test_wire_payload_carries_intensity_curve(self):
        sig = eb.Signal("happy", 0.8, "P_LLM", 2, 4.0, self.clock())
        payload = eb.payload_for(sig)
        self.assertEqual(payload["curve"], {"attack_ms": 180, "release_ms": 420})
        self.assertEqual(payload["intensity"], 0.8)

    def test_emotion_signal_carries_2d_card(self):
        self.bridge.llm_reply("好呀。[[emo:happy:0.8]]")
        payload = eb.payload_for(self.bridge.last_emitted)
        self.assertEqual(payload["card"], "expression/happy")
        self.assertEqual(payload["card_ttl_ms"], 1800)

    def test_action_hold_suppresses_auto_card_until_expiry(self):
        self.bridge.hold_cards(3.0)
        self.bridge.llm_reply("好呀。[[emo:happy:0.8]]")
        payload = eb.payload_for(self.bridge.last_emitted)
        self.assertNotIn("card", payload)
        self.clock.t += 3.2
        self.bridge.user_text("气死我了")
        payload = eb.payload_for(self.bridge.last_emitted)
        self.assertEqual(payload["card"], "expression/angry")

    def test_tts_hold_keeps_llm_face_through_long_speech(self):
        self.bridge.llm_reply("好呀。[[emo:happy:0.8]]")
        self.clock.t += 5.0
        self.assertIsNone(self.bridge.arbiter.current())
        self.bridge.tts_active(True)
        self.assertEqual(self.bridge.arbiter.current().source, "P_LLM")
        self.clock.t += 20.0
        self.assertEqual(self.bridge.arbiter.current().source, "P_LLM")
        self.bridge.tts_active(False)
        self.clock.t += 5.0
        self.assertIsNone(self.bridge.arbiter.current())


if __name__ == "__main__":
    unittest.main(verbosity=2)
