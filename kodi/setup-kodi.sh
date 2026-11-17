#!/bin/bash
# kodi/setup-kodi.sh — Kodi part of PiTV. Runs ON the Pi (install.sh pipes it over SSH).
#   kodi.service on tty1, skin.pitv (a copy of Estuary with Thai fonts), YouTube add-on,
#   Kodi + add-on settings tuned for a Pi 3 on a Sony Bravia over HDMI. Safe to re-run.
# The home screen itself (Home.xml, artwork, plugin.video.pitv) is pushed by kodi/deploy.sh.
set -euo pipefail
G=~/.kodi/userdata/guisettings.xml
SKIN=~/.kodi/addons/skin.pitv

show() { echo "==> $*"; pitv-show "$*" 2>/dev/null || true; }
rpc() { kodi-rpc "$@"; }
wait_kodi() {
  for _ in $(seq 1 60); do rpc JSONRPC.Ping 2>/dev/null | grep -q pong && return 0; sleep 2; done
  echo "Kodi did not start" >&2; return 1
}
focus_label() { rpc GUI.GetProperties '{"properties":["currentcontrol"]}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["currentcontrol"]["label"])'; }
answer_yes() {  # press "Yes" in Kodi's Yes/No dialog (default focus is "No")
  for _ in $(seq 1 15); do
    rpc GUI.GetProperties '{"properties":["currentwindow"]}' | grep -q "Yes / No" && break; sleep 1
  done
  for _ in 1 2 3; do [ "$(focus_label)" = "Yes" ] && break; rpc Input.Left >/dev/null; sleep 0.5; done
  [ "$(focus_label)" = "Yes" ] && rpc Input.Select >/dev/null
}

# ------------------------------------------------------------------ service on tty1
show "PiTV: Kodi service"
sudo tee /etc/systemd/system/kodi.service >/dev/null <<'EOF'
[Unit]
Description=Kodi (PiTV main screen)
After=network-online.target sound.target systemd-user-sessions.service
Wants=network-online.target
Conflicts=getty@tty1.service

[Service]
User=pi
Group=pi
SupplementaryGroups=input video render audio
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
ExecStart=/usr/bin/kodi-standalone
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl disable --now getty@tty1 >/dev/null 2>&1 || true
sudo systemctl enable kodi.service >/dev/null 2>&1

# JSON-RPC (TCP 9090, this machine only) must be on before Kodi starts the first time
mkdir -p ~/.kodi/userdata ~/.kodi/media/Fonts
if [ ! -f "$G" ]; then
  printf '<settings version="2">\n    <setting id="services.esenabled">true</setting>\n    <setting id="services.esallinterfaces">false</setting>\n</settings>\n' > "$G"
fi
# Thai-capable font for Kodi's "Arial" option (dialogs from other add-ons)
cp /usr/share/fonts/truetype/tlwg/Garuda.ttf ~/.kodi/media/Fonts/arial.ttf
sudo systemctl restart kodi.service
wait_kodi

# ------------------------------------------------------------------ skin.pitv = Estuary + Thai fonts
show "PiTV: skin"
if [ ! -f "$SKIN/addon.xml" ]; then
  rm -rf "$SKIN"
  cp -rL /usr/share/kodi/addons/skin.estuary "$SKIN" 2>/dev/null || true   # one dangling font link is fine
  sed -i 's/id="skin.estuary"/id="skin.pitv"/; s/name="Estuary"/name="PiTV"/; s/\(<addon [^>]*version="[0-9.]*\)"/\1.1"/' "$SKIN/addon.xml"
fi
cp /usr/share/fonts/truetype/tlwg/Garuda.ttf      "$SKIN/fonts/NotoSans-Regular.ttf"
cp /usr/share/fonts/truetype/tlwg/Garuda-Bold.ttf "$SKIN/fonts/NotoSans-Bold.ttf"
cp /usr/share/fonts/truetype/tlwg/Garuda.ttf      "$SKIN/fonts/Roboto-Thin.ttf"
kodi-send --action="UpdateLocalAddons" >/dev/null; sleep 3
rpc Addons.SetAddonEnabled '{"addonid":"skin.pitv","enabled":true}' >/dev/null

