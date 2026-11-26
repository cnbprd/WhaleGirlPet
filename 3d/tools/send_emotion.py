#!/usr/bin/env python3
"""Send one v3.2 emotion frame to the local WhaleGirl 3D process.

Usage:
    python 3d/tools/send_emotion.py happy 0.8
    python 3d/tools/send_emotion.py sad 0.6 --source llm
    python 3d/tools/send_emotion.py neutral 0 --port 47832
"""
from __future__ import annotations

import argparse
import json
import socket


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("emotion", help="happy / curious / neutral / sad / angry ...")
    parser.add_argument("intensity", nargs="?", type=float, default=1.0)
    parser.add_argument("--source", default="manual")
    parser.add_argument("--port", type=int, default=47832)
    args = parser.parse_args()

    payload = {
        "emotion": args.emotion,
        "intensity": max(0.0, min(1.0, args.intensity)),
        "source": args.source,
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ("127.0.0.1", args.port),
        )
    finally:
        sock.close()
    print(f"sent {payload} -> udp://127.0.0.1:{args.port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
