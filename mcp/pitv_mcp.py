# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2,<2"]  # v2 renamed FastMCP -> MCPServer
# ///
"""PiTV MCP server (runs on the Mac, stdio).

Every tool sends one JSON command over SSH to `pitv-ctl` on the Pi
(see ../pi/pitv-ctl). SSH uses the existing key login to pi@pitv.local.

Run:  uv run --script mcp/pitv_mcp.py
Settings: pitv.env in the repo root (PITV_HOST, PITV_VOICE_TH, PITV_VOICE_EN);
environment variables override it.
"""
import base64
import json
import os
import re
import subprocess
import tempfile
from typing import Literal

from mcp.server.fastmcp import FastMCP

def _load_env():
    """Read KEY=value lines from pitv.env.example, then pitv.env (repo root)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vals = {}
    for name in ("pitv.env.example", "pitv.env"):
        path = os.path.join(root, name)
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                m = re.match(r"^\s*([A-Z_]+)=(.*)$", line)
                if m:
                    vals[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    vals.update({k: v for k, v in os.environ.items() if k.startswith("PITV_")})
    return vals


ENV = _load_env()
PITV_HOST = ENV.get("PITV_HOST", "pi@pitv.local")
SSH = [
    "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
    "-o", "ServerAliveInterval=5", PITV_HOST, "/usr/local/bin/pitv-ctl",
]

mcp = FastMCP(
    "pitv",
    instructions=(
        "Controls PiTV: a Raspberry Pi on the HDMI input of the user's TV at home. "
        "Kodi is the main screen; Pi-hole blocks ads on the home network. "
        "Use pitv_notify for silent on-screen messages and pitv_say to speak out loud (Thai or English). "
        "Never open pirated streaming sites with pitv_play."
    ),
)


def call(cmd: str, timeout: int = 60, **args) -> dict:
    payload = json.dumps({"cmd": cmd, **args}, ensure_ascii=False)
    try:
        p = subprocess.run(SSH, input=payload, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"PiTV did not answer within {timeout}s"}
    if p.returncode == 255:
        return {"ok": False, "error": f"Cannot reach {PITV_HOST} over SSH: {p.stderr.strip()[-300:]}"}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "error": f"Bad reply from pitv-ctl: {(p.stdout + p.stderr).strip()[-300:]}"}


@mcp.tool()
def pitv_status() -> dict:
    """TV power state (via HDMI-CEC), what Kodi is playing, Kodi volume, and Pi-hole status."""
    return call("status")


@mcp.tool()
def pitv_power(state: Literal["on", "off"]) -> dict:
    """Turn the TV on (and switch it to the Pi) or put it in standby, via HDMI-CEC."""
    return call("power", state=state)


@mcp.tool()
def pitv_switch_to_pi() -> dict:
    """Switch the TV's input to HDMI 1 (the Pi / Kodi screen)."""
    return call("input_pi")


@mcp.tool()
def pitv_notify(message: str, title: str = "PiTV", seconds: int = 8) -> dict:
    """Show a pop-up notification in the top-right corner of the TV (Kodi). Thai text works.

    seconds: 2-60.
    """
    return call("notify", message=message, title=title, seconds=seconds)


MAC_VOICES = {"th": ENV.get("PITV_VOICE_TH", "Kanya (Enhanced)"), "en": ENV.get("PITV_VOICE_EN", "Samantha")}


def mac_tts_wav(text: str, voice: str, rate: int) -> bytes:
    """Render speech with macOS `say` and return it as a 22 kHz 16-bit WAV."""
    with tempfile.TemporaryDirectory(prefix="pitv-say-") as d:
        aiff, wav = os.path.join(d, "s.aiff"), os.path.join(d, "s.wav")
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", aiff, "--", text],
                       check=True, capture_output=True, timeout=60)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", aiff, wav],
                       check=True, capture_output=True, timeout=60)
        with open(wav, "rb") as f:
            data = f.read()
    return data


def mac_tts(text: str, voice: str, rate: int) -> bytes:
    """macOS voices sometimes return silence (first call after idle, or some Thai
    sentences without a full stop): retry, then retry with a full stop."""
    for attempt in range(4):
        t = text if attempt < 2 or text.endswith(".") else text + "."
        data = mac_tts_wav(t, voice, rate)
        if len(data) > 22050:  # > ~0.5 s of 22 kHz 16-bit audio
            return data
    return data


