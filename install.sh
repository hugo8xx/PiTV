#!/bin/bash
# PiTV installer. Run on the Mac once the Pi answers on the network (see README).
#   ./install.sh            everything: system, Pi-hole, Kodi, home screen, controller, MCP
#   ./install.sh --no-mcp   skip registering the MCP server with Claude Code
# Safe to run again; each part checks what is already done.
set -euo pipefail
. "$(dirname "$0")/lib/env.sh"
cd "$PITV_ROOT"
HOST="$PITV_HOST"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

for tool in ssh scp uv python3; do
  command -v "$tool" >/dev/null || { echo "missing: $tool"; exit 1; }
done
step "Checking SSH to $HOST"
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" true || {
  echo "Cannot log in to $HOST with your SSH key. Did you run boot/prepare-sd.sh?"; exit 1; }

step "System, Pi-hole (on the Pi, takes a while)"
ssh "$HOST" "PITV_HOSTNAME='$PITV_HOSTNAME' PITV_IP='$PITV_IP' PITV_GW='$PITV_GW' PITV_TIMEZONE='$PITV_TIMEZONE' bash -s" \
  < pi/setup-system.sh

step "PiTV controller (pitv-ctl + YouTube helpers)"
scp -q pi/pitv-ctl pi/pitv_youtube.py "$HOST:/tmp/"
ssh "$HOST" 'sudo install -m 755 /tmp/pitv-ctl /usr/local/bin/pitv-ctl
  sudo install -D -m 644 /tmp/pitv_youtube.py /usr/local/lib/pitv/pitv_youtube.py
  rm -f /tmp/pitv-ctl /tmp/pitv_youtube.py'

step "Kodi, skin, YouTube add-on"
ssh "$HOST" 'bash -s' < kodi/setup-kodi.sh

step "Home screen"
kodi/deploy.sh

if [ "${1:-}" != "--no-mcp" ] && command -v claude >/dev/null; then
  step "MCP server for Claude Code"
  if claude mcp get pitv >/dev/null 2>&1; then
    echo "pitv MCP server already registered"
  else
    claude mcp add --scope user pitv -- uv run --quiet --script "$PITV_ROOT/mcp/pitv_mcp.py"
  fi
fi

step "Done"
cat <<EOF
PiTV is on the TV (HDMI). Next steps you do yourself:
  - Pi-hole admin password:   ssh -t $HOST sudo pihole setpassword
  - Point the TV's DNS (or your router's) at $PITV_IP to block ads
  - Wake-up alarm (optional):  alarm/install.sh "Mon..Fri 05:00:00"
  - The static IP $PITV_IP takes effect on the Pi's next reboot.
EOF
