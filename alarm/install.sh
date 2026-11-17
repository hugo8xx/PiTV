#!/bin/bash
# Install the PiTV wake-up alarm on the Pi and schedule it (systemd OnCalendar syntax).
#   alarm/install.sh "2026-11-18 05:00:00"     one-off
#   alarm/install.sh "Mon..Fri 05:00:00"       every weekday
#   alarm/install.sh "*-*-* 06:30:00"          every day
#   alarm/install.sh off                        remove the schedule
# Channels: PITV_ALARM_CHANNEL / PITV_ALARM_BACKUP in pitv.env.
set -euo pipefail
. "$(dirname "$0")/../lib/env.sh"
cd "$PITV_ROOT/alarm"
HOST="$PITV_HOST"
WHEN="${1:?give a time, e.g. \"2026-11-18 05:00:00\", or off}"

if [ "$WHEN" = "off" ]; then
  ssh "$HOST" 'sudo systemctl disable --now pitv-alarm.timer; systemctl list-timers pitv-alarm.timer --no-pager'
  exit 0
fi

[ -f sounds/hello.wav ] || ./make_sounds.sh
python3 -m py_compile pitv-alarm
scp -q pitv-alarm "$HOST:/tmp/pitv-alarm"
ssh "$HOST" 'rm -rf /tmp/pitv-sounds'
scp -q -r sounds "$HOST:/tmp/pitv-sounds"
ssh "$HOST" "WHEN='$WHEN' MAIN='$PITV_ALARM_CHANNEL' BACKUP='$PITV_ALARM_BACKUP' bash -s" <<'EOF'
set -e
sudo install -m 755 /tmp/pitv-alarm /usr/local/bin/pitv-alarm
sudo mkdir -p /usr/local/share/pitv/sounds
sudo cp /tmp/pitv-sounds/*.wav /usr/local/share/pitv/sounds/
rm -rf /tmp/pitv-sounds /tmp/pitv-alarm
sudo tee /etc/systemd/system/pitv-alarm.service >/dev/null <<UNIT
[Unit]
Description=PiTV wake-up alarm
After=kodi.service network-online.target
[Service]
Type=oneshot
User=pi
ExecStart=/usr/local/bin/pitv-alarm --channel "$MAIN" --backup "$BACKUP"
UNIT
sudo tee /etc/systemd/system/pitv-alarm.timer >/dev/null <<UNIT
[Unit]
Description=PiTV wake-up alarm schedule
[Timer]
OnCalendar=$WHEN
AccuracySec=1s
[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now pitv-alarm.timer
systemctl list-timers pitv-alarm.timer --no-pager | head -2
EOF
