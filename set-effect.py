#!/usr/bin/env python3
"""Set ONE built-in mode on the HP Omen 30L with a full palette + max speed.
Usage: set-effect.py "Color Cycle" [speed]
"""
import sys
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

PALETTE = [
    RGBColor(255, 0, 0),    # red
    RGBColor(255, 110, 0),  # orange
    RGBColor(255, 255, 0),  # yellow
    RGBColor(0, 255, 0),    # green
    RGBColor(0, 80, 255),   # blue
    RGBColor(160, 0, 255),  # purple
]

mode_name = sys.argv[1] if len(sys.argv) > 1 else "Color Cycle"
client = OpenRGBClient("localhost", 6742, name="set-effect")
dev = client.devices[0]
m = next((x for x in dev.modes if x.name.lower() == mode_name.lower()), None)
if m is None:
    print("modes:", [x.name for x in dev.modes]); sys.exit(1)

if m.speed_max is not None:
    m.speed = int(sys.argv[2]) if len(sys.argv) > 2 else m.speed_max
if m.colors_max:
    n = m.colors_max
    m.colors = (PALETTE * ((n // len(PALETTE)) + 1))[:n]

dev.set_mode(m)
print(f"set '{m.name}'  speed={getattr(m,'speed',None)}  "
      f"colors={len(m.colors) if m.colors else 0}")
