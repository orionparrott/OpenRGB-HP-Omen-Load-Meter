#!/usr/bin/env python3
"""Set specific HP Omen 30L zones to colors, all others OFF.
Usage: zone-set.py 2:0000FF 3:FF0000   (zone index : RRGGBB)
"""
import sys
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

spec = {}
for a in sys.argv[1:]:
    z, hexc = a.split(":")
    spec[int(z)] = hexc

dev = OpenRGBClient("localhost", 6742, name="zone-set").devices[0]
dev.set_mode("Direct")
for i, z in enumerate(dev.zones):
    h = spec.get(i, "000000")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    z.set_color(RGBColor(r, g, b))
    print(f"zone {i}: {z.name:20s} -> #{h.upper()}")
