# -*- coding: utf-8 -*-
"""Unit tests for the 2D->3D asset protocol (stdlib only)."""
import json
import socket
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import asset_bridge as ab  # noqa: E402


class AssetBridgeTests(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.settimeout(1.0)
        self.port = self.listener.getsockname()[1]
        self.bridge = ab.AssetBridge(port=self.port, enabled=True)

    def tearDown(self):
        self.bridge.close()
        self.listener.close()

    def _recv(self):
        data, _ = self.listener.recvfrom(4096)
        return json.loads(data.decode("utf-8"))

    def test_manifest_has_17_cards_and_valid_bounds(self):
        self.assertEqual(len(self.bridge.cards), 17)
        sheet_w, sheet_h = 1024, 512
        for card in self.bridge.cards.values():
            x, y, w, h = card.rect
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, sheet_w)
            self.assertLessEqual(y + h, sheet_h)

    def test_expression_packet(self):
        self.assertTrue(self.bridge.expression("happy", ttl_ms=1800))
        payload = self._recv()
        self.assertEqual(payload["card"], "expression/happy")
        self.assertEqual(payload["card_ttl_ms"], 1800)
        self.assertEqual(payload["emotion"], "happy")
        self.assertEqual(payload["source"], "P_2D")

    def test_action_packet_is_neutral_emotion(self):
        self.assertTrue(self.bridge.action("wave", ttl_ms=2600))
        payload = self._recv()
        self.assertEqual(payload["card"], "action/wave")
        self.assertEqual(payload["card_ttl_ms"], 2600)
        self.assertEqual(payload["emotion"], "neutral")

    def test_unknown_card_rejected_without_packet(self):
        self.assertFalse(self.bridge.send_card("expression/not-real"))
        self.listener.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            self.listener.recvfrom(4096)

    def test_ttl_is_clamped(self):
        self.assertTrue(self.bridge.send_card("expression/idle", ttl_ms=10))
        payload = self._recv()
        self.assertEqual(payload["card_ttl_ms"], 200)
        self.assertTrue(self.bridge.send_card("expression/idle", ttl_ms=99999))
        payload = self._recv()
        self.assertEqual(payload["card_ttl_ms"], 10000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