@mcp.tool()
def pitv_say(
    text: str,
    lang: Literal["auto", "th", "en"] = "auto",
    speed: int = 170,
    engine: Literal["mac", "espeak"] = "mac",
) -> dict:
    """Speak text out loud through the TV speakers.

    engine 'mac' (default): natural voice made on this Mac with macOS `say`
    (Thai: Kanya, English: Samantha), then played on the Pi.
    engine 'espeak': robotic offline voice made on the Pi itself (fallback).
    lang 'auto' picks Thai if the text contains Thai letters, else English.
    speed: words per minute, 80-260.
    """
    text = text.strip()[:1000]
    if lang == "auto":
        lang = "th" if re.search(r"[฀-๿]", text) else "en"
    speed = max(80, min(int(speed), 260))
    if engine == "mac":
        try:
            wav = mac_tts(text, MAC_VOICES[lang], speed)
            r = call("play_wav", timeout=200, wav_b64=base64.b64encode(wav).decode())
            if r.get("ok"):
                r["voice"] = MAC_VOICES[lang]
            return r
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            fallback = call("say", timeout=150, text=text, lang=lang, speed=speed)
            fallback["note"] = f"macOS voice failed ({type(e).__name__}); used espeak-ng on the Pi"
            return fallback
    return call("say", timeout=150, text=text, lang=lang, speed=speed)


@mcp.tool()
def pitv_play(url: str) -> dict:
    """Play a media URL in Kodi on the TV: a direct http(s) video/audio link, or a Kodi plugin:// URL.

    Only legal sources. Does not switch the TV input; call pitv_switch_to_pi first if needed.
    """
    return call("play", url=url)


YT_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})|^([A-Za-z0-9_-]{11})$")


@mcp.tool()
def pitv_youtube(video: str) -> dict:
    """Play a YouTube video on the TV through Kodi's YouTube add-on.

    video: a YouTube URL (watch, youtu.be, shorts, live) or the 11-character video ID.
    Search is not available (the add-on has no API key); find the video ID first.
    Streams are H.264 up to 720p so the Pi 3 can decode them in hardware.
    """
    m = YT_ID.search(video.strip())
    if not m:
        return {"ok": False, "error": "could not find a YouTube video ID in that text"}
    vid = m.group(1) or m.group(2)
    r = call("play", url=f"plugin://plugin.video.youtube/play/?video_id={vid}")
    if r.get("ok"):
        call("input_pi")
    return r


@mcp.tool()
def pitv_youtube_live(channel: str, fallback_newest: bool = True) -> dict:
    """Play a YouTube channel's live stream on the TV.

    channel: @handle, channel URL (youtube.com/@name) or UC... channel id.
    If the channel is not live and fallback_newest is true, plays its newest video instead.
    """
    r = call("youtube_live", timeout=90, channel=channel, fallback_newest=fallback_newest)
    if r.get("ok") and (r.get("result") or {}).get("video_id"):
        call("input_pi")
    return r


@mcp.tool()
def pitv_control(
    action: Literal["play_pause", "stop", "next", "previous", "mute", "volume", "home"],
    level: int = 50,
) -> dict:
    """Control Kodi playback. 'volume' sets Kodi's volume to `level` (0-100); 'mute' toggles mute;
    'home' goes back to the Kodi home screen."""
    return call("control", action=action, level=level)


@mcp.tool()
def pitv_pihole_stats() -> dict:
    """Pi-hole statistics: total DNS queries, how many were blocked, and the top blocked domains."""
    return call("pihole_stats")


@mcp.tool()
def pitv_pihole_block(domain: str) -> dict:
    """Add a domain (e.g. ads.example.com) to Pi-hole's deny list for the whole home network."""
    return call("pihole_block", domain=domain)


@mcp.tool()
def pitv_pihole_unblock(domain: str) -> dict:
    """Allow a domain in Pi-hole (removes it from the deny list and adds it to the allow list)."""
    return call("pihole_unblock", domain=domain)


if __name__ == "__main__":
    mcp.run()
