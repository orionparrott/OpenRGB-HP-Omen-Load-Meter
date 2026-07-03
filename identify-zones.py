#!/usr/bin/env python3
"""Light each HP Omen 30L zone ALONE, in a loop, to map logical zones -> physical parts."""
import time
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

HOLD = 5  # seconds each zone stays lit alone
dev = OpenRGBClient("localhost", 6742, name="identify-zones").devices[0]
dev.set_mode("Direct")
off = RGBColor(0, 0, 0)
white = RGBColor(255, 255, 255)

while True:
    for i, z in enumerate(dev.zones):
        for zz in dev.zones:
            zz.set_color(off)
        z.set_color(white)
        print(f"[{i}] {z.name}", flush=True)
        time.sleep(HOLD)
