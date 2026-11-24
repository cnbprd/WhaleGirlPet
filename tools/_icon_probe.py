# -*- coding: utf-8 -*-
from PIL import Image

for p in ["assets/ui/pet_flat.ico", "assets/ui/pet.ico",
          "assets/ui/pet_flat_256.png", "assets/ui/avatar.png", "assets/ui/qwhale.png"]:
    im = Image.open(p)
    rgba = im.convert("RGBA")
    a = rgba.getchannel("A")
    w, h = rgba.size
    cnt = sum(1 for v in a.getdata() if v > 20)
    print("%-28s %-10s %-6s body=%-22s fill=%.2f" % (p, "%dx%d" % (w, h), im.mode, str(a.getbbox()), cnt / (w * h)))
