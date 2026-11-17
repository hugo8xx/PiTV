#!/bin/bash
# Prepare a freshly flashed Raspberry Pi OS Lite (32-bit, Trixie) SD card for PiTV. macOS.
#
#   1. Flash the card with Raspberry Pi Imager (no customisation) and leave it in the Mac.
#   2. boot/prepare-sd.sh            (uses pitv.env; bootfs must be mounted)
#   3. Type your Wi-Fi password where it asks (nano opens network-config on the card).
#   4. Eject, put the card in the Pi, power on. It reboots once; then: ./install.sh
set -euo pipefail
. "$(dirname "$0")/../lib/env.sh"
B="${1:-/Volumes/bootfs}"
[ -f "$B/cmdline.txt" ] || { echo "No Raspberry Pi boot partition at $B (is the card mounted?)"; exit 1; }

KEY_FILE="${PITV_SSH_KEY:-}"
[ -z "$KEY_FILE" ] && for k in ~/.ssh/id_ed25519.pub ~/.ssh/id_rsa.pub; do [ -f "$k" ] && KEY_FILE=$k && break; done
[ -n "$KEY_FILE" ] || { echo "No SSH public key found. Create one: ssh-keygen -t ed25519"; exit 1; }

cd "$PITV_ROOT/boot"
sed -e "s|__HOSTNAME__|$PITV_HOSTNAME|" -e "s|__TIMEZONE__|$PITV_TIMEZONE|" \
    -e "s|__SSH_KEY__|$(cat "$KEY_FILE")|" user-data > "$B/user-data"
sed -e "s|__SSID__|$PITV_WIFI_SSID|" -e "s|__COUNTRY__|$PITV_WIFI_COUNTRY|" network-config > "$B/network-config"
cp pitv-firstboot.sh "$B/pitv-firstboot.sh"
touch "$B/ssh"
if ! grep -q pitv-firstboot "$B/cmdline.txt"; then
  printf '%s systemd.run=/boot/firmware/pitv-firstboot.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target\n' \
    "$(tr -d '\n' < "$B/cmdline.txt")" > "$B/cmdline.txt"
fi
echo "Card prepared: hostname $PITV_HOSTNAME, Wi-Fi \"$PITV_WIFI_SSID\", SSH key $(basename "$KEY_FILE")."

if [ -n "$PITV_WIFI_SSID" ] && [ "${PITV_SKIP_WIFI:-}" != 1 ]; then
  echo
  echo "Now type your Wi-Fi password: replace PASSWORD_HERE (keep the quotes)."
  echo "Save with Ctrl+O, Enter, then Ctrl+X."
  read -r -p "Press Enter to open the editor... " _
  nano "$B/network-config"
  if grep -q PASSWORD_HERE "$B/network-config"; then
    echo "WARNING: password not set; the Pi will only work over Ethernet."
  fi
fi
ssh-keygen -R "$PITV_HOSTNAME.local" >/dev/null 2>&1 || true
diskutil eject "$B" >/dev/null && echo "Ejected. Put the card in the Pi and power it on."
