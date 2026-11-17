# TODO

## Run the MCP server on the Pi

Today `mcp/pitv_mcp.py` runs on the Mac (stdio, started by Claude Code) and talks to
the Pi over SSH, so Claude can only drive the TV while the Mac is on and on the same
network. Moving it to the Pi removes that dependency.

- [ ] Check the Python MCP SDK installs on a Pi 3 (armv7, 32-bit): `pydantic-core` is
      Rust; confirm a prebuilt wheel exists (PyPI / piwheels) instead of compiling on the Pi.
- [ ] Serve MCP over streamable HTTP on the Pi (e.g. `http://pitv.local:8765/mcp`) as a
      systemd service; call `pitv-ctl` locally instead of over SSH.
- [ ] Require a bearer token (generated at install, stored on the Pi and in `pitv.env`);
      LAN only by default.
- [ ] `install.sh`: register it with `claude mcp add --transport http ... --header "Authorization: Bearer ..."`
      and keep the Mac/stdio server as an option.
- [ ] Voice: keep macOS voices when the Mac is reachable; otherwise fall back to
      `espeak-ng` on the Pi. Evaluate Piper TTS (offline, check for a Thai voice) or a
      cloud TTS (needs the user's own API key).
- [ ] Optional, later: reach it from Claude on the phone / claude.ai through a tunnel
      (Cloudflare Tunnel or Tailscale) with proper authentication. Bigger security
      surface; do not expose it without auth.

Memory budget on a Pi 3 (1 GB): about 600 MB free with Kodi and Pi-hole running; the
MCP server needs roughly 40-60 MB.

## Other open items

- [ ] YouTube search inside Kodi needs a YouTube Data API key (the user's own); document
      how to add it. Playback and the RSS channel lists work without one.
- [ ] 60 fps uploads play at 480p because 60 fps is disabled (a Pi 3 cannot decode
      1080p60 H.264). Consider allowing 720p60.
- [ ] Screenshots for the README without channel logos (e.g. demo channels or blurred tiles).
- [ ] Test `boot/prepare-sd.sh` + `install.sh` end to end on a freshly flashed card
      (the installer was re-run on a configured Pi; the first-boot script was verified
      piece by piece during the original setup).
- [ ] Weather line on the home screen, clock screensaver (ideas from CleanYourTV's add-ons).
