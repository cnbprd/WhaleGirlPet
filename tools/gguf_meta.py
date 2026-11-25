# -*- coding: utf-8 -*-
"""读 GGUF 头部元数据（不依赖 gguf 库），用来判断模型架构与是否带视觉/音频端口。"""
import struct
import sys

T_STR, T_ARR = 8, 9


def _rd(f, n):
    return f.read(n)


def _u32(f):
    return struct.unpack("<I", _rd(f, 4))[0]


def _u64(f):
    return struct.unpack("<Q", _rd(f, 8))[0]


def _s(f):
    n = _u64(f)
    return _rd(f, n).decode("utf-8", "replace")


def val(f, t):
    if t == 0:
        return _rd(f, 1)[0]
    if t == 1:
        return struct.unpack("<b", _rd(f, 1))[0]
    if t == 2:
        return struct.unpack("<H", _rd(f, 2))[0]
    if t == 3:
        return struct.unpack("<h", _rd(f, 2))[0]
    if t == 4:
        return _u32(f)
    if t == 5:
        return struct.unpack("<i", _rd(f, 4))[0]
    if t == 6:
        return struct.unpack("<f", _rd(f, 4))[0]
    if t == 7:
        return _rd(f, 1)[0]
    if t == T_STR:
        return _s(f)
    if t == 10:
        return _u64(f)
    if t == 11:
        return struct.unpack("<q", _rd(f, 8))[0]
    if t == 12:
        return struct.unpack("<d", _rd(f, 8))[0]
    if t == T_ARR:
        at = _u32(f)
        n = _u64(f)
        out = []
        for _ in range(min(n, 4)):
            out.append(val(f, at))
        return out if n <= 4 else out + [f"...({n} items)"]
    raise ValueError(f"unknown type {t}")


def main(path, only_keys=None):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"GGUF":
            print("不是 GGUF:", magic)
            return
        ver = struct.unpack("<I", f.read(4))[0]
        n_tensor = struct.unpack("<Q", f.read(8))[0]
        n_kv = struct.unpack("<Q", f.read(8))[0]
        print(f"file      {path}")
        print(f"gguf v{ver}  tensors={n_tensor}  kv={n_kv}")
        keys = {}
        for _ in range(n_kv):
            k = None
            try:
                k = _s(f)
                t = _u32(f)
                keys[k] = val(f, t)
            except Exception as e:  # noqa: BLE001
                print(f"  解析中断于 {k}: {e}")
                break
        for k in sorted(keys):
            sv = str(keys[k])
            if len(sv) > 110:
                sv = sv[:110] + "…"
            print(f"  {k} = {sv}")
        hits = [k for k in keys if any(w in k.lower() for w in
                                        ("vision", "mmproj", "image", "audio", "clip", "projector"))]
        print("端口线索:", hits or "无（纯文本权重）")


if __name__ == "__main__":
    main(sys.argv[1])
