#!/bin/bash
# PiTV first boot: bring Wi-Fi up without relying on cloud-init.
# Runs once from cmdline.txt (systemd.run=...), removes itself from cmdline, then reboots.
#
# Why: on Raspberry Pi OS Trixie Lite we found that
#   - cloud-init's network-config did not bring Wi-Fi up, and
#   - NetworkManager kept Wi-Fi disabled in its own state file (WirelessEnabled=false).
# SSID, password and country are read from network-config on this card; the password
# is never written to the log, and it is removed from network-config afterwards.
set +e
B=/boot/firmware
exec > "$B/pitv-firstboot.log" 2>&1
echo "== pitv-firstboot $(date)"

# never run twice
sed -i 's| systemd\.run[^ ]*||g; s| systemd\.unit=kernel-command-line\.target||g' "$B/cmdline.txt"

NC="$B/network-config"
SSID=$(sed -n 's/^ *"\(.*\)": *$/\1/p' "$NC" | head -1)
PSK=$(sed -n 's/^ *password: *"\(.*\)" *$/\1/p' "$NC" | head -1)
COUNTRY=$(sed -n 's/^ *regulatory-domain: *\([A-Z][A-Z]\).*/\1/p' "$NC" | head -1)
echo "ssid: $SSID  country: ${COUNTRY:-none}  password length: ${#PSK}"

# Wi-Fi regulatory domain (enables channels 12-13 where allowed)
if [ -n "$COUNTRY" ] && ! grep -q cfg80211.ieee80211_regdom "$B/cmdline.txt"; then
  sed -i "s/\$/ cfg80211.ieee80211_regdom=$COUNTRY/" "$B/cmdline.txt"
fi

if [ -n "$SSID" ] && [ -n "$PSK" ] && [ "$PSK" != "PASSWORD_HERE" ]; then
  F=/etc/NetworkManager/system-connections/pitv-wifi.nmconnection
  cat > "$F" <<EOF
[connection]
id=pitv-wifi
type=wifi
interface-name=wlan0
autoconnect=true

[wifi]
mode=infrastructure
ssid=$SSID

[wifi-security]
key-mgmt=wpa-psk
psk=$PSK

[ipv4]
method=auto

[ipv6]
method=auto
EOF
  chmod 600 "$F"
  echo "wifi connection written"
  # the password now lives only in the root-only NetworkManager file
  sed -i 's/^\( *password: *\)".*"/\1"REMOVED_AFTER_SETUP"/' "$NC"
else
  echo "no Wi-Fi password set; using Ethernet only"
fi

# Wi-Fi radio on, now and on every boot
S=/var/lib/NetworkManager/NetworkManager.state
mkdir -p /var/lib/NetworkManager
if grep -q '^WirelessEnabled=' "$S" 2>/dev/null; then
  sed -i 's/^WirelessEnabled=.*/WirelessEnabled=true/' "$S"
else
  printf '[main]\nNetworkingEnabled=true\nWirelessEnabled=true\nWWANEnabled=true\n' > "$S"
fi
for f in /var/lib/systemd/rfkill/*:wlan; do [ -e "$f" ] && echo 0 > "$f"; done
cat > /etc/systemd/system/pitv-wifi-on.service <<'EOF'
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
ln -sf /etc/systemd/system/pitv-wifi-on.service /etc/systemd/system/multi-user.target.wants/pitv-wifi-on.service
systemctl enable ssh 2>&1 | tail -1

rm -f "$B/pitv-firstboot.sh"
echo "== done $(date)"
sync
exit 0
