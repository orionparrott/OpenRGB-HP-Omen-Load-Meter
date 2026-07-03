# OpenRGB HP Omen Load Meter

Turn the case lighting on an **HP OMEN 30L** desktop into a live **GPU/CPU load meter** on
Linux, driven by [OpenRGB](https://openrgb.org). The front fan glows with GPU load, the
exhaust fan with CPU load (a smooth blue→red "cold→hot" thermal gradient), and the Omen logo
runs an animated color wave. Runs headless as a `systemd --user` service — no sudo, auto-starts
at login.

Built as a set of small, hackable Python scripts on top of the OpenRGB SDK. Should adapt to
other OpenRGB-supported gear with minor edits.

## What it does

- **Front intake fan → GPU utilization**, **top exhaust fan → CPU utilization.**
- **Thermal color scale:** 0% = cool blue → magenta → 100% = hot red (no Christmassy green/red
  clash). Other scales included (`green-red`, `cyan-magenta`, `amber-red`).
- **Omen logo → animated wave** (configurable color range + speed).
- **Temporally smoothed:** colors *ease* between values (exponential filter) instead of
  snapping, so spiky GPU load reads as a gentle glide, not flicker. Color is continuous 24-bit
  (not stepped levels).
- **One process owns all zones**, so nothing races over the device.

## Hardware

HP **OMEN 30L Desktop** (GT13-0xxx). The case lighting is the **"HP TracerLED"** controller
(USB `103c:84fd`), which recent OpenRGB supports as the **"HP Omen 30L"** device. NVIDIA GPU
assumed (`nvidia-smi`); swap `gpu_util()` for your GPU otherwise.

## ⚠️ The driver zone names lie — verify your hardware first

OpenRGB exposes **7 logical zones**, but their **names don't match the physical parts**, and
several may be **unpopulated/unplugged** on any given build. On the reference machine only 3 of
7 were wired, and the mapping was:

| Zone # | OpenRGB name    | Actually is           |
|--------|-----------------|-----------------------|
| 0      | Omen Logo       | Omen logo ✅          |
| 1      | Light Bar       | **top exhaust fan**   |
| 2      | Front Fan       | front intake fan ✅   |
| 3      | CPU Cooler      | *(not connected)*     |
| 4–6    | Front B/M/T Fan | *(not connected)*     |

**Do not trust the defaults blindly.** Use the mapping tools below to find which zone indices
drive which physical parts on *your* case, then set `--gpu-zones` / `--cpu-zones` /
`--wave-zones` accordingly.

## How it works

```
nvidia-smi + /proc/stat  ──►  case-rgb-meter.py  ──(OpenRGB SDK, localhost:6742)──►  OpenRGB server  ──►  /dev/hidraw0 (TracerLED)
        (load %)              (map load→color,                                       (headless, holds
                              ease, per-zone)                                         the device)
```

- `openrgb --server` runs headless and owns the HID device.
- `case-rgb-meter.py` (a [`openrgb-python`](https://github.com/jath03/openrgb-python) client)
  reads load, maps to colors, eases them, and pushes per-zone updates ~15×/sec.
- Two `systemd --user` services (`systemd/`) run the server + meter and auto-start at login.
- Access to `/dev/hidraw0` comes from OpenRGB's udev rule (`uaccess` / `plugdev`) — **no sudo
  at runtime.**

## Install

**Prerequisites**
1. **OpenRGB** (1.0rc3+ recommended for the Omen 30L driver) — the AppImage from
   [openrgb.org](https://openrgb.org) works well.
2. **Its udev rules** installed so you get non-root access to the controller:
   `sudo cp <openrgb>/usr/lib/udev/rules.d/60-openrgb.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger`
   (be in the `plugdev` group). See <https://openrgb.org/udev>.
3. **Python 3** and **`nvidia-smi`** (NVIDIA driver).

**Set up this project**
```bash
git clone <this-repo> ~/omen-load-meter && cd ~/omen-load-meter
./install.sh            # creates ./venv, installs openrgb-python, generates + enables services
```
`install.sh` will ask for the command that launches your OpenRGB server (e.g. the AppImage
path) and wire the two services to it. Then map your zones (below) and edit the meter service's
`--gpu-zones/--cpu-zones/--wave-zones` if your physical layout differs.

## Usage

All scripts talk to the running OpenRGB server on `localhost:6742`.

| Script | Purpose |
|---|---|
| `case-rgb-meter.py` | **The meter.** Load→color per zone + animated logo wave. Runs as the service. |
| `identify-zones.py` | Light each zone **alone**, looping, to see which physical part each drives. |
| `zones-rainbow.py`  | Light all zones a **distinct color at once** (map parts by color). |
| `zone-set.py`       | Set specific zones to colors, rest off. e.g. `zone-set.py 2:0000FF 3:FF0000`. |
| `set-effect.py`     | Apply a built-in hardware mode w/ full palette, e.g. `set-effect.py "Color Cycle"`. |
| `soft-wave.py`      | Host-driven rolling rainbow across zones (a real wave the hardware Wave mode can't do here). |

**Map your zones, then configure the meter:**
```bash
./venv/bin/python identify-zones.py     # watch which steps light up
./venv/bin/python zones-rainbow.py      # or: read each part's color
# then set the meter to YOUR mapping, e.g. the reference machine:
./venv/bin/python case-rgb-meter.py --gpu-zones 2 --cpu-zones 1 --wave-zones 0 --scale blue-red
```

## Configuration (`case-rgb-meter.py` flags)

| Flag | Default | Meaning |
|---|---|---|
| `--gpu-zones` | `2` | zone indices showing GPU load |
| `--cpu-zones` | `1` | zone indices showing CPU load |
| `--wave-zones`| `0` | zone indices running the animated wave |
| `--scale` | `blue-red` | `blue-red`, `green-red`, `cyan-magenta`, `amber-red` |
| `--wave-speed` | `0.66` | logo wave frequency (Hz) |
| `--smooth` | `0.6` | color easing time constant (s); higher = dreamier |
| `--interval` | `0.5` | seconds between load re-reads |
| `--mono` | off | drive all mapped zones from GPU load only |

Edit `wave_rgb()` to change the wave's colors (it's a plain HSV sweep).

## Service control

```bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user status  case-rgb-meter.service
systemctl --user restart case-rgb-meter.service   # after editing the script/flags
systemctl --user stop    case-rgb-meter.service    # to run an effect instead
```
For lighting to run **before login / when logged out**: `sudo loginctl enable-linger $USER`.

## Notes & gotchas

- **`pkill -f 'AppRun --server'` will match its own shell** and kill it — kill by PID instead.
- On this hardware the **Wave/Radial** built-in modes don't animate (only ~discrete zones); use
  `soft-wave.py` for a real wave. **Color Cycle** works.
- If the server ever starts with **0 devices**, restart it — detection can lose a startup race.

## Credits

- [OpenRGB](https://openrgb.org) by Adam Honse — device control + the Omen 30L driver.
- [openrgb-python](https://github.com/jath03/openrgb-python) — the SDK client.

## License

MIT — see [LICENSE](LICENSE).