# ------------------------------------------------------------------ YouTube add-on (official Kodi repo)
if ! rpc Addons.GetAddonDetails '{"addonid":"plugin.video.youtube"}' | grep -q '"addonid"'; then
  show "PiTV: YouTube add-on"
  kodi-send --action="UpdateAddonRepos" >/dev/null; sleep 20
  kodi-send --action="InstallAddon(plugin.video.youtube)" >/dev/null
  answer_yes
  for _ in $(seq 1 60); do rpc Addons.GetAddonDetails '{"addonid":"plugin.video.youtube"}' | grep -q '"addonid"' && break; sleep 3; done
fi

# ------------------------------------------------------------------ settings (edit while Kodi is stopped)
show "PiTV: Kodi settings"
sudo systemctl stop kodi.service; sleep 2
python3 - "$G" <<'EOF'
import re, sys
path = sys.argv[1]
SETTINGS = {
    "lookandfeel.skin": "skin.pitv",
    "locale.country": "UK (24h)",                          # 24h clock: greetings use System.Time(HH)
    "audiooutput.audiodevice": "ALSA:hdmi:CARD=vc4hdmi,DEV=0",  # default is the headphone jack
    "audiooutput.streamsilence": "0",                      # free HDMI when idle (alarm uses aplay)
    "audiooutput.guisoundmode": "0",
    "services.esenabled": "true",                          # JSON-RPC on 127.0.0.1:9090
    "services.esallinterfaces": "false",
    "debug.screenshotpath": "/home/pi/shots/",
}
xml = open(path, encoding="utf-8").read()
for key, val in SETTINGS.items():
    new = f'<setting id="{key}">{val}</setting>'
    xml, n = re.subn(rf'<setting id="{re.escape(key)}"[^>]*?(?:/>|>[^<]*</setting>)', new, xml)
    if not n:
        xml = xml.replace("</settings>", f"    {new}\n</settings>")
open(path, "w", encoding="utf-8").write(xml)
EOF
mkdir -p ~/shots

# YouTube: H.264 only (hardware decode on Pi 3), no 60 fps, up to 1080p
Y=~/.kodi/userdata/addon_data/plugin.video.youtube; mkdir -p "$Y"
python3 - "$Y/settings.xml" <<'EOF'
import os, re, sys
path = sys.argv[1]
want = {"kodion.mpd.stream.features": "avc1,prefer_dub,prefer_auto_dub,mp4a,vtt,filter",
        "kodion.mpd.quality.selection": "4",
        # live: Kodi's own HLS player starts at the live edge (isa_hls started at the
        # beginning of the DVR window, minutes behind)
        "kodion.live_stream.selection.1": "1"}
xml = open(path, encoding="utf-8").read() if os.path.exists(path) else '<settings version="2">\n</settings>\n'
for k, v in want.items():
    new = f'<setting id="{k}">{v}</setting>'
    xml, n = re.subn(rf'<setting id="{re.escape(k)}"[^>]*?(?:/>|>[^<]*</setting>)', new, xml)
    if not n:
        xml = xml.replace("</settings>", f"    {new}\n</settings>")
open(path, "w", encoding="utf-8").write(xml)
EOF
# inputstream.adaptive: start at 20 Mbit/s instead of guessing low (stuck at 480p otherwise)
A=~/.kodi/userdata/addon_data/inputstream.adaptive; mkdir -p "$A"
cat > "$A/settings.xml" <<'EOF'
<settings version="2">
    <setting id="adaptivestream.bandwidth.init.auto">false</setting>
    <setting id="adaptivestream.bandwidth.init">20000</setting>
</settings>
EOF

sudo systemctl start kodi.service
wait_kodi
show "PiTV: Kodi ready"
