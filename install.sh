#!/usr/bin/env bash
# Set up the venv + systemd --user services for omen-load-meter.
# Assumes OpenRGB and its udev rules are already installed (see README).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/venv/bin/python"

echo "==> Creating venv + installing openrgb-python"
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" -q install --upgrade pip
"$DIR/venv/bin/pip" -q install openrgb-python

DEFAULT_OPENRGB="$(command -v openrgb || true)"
echo
read -rp "Command that launches OpenRGB [${DEFAULT_OPENRGB:-e.g. /path/to/OpenRGB.AppImage}]: " OPENRGB
OPENRGB="${OPENRGB:-$DEFAULT_OPENRGB}"
if [ -z "$OPENRGB" ]; then
  echo "!! No OpenRGB command given; edit ~/.config/systemd/user/openrgb-server.service later."
  OPENRGB="/path/to/OpenRGB.AppImage"
fi

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
sed "s|__OPENRGB__|$OPENRGB|g" "$DIR/systemd/openrgb-server.service" > "$UNIT_DIR/openrgb-server.service"
sed -e "s|__PY__|$PY|g" -e "s|__DIR__|$DIR|g" "$DIR/systemd/case-rgb-meter.service" > "$UNIT_DIR/case-rgb-meter.service"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
systemctl --user daemon-reload
systemctl --user enable --now openrgb-server.service case-rgb-meter.service

echo
echo "==> Installed and started. Verify:  systemctl --user status case-rgb-meter.service"
echo "    1) Map YOUR zones:  $PY $DIR/identify-zones.py   (and/or zones-rainbow.py)"
echo "    2) Edit ExecStart flags (--gpu-zones/--cpu-zones/--wave-zones) in:"
echo "       $UNIT_DIR/case-rgb-meter.service   then: systemctl --user restart case-rgb-meter.service"
echo "    (Make sure OpenRGB udev rules are installed so it runs without sudo — see README.)"
