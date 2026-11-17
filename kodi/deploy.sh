#!/bin/bash
# Build the PiTV home screen and push it to the Pi, then reload Kodi's skin.
#   kodi/deploy.sh            build + copy + reload
#   kodi/deploy.sh --shot     ... and save a screenshot to screenshots/home-latest.png
set -euo pipefail
. "$(dirname "$0")/../lib/env.sh"
cd "$PITV_ROOT"
HOST="$PITV_HOST"

# channel avatars are fetched locally (not stored in the repo)
uv run --quiet --script kodi/fetch_channels.py
uv run --quiet --script kodi/build_home.py
python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1])" kodi/skin.pitv/xml/Home.xml

scp -q kodi/skin.pitv/xml/Home.xml kodi/skin.pitv/xml/Custom_1150_PiTVAlarm.xml "$HOST:.kodi/addons/skin.pitv/xml/"
ssh "$HOST" 'rm -rf ~/.kodi/addons/skin.pitv/media/pitv'
scp -q -r kodi/skin.pitv/media/pitv "$HOST:.kodi/addons/skin.pitv/media/"
scp -q kodi/fonts/Outfit-200.ttf kodi/fonts/Outfit-300.ttf "$HOST:.kodi/addons/skin.pitv/fonts/"
ssh "$HOST" 'python3 - .kodi/addons/skin.pitv/xml/Font.xml' < kodi/patch_fonts.py
scp -q -r kodi/plugin.video.pitv "$HOST:.kodi/addons/"
ssh "$HOST" 'kodi-send --action="UpdateLocalAddons" >/dev/null; sleep 2
  kodi-rpc Addons.SetAddonEnabled "{\"addonid\":\"plugin.video.pitv\",\"enabled\":true}" >/dev/null
  kodi-send --action="ReloadSkin()" >/dev/null'
echo "deployed to $HOST"

if [ "${1:-}" = "--shot" ]; then
  sleep 4
  ssh "$HOST" 'mkdir -p ~/shots; rm -f ~/shots/*.png; kodi-send --action="TakeScreenshot" >/dev/null
    for i in $(seq 1 20); do f=$(ls ~/shots/*.png 2>/dev/null | head -1); [ -n "$f" ] && [ -s "$f" ] && sleep 2 && break; sleep 1; done
    mv "$(ls ~/shots/*.png | head -1)" ~/shots/latest.png'
  mkdir -p screenshots
  scp -q "$HOST:shots/latest.png" screenshots/home-latest.png
  sips -Z 1200 screenshots/home-latest.png >/dev/null
  echo "screenshot: screenshots/home-latest.png"
fi
