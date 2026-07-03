#!/usr/bin/env python3
"""Case lighting for the HP Omen 30L via OpenRGB: load meter + animated logo.

Confirmed physical map (2026-07-02): zone 0 = Omen logo, zone 1 = top exhaust fan,
zone 2 = front intake fan. Zones 3-6 not connected on this build.

Default: logo(0) = teal->blue wave; front intake(2) = GPU load; exhaust(1) = CPU load.
--scale picks the load gradient (0% -> 100%):
  green-red     : green -> yellow -> orange -> red   (classic, but Christmassy w/ green)
  blue-red      : blue  -> magenta -> red            (thermal "cold->hot", no green)
  cyan-magenta  : cyan  -> blue -> magenta           (cool techy)
  amber-red     : amber -> orange -> red             (warm)
One process owns all zones so nothing fights. Fast frame loop for the wave; load
re-read once per --interval.
"""
import argparse
import colorsys
import math
import subprocess
import sys
import time

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

# (hue_at_0pct, hue_at_100pct) in degrees; interpolated the short/explicit way below
SCALES = {
    "green-red": (120.0, 0.0),      # 120 -> 0
    "blue-red": (240.0, 360.0),     # 240 -> 360(=0 red) through 300 magenta, no green
    "cyan-magenta": (180.0, 300.0), # 180 -> 300
    "amber-red": (45.0, 0.0),       # 45 -> 0
}


def gpu_util():
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=utilization.gpu",
         "--format=csv,noheader,nounits"], text=True)
    vals = [int(x) for x in out.split() if x.strip().isdigit()]
    return max(0, min(100, max(vals))) if vals else 0


def read_cpu():
    with open("/proc/stat") as f:
        v = list(map(int, f.readline().split()[1:]))
    idle = v[3] + (v[4] if len(v) > 4 else 0)
    return sum(v), idle


def load_rgb(u, scale):
    h0, h1 = SCALES.get(scale, SCALES["green-red"])
    hue = (h0 + (h1 - h0) * (u / 100.0)) % 360.0 / 360.0
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return RGBColor(int(r * 255), int(g * 255), int(b * 255))


def wave_rgb(t, speed, bias=3.0):
    """Wave: blue-anchored with a brief pink 'activation'. bias>1 dwells on blue
    (pink becomes a short peak); bias=1 is a symmetric 50/50 sweep."""
    phase = 0.5 * (1.0 + math.sin(2.0 * math.pi * t * speed))  # 0..1 symmetric
    phase = phase ** bias               # >1 -> more time near blue, brief pink peaks
    hue = 0.57 + 0.35 * phase           # 0.57 light blue .. 0.92 pink (via violet)
    sat = 0.55                          # pastel
    val = 0.85 + 0.15 * phase
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return RGBColor(int(r * 255), int(g * 255), int(b * 255))


def parse_zones(s):
    return [int(x) for x in s.split(",") if x.strip() != ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=6742)
    ap.add_argument("--interval", type=float, default=0.5, help="GPU/CPU re-read seconds")
    ap.add_argument("--smooth", type=float, default=0.6,
                    help="color easing time constant in seconds (bigger = smoother/slower)")
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--gpu-zones", default="2")
    ap.add_argument("--cpu-zones", default="1")
    ap.add_argument("--wave-zones", default="0")
    ap.add_argument("--wave-speed", type=float, default=0.5)
    ap.add_argument("--wave-bias", type=float, default=3.0,
                    help="wave duty bias; >1 dwells on the blue end, brief pink peak (1=50/50)")
    ap.add_argument("--scale", default="blue-red", choices=list(SCALES))
    ap.add_argument("--fps", type=float, default=15.0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    gpu_zones = parse_zones(args.gpu_zones)
    cpu_zones = parse_zones(args.cpu_zones)
    wave_zones = parse_zones(args.wave_zones)

    client = OpenRGBClient(args.host, args.port, name="case-meter")
    dev = client.devices[args.device]
    try:
        dev.set_mode("Direct")
    except Exception:
        pass

    def setz(i, col):
        if 0 <= i < len(dev.zones):
            dev.zones[i].set_color(col)

    prev_total, prev_idle = read_cpu()
    tgt_gpu = tgt_cpu = 0.0     # latest measured %
    disp_gpu = disp_cpu = 0.0   # smoothed % actually shown
    t0 = time.time()
    last_read = -1e9
    frame_dt = 1.0 / args.fps
    tau = max(1e-3, args.smooth)

    while True:
        now = time.time() - t0
        if now - last_read >= args.interval:
            try:
                tgt_gpu = float(gpu_util())
                total, idle = read_cpu()
                dt, di = total - prev_total, idle - prev_idle
                prev_total, prev_idle = total, idle
                tgt_cpu = max(0.0, min(100.0, 100.0 * (dt - di) / dt)) if dt > 0 else 0.0
                print(f"[{args.scale}] GPU {tgt_gpu:5.1f}% -> z{gpu_zones}   "
                      f"CPU {tgt_cpu:5.1f}% -> z{cpu_zones}   wave z{wave_zones}", flush=True)
            except Exception as e:
                sys.stderr.write(f"read error: {e}\n")
            last_read = now

        # exponential ease toward the measured values every frame -> smooth glide
        alpha = 1.0 - math.exp(-frame_dt / tau)
        disp_gpu += (tgt_gpu - disp_gpu) * alpha
        disp_cpu += (tgt_cpu - disp_cpu) * alpha

        gpu_col = load_rgb(disp_gpu, args.scale)
        cpu_col = load_rgb(disp_cpu, args.scale)
        wcol = wave_rgb(now, args.wave_speed, args.wave_bias)
        try:
            for i in wave_zones:
                setz(i, wcol)
            for i in gpu_zones:
                setz(i, gpu_col)
            for i in cpu_zones:
                setz(i, cpu_col)
        except Exception as e:
            sys.stderr.write(f"set error: {e}\n")

        if args.once:
            break
        time.sleep(frame_dt)


if __name__ == "__main__":
    main()
