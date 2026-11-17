#!/bin/bash
# Make the alarm's sound clips on a Mac (git-ignored, so they are never redistributed):
#   hello.wav  "สวัสดีค่ะ. ได้เวลาตื่นแล้วนะคะ"   news.wav  "กำลังเปิดข่าวให้นะคะ"
#   tick.wav / chime.wav  simple tones
# Voices: macOS `say` (PITV_VOICE_TH in pitv.env). Edit the lines below to change the words.
set -euo pipefail
. "$(dirname "$0")/../lib/env.sh"
OUT="$PITV_ROOT/alarm/sounds"
mkdir -p "$OUT"
cd "$OUT"

speak() {  # speak <file> <text>
  # The first `say` after the voice has been idle often renders silence: retry.
  for _ in 1 2 3 4; do
    say -v "$PITV_VOICE_TH" -r 165 -o "$1.aiff" -- "$2"
    afinfo "$1.aiff" | awk '/estimated duration/{exit !($3 > 0.5)}' && break
    sleep 1
  done
  afconvert -f WAVE -d LEI16@22050 "$1.aiff" "$1.wav"
  rm -f "$1.aiff"
}
speak hello "สวัสดีค่ะ. ได้เวลาตื่นแล้วนะคะ"   # the "." helps Kanya with this sentence
speak news  "กำลังเปิดข่าวให้นะคะ"

python3 - <<'EOF'
import math, struct, wave
RATE = 22050
def tone(freq, dur, vol=0.35):
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1, t / 0.01, (dur - t) / 0.04)
        out.append(int(math.sin(2 * math.pi * freq * t) * env * vol * 32767))
    return out
clips = {"tick": tone(880, 0.12),
         "chime": tone(660, 0.18) + tone(880, 0.18) + tone(1320, 0.35)}
for name, data in clips.items():
    with wave.open(f"{name}.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(struct.pack(f"<{len(data)}h", *data))
EOF

for f in hello news; do
  d=$(afinfo "$f.wav" | awk '/estimated duration/{print $3}')
  echo "$f.wav ${d}s"
  if awk "BEGIN{exit !($d < 0.5)}"; then
    echo "ERROR: $f.wav is (almost) silent. Is the voice \"$PITV_VOICE_TH\" installed?"; exit 1
  fi
done
exit 0
