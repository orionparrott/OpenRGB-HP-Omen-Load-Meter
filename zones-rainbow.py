#!/usr/bin/env python3
"""Static per-zone rainbow: prove each HP Omen 30L zone is independently colorable."""
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

COLORS = [(255, 0, 0), (255, 110, 0), (255, 255, 0), (0, 255, 0),
          (0, 255, 255), (0, 80, 255), (160, 0, 255)]

client = OpenRGBClient("localhost", 6742, name="zones-rainbow")
dev = client.devices[0]
dev.set_mode("Direct")
for i, z in enumerate(dev.zones):
    r, g, b = COLORS[i % len(COLORS)]
    z.set_color(RGBColor(r, g, b))
    print(f"zone {i}: {z.name:20s} -> #{r:02X}{g:02X}{b:02X}")
