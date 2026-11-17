# PiTV

Turn an old Raspberry Pi and a "dumb" smart TV into a clean, ad-free TV box that
an AI assistant can drive.

> ปลุก Pi เก่ากับทีวีเก่าให้กลายเป็นกล่องทีวีที่ไม่มีโฆษณา หน้าตาเรียบสวยแบบ
> CleanYourTV และให้ Claude สั่งงานได้ ทั้งเปิดปิดทีวี เปิดไลฟ์ข่าว พูดภาษาไทย
> และปลุกตอนเช้า

Built and tested on a **Raspberry Pi 3 Model B (1 GB)** and a **Sony Bravia W660F**
(a Linux TV, not Android TV, so it cannot be debloated itself). Any TV with HDMI-CEC
should work.

| | What you get |
|---|---|
| Home screen | Kodi with a black, dock-style home (inspired by [CleanYourTV](https://github.com/Gathin23/cleanyourtv)): greeting, thin clock, Thai date, rotating landscape wallpapers, a top shelf that names the focused tile over a glow in its colour |
| Favourite channels | YouTube channels as dock tiles: latest videos via the public RSS feed (no API key), or straight to the live stream |
| YouTube | Official Kodi add-on, tuned for the Pi 3: H.264 hardware decode up to 1080p |
| TV control | HDMI-CEC: turn the TV on/off and switch it to the Pi; the TV remote drives Kodi |
| Ad blocking | Pi-hole for the TV, or the whole house |
| AI control | An MCP server so Claude can show notifications, speak (macOS voices), play videos or live streams, and read Pi-hole stats |
| Wake-up alarm | Wakes the TV, counts down, says good morning, opens the live news (falls back to a second channel, then the newest video) |

## How it fits together

```
Claude ──MCP (stdio)──> mcp/pitv_mcp.py (Mac) ──ssh + JSON──> pitv-ctl (Pi)
                                                               ├─ Kodi JSON-RPC (127.0.0.1:9090)
                                                               ├─ cec-ctl  ── HDMI-CEC ──> TV
                                                               ├─ aplay    ── HDMI audio ─> TV speakers
                                                               └─ pihole
pitv-alarm.timer (Pi) ──> pitv-alarm: CEC wake → countdown screen → voice → live news
```

## Requirements

- Raspberry Pi with HDMI (tested: Pi 3 B), 8 GB+ SD card, power supply
- A Mac (for the voices and the scripts) with `uv`, `python3`, and an SSH key
- Raspberry Pi Imager, to flash **Raspberry Pi OS Lite (32-bit)**
- Optional: [Claude Code](https://claude.com/claude-code) for the MCP server

## Install

```bash
git clone <this repo> pitv && cd pitv
cp pitv.env.example pitv.env      # set Wi-Fi name, static IP, alarm channels
```

1. Flash **Raspberry Pi OS Lite (32-bit)** with Raspberry Pi Imager (no customisation).
   Leave the card in the Mac.
2. Prepare the card. It adds your SSH key, hostname and Wi-Fi name, then opens the
   Wi-Fi config so **you** type the password (it is never stored in this repo):

   ```bash
   boot/prepare-sd.sh
   ```

3. Put the card in the Pi, connect HDMI to the TV, power on. The first boot reboots
   once (about 3 minutes). Check it answers: `ssh pi@pitv.local true`
4. Install everything:

   ```bash
   ./install.sh
   ```

5. Things only you should do:
   - Pi-hole admin password: `ssh -t pi@pitv.local sudo pihole setpassword`
   - Set the TV's DNS (or your router's) to the Pi's IP to block ads
   - Optional alarm: `alarm/install.sh "Mon..Fri 05:00:00"` (`alarm/install.sh off` removes it)

## Customise

| Change | How |
|---|---|
| Favourite channels | Edit `kodi/channels/channels.json` (`handle`, `name`, `tile`: `"videos"` or `"live"`), then `kodi/deploy.sh` |
| Wallpapers | Put 16:9 JPEGs in `kodi/wallpapers/src/`, then `kodi/deploy.sh`. `WALLPAPER*` in `kodi/build_home.py` sets rotation |
| Alarm words or voice | Edit `alarm/make_sounds.sh` / `PITV_VOICE_TH`, delete `alarm/sounds/`, re-run `alarm/install.sh` |
| Home screen layout | `kodi/build_home.py` generates `Home.xml`; `kodi/deploy.sh --shot` deploys and saves a screenshot |

## MCP tools

| Tool | Does |
|---|---|
| `pitv_status` | TV power, what Kodi plays, volume, Pi-hole state |
| `pitv_power` / `pitv_switch_to_pi` | TV on/standby, switch input to the Pi |
| `pitv_notify` | Pop-up on the TV (Thai works) |
| `pitv_say` | Speak through the TV: macOS voice rendered on the Mac (`engine="espeak"` = on the Pi) |
| `pitv_play` / `pitv_youtube` / `pitv_youtube_live` | Play a URL, a YouTube video, or a channel's live stream |
| `pitv_control` | play/pause, stop, next, previous, mute, volume, home |
| `pitv_pihole_stats` / `_block` / `_unblock` | Pi-hole stats, deny/allow a domain |

Arguments reach the Pi as JSON on stdin and are passed to programs as argument
lists, never through a shell. Kodi's JSON-RPC listens on `127.0.0.1` only.

## Repository layout

```
install.sh              one-shot installer (Mac → Pi over SSH)
pitv.env.example        settings template (copy to pitv.env)
boot/                   SD-card first boot: cloud-init + Wi-Fi fix (prepare-sd.sh)
pi/                     system setup, pitv-ctl controller, YouTube live/RSS helper
kodi/                   Kodi setup, home-screen generator, channel add-on, fonts, wallpapers
alarm/                  wake-up alarm, sound generator, scheduler
mcp/                    MCP server for Claude
```

## Things we learned the hard way

- **Wi-Fi on Raspberry Pi OS Trixie Lite:** cloud-init's `network-config` did not bring
  Wi-Fi up, changing `instance_id` did not re-run it, and NetworkManager kept Wi-Fi
  disabled in `/var/lib/NetworkManager/NetworkManager.state`. `boot/pitv-firstboot.sh`
  fixes all three via `systemd.run=`.
- **Kodi audio defaults to the headphone jack** on a Pi 3; set it to `ALSA:hdmi:CARD=vc4hdmi,DEV=0`.
- **The TV drops the start of every new HDMI audio stream** (worse right after waking
  from standby). The alarm plays one continuous track instead of separate clips.
- **YouTube on a Pi 3:** the default AV1 1080p60 is software-decoded and stutters. Use
  H.264 only, no 60 fps, and give inputstream.adaptive a higher starting bandwidth or it
  sits at 480p.
- **Live streams started minutes behind** with the YouTube add-on's default live player
  (inputstream.adaptive HLS starts at the beginning of the DVR window). Setting
  `kodion.live_stream.selection.1 = 1` (Kodi's own HLS) starts at the live edge.
- **Live detection:** `/channel/UC…/live` has `"isLive":true` but no `"isLiveNow"`;
  `/@handle/live` has both.
- **Kodi's Estuary font has no Thai glyphs**; the skin swaps in Garuda (TLWG).
- The macOS voice Kanya returns silence for some sentences unless they end with a full stop.

## Not included

- No pirated streams. Use legal sources only.
- Channel artwork, voice clips and screenshots are generated on your machine and
  git-ignored (they belong to the channels / come from macOS voices).

## Licence

PiTV is released under the MIT License (see `LICENSE`). Third-party material and
credits are listed in `NOTICE.md`.
