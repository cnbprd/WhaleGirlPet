# -*- coding: utf-8 -*-
"""Mock 3D emotion/card receiver for 2D-side protocol tests.

Listens on localhost UDP and prints the decoded packets.  It does not render,
does not touch the real 3D executable, and defaults to port 47833 so the 24h
soak on 47832 is not disturbed.
"""
from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=47833)
    parser.add_argument("--seconds", type=float, default=0.0,
                        help="0 means run until Ctrl+C")
    parser.add_argument("--once", action="store_true",
                        help="exit after the first packet containing a card")
    parser.add_argument("--card-only", action="store_true")
    parser.add_argument("--jsonl", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", args.port))
    sock.settimeout(0.5)
    print(f"listening udp://127.0.0.1:{args.port}", flush=True)

    out = Path(args.jsonl) if args.jsonl else None
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    count = 0
    card_count = 0
    while True:
        if args.seconds > 0 and time.monotonic() - started >= args.seconds:
            break
        try:
            data, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break
        try:
            payload = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"bad packet bytes={len(data)} error={type(exc).__name__}", flush=True)
            continue
        card = str(payload.get("card") or "")
        if args.card_only and not card:
            continue
        count += 1
        if card:
            card_count += 1
        print(
            f"emotion={payload.get('emotion')} intensity={payload.get('intensity')} "
            f"source={payload.get('source')} card={card or '-'} "
            f"card_ttl_ms={payload.get('card_ttl_ms')}",
            flush=True,
        )
        if out is not None:
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        if args.once and card:
            break
    sock.close()
    print(f"packets={count} cards={card_count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
