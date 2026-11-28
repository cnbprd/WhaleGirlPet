#!/usr/bin/env python3
"""Stage 2 QA: same-batch emotion frames + deferred card queue."""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_cards_visible as qa  # noqa: E402

ROOT = qa.ROOT
UDP_PORT = qa.UDP_PORT


def send_payload(card: str, ttl_ms: int, source: str, emotion: str = "happy") -> None:
    payload = {
        "emotion": emotion,
        "intensity": 0.8,
        "source": source,
        "card": card,
        "card_ttl_ms": ttl_ms,
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(json.dumps(payload).encode("utf-8"), ("127.0.0.1", UDP_PORT))
    finally:
        sock.close()


def main() -> int:
    exe = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "whale3d-stage2-queue.exe"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parent / "build" / "stage2-queue"
    out_dir.mkdir(parents=True, exist_ok=True)

    existing = qa.any_whale3d()
    if existing:
        raise RuntimeError(f"whale3d already running: {existing}")

    log_path = out_dir / "queue-test.log"
    proc = None
    checks: list[dict[str, object]] = []
    try:
        proc = qa.launch_3d(exe, log_path)
        hwnd = qa.wait_for_window(proc.pid, 12.0)
        if not qa.wait_log(log_path, "Sprite layer: ready", 8.0):
            raise RuntimeError("sprite layer not ready")

        # A: same-poll batch. The old poll() kept only the last frame; pollAll
        # should log both and show both before the second replaces the first.
        send_payload("expression/shy", 1200, "batch-a")
        send_payload("expression/angry", 1200, "batch-b")
        batch = qa.wait_log(log_path, "Emotion batch: 2 frames", 2.5)
        checks.append({"check": "poll_all_batch", "pass": batch})
        if not qa.wait_log(log_path, "Sprite card: expression/angry", 2.5):
            raise RuntimeError("batch second card not shown")
        time.sleep(1.5)

        # B: action first, then a lower-priority expression. The expression
        # must queue, not be discarded.
        send_payload("action/wave", 3000, "queue-action", emotion="happy")
        if not qa.wait_log(log_path, "Sprite card: action/wave", 2.5):
            raise RuntimeError("action wave not shown")
        send_payload("expression/happy", 1200, "queue-expression", emotion="happy")
        queued = qa.wait_log(log_path, "anim card queued: card=expression/happy", 1.5)
        checks.append({"check": "expression_queued", "pass": queued})
        if not queued:
            raise RuntimeError("expression was not queued")

        # Action TTL is 3s; queued expression should appear right after it.
        after_action = qa.wait_log(log_path, "Sprite card queued: expression/happy", 4.0)
        checks.append({"check": "queued_card_after_action", "pass": after_action})
        if not after_action:
            raise RuntimeError("queued expression did not appear after action")
        time.sleep(0.25)
        image = qa.capture_client(hwnd, out_dir / "queue_after_action.png")
        card_x, card_y, card_w, card_h = qa.card_rect(
            "expression/happy", image.width, image.height
        )
        image.crop((card_x, card_y, card_x + card_w, card_y + card_h)).save(
            out_dir / "queue_after_action_crop.png"
        )

        # The popped card's own 1.2s TTL is verified separately in
        # build/check_expiry.py; the source log may not emit a fresh idle line
        # when requestCardState(update(0)) replaces the state in the same frame.
        time.sleep(1.5)
        qa.capture_client(hwnd, out_dir / "queue_after_expiry.png")

        # C: two distinct low-priority cards queue FIFO behind one action.
        send_payload("action/dance", 2500, "multi-action", emotion="happy")
        if not qa.wait_log(log_path, "Sprite card: action/dance", 2.5):
            raise RuntimeError("action dance not shown")
        send_payload("expression/curious", 1200, "multi-1")
        send_payload("expression/pat", 1200, "multi-2")
        two_queued = qa.wait_log(
            log_path,
            "anim card queued: card=expression/pat state=expression_pat",
            2.0,
        )
        checks.append({"check": "two_cards_queued", "pass": two_queued})
        if not two_queued:
            raise RuntimeError("second expression was not queued")
        first = qa.wait_log(log_path, "Sprite card queued: expression/curious", 3.5)
        checks.append({"check": "multi_first_after_action", "pass": first})
        if not first:
            raise RuntimeError("first queued expression did not appear")
        second = qa.wait_log(log_path, "Sprite card queued: expression/pat", 2.0)
        checks.append({"check": "multi_second_after_first", "pass": second})
        if not second:
            raise RuntimeError("second queued expression did not appear")
        time.sleep(1.5)

        result = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "exe": str(exe),
            "hwnd": int(hwnd),
            "pid": proc.pid,
            "log": str(log_path),
            "checks": checks,
            "screenshots": {
                "after_action": str(out_dir / "queue_after_action.png"),
                "after_expiry": str(out_dir / "queue_after_expiry.png"),
            },
        }
        (out_dir / "queue-test.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if all(bool(item["pass"]) for item in checks) else 1
    finally:
        qa.stop_process(proc)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
