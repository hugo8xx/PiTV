#!/bin/bash
# pi/setup-system.sh — system part of PiTV. Runs ON the Pi (install.sh pipes it over SSH).
#   packages, helpers, hostname, Wi-Fi radio fix, static IP, timezone, Pi-hole
# Settings come in as environment variables (see pitv.env.example). Safe to re-run.
set -euo pipefail
: "${PITV_HOSTNAME:?}" "${PITV_IP:?}" "${PITV_GW:?}" "${PITV_TIMEZONE:=Asia/Bangkok}"
UPSTREAM_DNS=("1.1.1.1" "9.9.9.9")

show() {  # progress here and as a banner on the TV console
  echo "==> $*"
  sudo sh -c 'printf "\n\033[1;36m==== %s  [%s] ====\033[0m\n" "$1" "$(date +%H:%M:%S)" > /dev/tty1' _ "$*" 2>/dev/null || true
}

# ------------------------------------------------------------------ packages
show "PiTV: system update"
export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get update -q
sudo -E apt-get -y -q -o Dpkg::Options::=--force-confold full-upgrade
sudo -E apt-get -y -q install \
  cec-utils curl git iw alsa-utils espeak-ng fonts-thai-tlwg-ttf \
  kodi kodi-inputstream-adaptive kodi-repository-kodi kodi-eventclients-kodi-send

# ------------------------------------------------------------------ helpers
sudo tee /usr/local/bin/pitv-show >/dev/null <<'EOF'
#!/bin/sh
# pitv-show "message" : print a banner on the TV console (tty1)
printf "\n\033[1;36m==== %s  [%s] ====\033[0m\n" "$*" "$(date +%H:%M:%S)" > /dev/tty1
EOF
sudo tee /usr/local/bin/kodi-rpc >/dev/null <<'EOF'
#!/usr/bin/env python3
"""kodi-rpc Method ['{"json": "params"}']  - one Kodi JSON-RPC call on 127.0.0.1:9090"""
import json, socket, sys
req = {"jsonrpc": "2.0", "id": 1, "method": sys.argv[1],
       "params": json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}}
with socket.create_connection(("127.0.0.1", 9090), timeout=10) as s:
    s.sendall(json.dumps(req).encode())
    buf = b""
    while True:
        buf += s.recv(65536)
        try:
            print(json.dumps(json.loads(buf), ensure_ascii=False)); break
        except ValueError:
            continue
EOF
sudo chmod 755 /usr/local/bin/pitv-show /usr/local/bin/kodi-rpc

# ------------------------------------------------------------------ hostname, timezone
show "PiTV: hostname $PITV_HOSTNAME"
printf 'preserve_hostname: true\nmanage_etc_hosts: false\n' | sudo tee /etc/cloud/cloud.cfg.d/99-pitv.cfg >/dev/null
if [ "$(hostname)" != "$PITV_HOSTNAME" ]; then
  OLD="$(hostname)"
  sudo hostnamectl set-hostname "$PITV_HOSTNAME"
  sudo sed -i "s/\b$OLD\b/$PITV_HOSTNAME/g" /etc/hosts
  sudo systemctl restart avahi-daemon
fi
sudo timedatectl set-timezone "$PITV_TIMEZONE"

# ------------------------------------------------------------------ Wi-Fi radio always on
# A fresh image can keep Wi-Fi disabled in NetworkManager's own state file.
sudo tee /etc/systemd/system/pitv-wifi-on.service >/dev/null <<'EOF'
[Unit]
Description=PiTV: make sure the Wi-Fi radio is on
After=NetworkManager.service
Wants=NetworkManager.service
[Service]
Type=oneshot
ExecStart=/usr/sbin/rfkill unblock wifi
ExecStart=/usr/bin/nmcli radio wifi on
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable pitv-wifi-on.service >/dev/null 2>&1

# ------------------------------------------------------------------ static IP
# Applied to whichever connection is active (Wi-Fi or Ethernet); takes effect on next reconnect.
CON="$(nmcli -t -f NAME,TYPE con show --active | awk -F: '$2 ~ /wireless|ethernet/ {print $1; exit}')"
if [ -n "$CON" ]; then
  show "PiTV: static IP $PITV_IP on $CON"
  sudo nmcli con mod "$CON" ipv4.method manual ipv4.addresses "$PITV_IP/24" ipv4.gateway "$PITV_GW" \
    ipv4.dns "${UPSTREAM_DNS[*]}" ipv4.ignore-auto-dns yes ipv6.ignore-auto-dns yes
else
  echo "WARNING: no active network connection found; static IP skipped"
fi

# ------------------------------------------------------------------ Pi-hole
if ! command -v pihole >/dev/null; then
  show "PiTV: installing Pi-hole"
  IFACE="$(ip route show default | awk '{print $5; exit}')"
  sudo mkdir -p /etc/pihole
  sudo tee /etc/pihole/pihole.toml >/dev/null <<EOF
[dns]
  upstreams = ["${UPSTREAM_DNS[0]}", "${UPSTREAM_DNS[1]}"]
  interface = "${IFACE:-wlan0}"
  listeningMode = "LOCAL"
[webserver]
  port = "80o,443os,[::]:80o,[::]:443os"
EOF
  curl -sSL https://install.pi-hole.net -o /tmp/pihole-install.sh
  sudo PIHOLE_SKIP_OS_CHECK=true bash /tmp/pihole-install.sh --unattended
  rm -f /tmp/pihole-install.sh
fi

show "PiTV: system ready"
