#!/usr/bin/env python3
"""Host-driven 'wave': roll a rainbow across the HP Omen 30L's 7 zones.
Does what the hardware Wave mode fails to do, using per-zone Direct control."""
import argparse
import colorsys
import time

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

ap = argparse.ArgumentParser()
ap.add_argument("--speed", type=float, default=0.20, help="hue cycles per second")
ap.add_argument("--spread", type=float, default=1.0, help="hue span across the zones")
ap.add_argument("--fps", type=float, default=20.0)
ap.add_argument("--duration", type=float, default=0.0, help="seconds; 0 = forever")
args = ap.parse_args()

dev = OpenRGBClient("localhost", 6742, name="soft-wave").devices[0]
dev.set_mode("Direct")
n = max(1, len(dev.zones))
dt = 1.0 / args.fps
t0 = time.time()
while True:
    now = time.time() - t0
    for i, z in enumerate(dev.zones):
        h = ((i / n) * args.spread + now * args.speed) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
        z.set_color(RGBColor(int(r * 255), int(g * 255), int(b * 255)))
    if args.duration and now >= args.duration:
        break
    time.sleep(dt)
