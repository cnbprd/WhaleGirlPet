# -*- coding: utf-8 -*-
"""Fuzz the C++ UDP emotion/card parser without opening a 3D window.

The probe only links emotion_bus.cpp (no SDL, no OpenGL).  We send malformed
datagrams followed by one valid card packet; success means the process stayed
alive and still parsed the valid packet.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
EXE = BUILD / "emotion_bus_probe_fuzz.exe"
OUT = ROOT / "docs/protocol-fuzz.json"


def free_udp_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def find_gxx() -> Path:
    for p in (ROOT / ".toolchains/w64devkit").rglob("g++.exe"):
        return p
    raise FileNotFoundError("g++.exe not found under .toolchains/w64devkit")


def build_probe() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    gxx = find_gxx()
    cmd = [
        str(gxx), "-std=c++17", "-O2", "-I3d",
        "3d/emotion_bus.cpp", "3d/tools/emotion_bus_probe.cpp",
        "-lws2_32", "-o", str(EXE),
    ]
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError("probe build failed")


CASES = [
    ("empty_object", b"{}"),
    ("truncated_emotion", b'{"emotion":'),
    ("empty_emotion", b'{"emotion":""}'),
    ("unclosed_object", b'{"emotion":"happy"'),
    ("nan_intensity", b'{"emotion":"happy","intensity":NaN}'),
    ("inf_intensity", b'{"emotion":"happy","intensity":1e999}'),
    ("string_intensity", b'{"emotion":"happy","intensity":"loud"}'),
    ("negative_ttl", b'{"emotion":"happy","card_ttl_ms":-50}'),
    ("huge_ttl", b'{"emotion":"happy","card_ttl_ms":999999}'),
    ("path_card", b'{"emotion":"happy","card":"expression/../../etc/passwd"}'),
    ("unclosed_gaze", b'{"emotion":"happy","gaze":{"x":0.2,"y":0.3'),
    ("nan_gaze", b'{"emotion":"happy","gaze":{"x":NaN,"y":1e999,"weight":-1}}'),
    ("duplicate_keys", b'{"emotion":"happy","emotion":"angry","intensity":0.5}'),
    ("non_utf8", b'{"emotion":"happy","source":"\xff\xfe"}'),
    ("long_card", b'{"emotion":"happy","card":"' + b"x" * 600 + b'"}'),
    ("long_junk", b"A" * 700),
]


def main() -> int:
    build_probe()
    port = free_udp_port()
    proc = subprocess.Popen(
        [str(EXE), "--port", str(port), "--seconds", "2.5"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace",
    )
    time.sleep(0.35)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = []
    for name, payload in CASES:
        sock.sendto(payload, ("127.0.0.1", port))
        sent.append({"case": name, "bytes": len(payload)})
        time.sleep(0.015)
    valid = b'{"emotion":"neutral","card":"action/wave","card_ttl_ms":2600,"source":"fuzz"}'
    for _ in range(3):
        sock.sendto(valid, ("127.0.0.1", port))
        time.sleep(0.02)
    sock.close()
    out, err = proc.communicate(timeout=8)
    ok = (proc.returncode == 0 and "ready" in out and
          "valid emotion=neutral card=action/wave ttl=2600 source=fuzz" in out)
    summary = {
        "probe": str(EXE.relative_to(ROOT)),
        "port": port,
        "cases": sent,
        "valid_packet": valid.decode("utf-8"),
        "returncode": proc.returncode,
        "stdout": out,
        "stderr": err,
        "ok": ok,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"cases={len(CASES)} returncode={proc.returncode} ok={ok}")
    print(out.strip())
    if err.strip():
        print("stderr:", err.strip(), file=sys.stderr)
    print(f"json={OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
