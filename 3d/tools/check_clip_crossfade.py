from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_cards_visible as qa

def key(hwnd: int, down: bool):
    qa.user32.PostMessageW(hwnd, 0x0100 if down else 0x0101, 0x57, 0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=str(Path("3d/whale3d-stage2-crossfade.exe")))
    parser.add_argument("--out-dir", default=str(Path("build/stage2-crossfade")))
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = out / "crossfade.log"
    result_path = out / "crossfade-result.json"
    if log.exists(): log.unlink()
    proc = None
    try:
        proc = qa.launch_3d(exe, log)
        hwnd = qa.wait_for_window(proc.pid, 12.0)
        if not qa.wait_log(log, "AnimationController ready", 8.0):
            raise RuntimeError("controller not ready")
        key(hwnd, True); key(hwnd, False)
        forward = qa.wait_log(log, "clip fade: idle -> walk", 3.0)
        time.sleep(0.45)
        key(hwnd, True); key(hwnd, False)
        backward = qa.wait_log(log, "clip fade: walk -> idle", 3.0)
        result = {"ok": bool(forward and backward), "hwnd": int(hwnd), "pid": proc.pid,
                  "forward_fade": forward, "backward_fade": backward, "log": str(log)}
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    finally:
        qa.stop_process(proc)

if __name__ == "__main__":
    raise SystemExit(main())
