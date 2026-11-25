# -*- coding: utf-8 -*-
"""② 音频输入探针：Gemma 4 E2B 的 mmproj 到底收不收 audio。

对同一个 wav，试三种 OpenAI 风格写法，看服务端认哪一种、还是压根不支持。
用法：python tools/probe_audio.py
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MDIR = os.path.join(ROOT, "runtime", "models")
EXE = os.path.join(ROOT, "runtime", "dafeiyu", "dafeiyu-server.exe")
MODEL = os.path.join(MDIR, "gemma4-e2b-it.gguf")
MMPROJ = os.path.join(MDIR, "mmproj-gemma4-e2b-f16.gguf")
WAV = r"F:\WhaleGirlPetApp\accounts\default\tts_cache\_verify_16k.wav"
PORT = 11598


def short_wav(seconds=2.5):
    """截前 N 秒，16k 单声道 → base64（太长会被拒/太慢）。"""
    with wave.open(WAV, "rb") as w:
        n = min(w.getnframes(), int(w.getframerate() * seconds))
        frames = w.readframes(n)
    out = os.path.join(ROOT, "build", "probe_audio.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(frames)
    with open(out, "rb") as f:
        raw = f.read()
    return base64.b64encode(raw).decode("ascii"), len(raw)


def wait_health(t=90):
    for _ in range(int(t * 2)):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
                if (json.loads(r.read().decode()) or {}).get("status") in ("ok", "no slot available"):
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def post(part, text="这段音频里说了什么？"):
    body = {"model": "local", "stream": False, "max_tokens": 120, "temperature": 0.1,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": text}, part]}]}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode("utf-8"))
        msg = (d.get("choices") or [{}])[0].get("message", {})
        return True, time.perf_counter() - t0, (msg.get("content") or "")[:200]
    except urllib.error.HTTPError as e:
        return False, time.perf_counter() - t0, f"{e.code} " + (e.read() or b"")[:200].decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return False, time.perf_counter() - t0, str(e)[:200]


def main():
    b64, n = short_wav()
    print(f"wav 2.5s，raw {n/1024:.0f}KB，base64 {len(b64)/1024:.0f}KB")

    log = open(os.path.join(ROOT, "runtime", "probe_audio.log"), "ab")
    p = subprocess.Popen([EXE, "-m", MODEL, "-c", "4096", "-np", "1", "-rea", "off",
                          "--port", str(PORT), "--host", "127.0.0.1",
                          "--mmproj", MMPROJ, "-mmdev", "none"],
                         stdout=log, stderr=subprocess.STDOUT,
                         creationflags=0x08000000 if os.name == "nt" else 0)
    try:
        if not wait_health():
            print("引擎没起来")
            return
        m = None
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=8) as r:
                d = json.loads(r.read().decode("utf-8"))
            m = (d.get("data") or [{}])[0].get("architecture")
            print("architecture:", m)
        except Exception as e:  # noqa: BLE001
            print("查 modalities 失败:", e)

        cases = [
            ("A input_audio(data/format)", {"type": "input_audio",
                                            "input_audio": {"data": b64, "format": "wav"}}),
            ("B audio_url(data url)", {"type": "audio_url",
                                       "audio_url": {"url": "data:audio/wav;base64," + b64}}),
            ("C input_audio(string)", {"type": "input_audio", "input_audio": b64}),
        ]
        for name, part in cases:
            ok, dt, out = post(part)
            print(f"{name}: ok={ok} {dt:.1f}s -> {out!r}")
            time.sleep(0.4)
    finally:
        p.terminate()
        try:
            p.wait(timeout=8)
        except Exception:
            p.kill()
        log.close()


if __name__ == "__main__":
    main()
