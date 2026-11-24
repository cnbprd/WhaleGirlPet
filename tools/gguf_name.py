# -*- coding: utf-8 -*-
"""读 GGUF 头部关键元信息（architecture / name / quantization），用于给无名 blob 命名。"""
import struct
import sys


def rd(f, fmt):
    n = struct.calcsize(fmt)
    return struct.unpack(fmt, f.read(n))


def rstr(f):
    (ln,) = rd(f, "<Q")
    return f.read(ln).decode("utf-8", "replace")


def skip_val(f, t):
    if t == 0:
        f.read(1)
    elif t == 1:
        f.read(1)
    elif t == 2:
        f.read(2)
    elif t == 3:
        f.read(2)
    elif t == 4:
        f.read(4)
    elif t == 5:
        f.read(4)
    elif t == 6:
        f.read(4)
    elif t == 7:
        f.read(1)
    elif t == 8:
        rstr(f)
    elif t == 9:
        (at, n) = rd(f, "<I")
        nt, = rd(f, "<I") if False else rd(f, "<I")
        del at, nt
        # 上面写法容易出错，改为标准读法
    elif t == 10:
        pass


def main(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"GGUF":
            print("not gguf:", magic)
            return
        ver, = rd(f, "<I")
        n_tensors, = rd(f, "<Q")
        n_kv, = rd(f, "<Q")
        print(f"version={ver} tensors={n_tensors} kv={n_kv}")
        want = {"general.architecture", "general.name", "general.size_label",
                "general.parameter_count", "general.file_type",
                "general.quantization_version", "tokenizer.ggml.model"}
        for _ in range(min(n_kv, 40)):
            key = rstr(f)
            (t,) = rd(f, "<I")
            if t == 4:
                val = rd(f, "<I")[0]
            elif t == 5:
                val = rd(f, "<i")[0]
            elif t == 6:
                val = rd(f, "<f")[0]
            elif t == 7:
                val = bool(f.read(1)[0])
            elif t == 8:
                val = rstr(f)
            elif t == 9:
                (at,) = rd(f, "<I")
                cnt, = rd(f, "<Q")
                vals = []
                for _ in range(min(cnt, 20)):
                    vals.append(rstr(f) if at == 8 else str(rd(f, "<I")[0]))
                val = vals
            elif t == 10:
                (at,) = rd(f, "<I")
                cnt, = rd(f, "<Q")
                if at == 8:
                    for _ in range(cnt):
                        rstr(f)
                elif at == 6:
                    f.read(4 * cnt)
                elif at == 5:
                    f.read(4 * cnt)
                elif at == 4:
                    f.read(4 * cnt)
                elif at == 7:
                    f.read(cnt)
                val = f"array({at},{cnt})"
            elif t == 0:
                val = f.read(1)[0]
            elif t == 1:
                val = f.read(1)[0]
            elif t == 2:
                val = rd(f, "<H")[0]
            elif t == 3:
                val = rd(f, "<h")[0]
            else:
                print("unknown kv type", t, "key", key)
                return
            if key in want:
                print(f"  {key} = {val}")


if __name__ == "__main__":
    main(sys.argv[1])
