# /// script
# dependencies = []
# ///
"""Fill in channel ids and download channel avatars for kodi/channels/channels.json.

Avatars are the channels' own artwork, so they are downloaded to your machine and
git-ignored instead of being stored in the repo. Only missing data is fetched.

channels.json rows need just a handle; the rest is filled in:
  {"handle": "MorningNewsTV3", "name": "เรื่องเล่าเช้านี้", "tile": "videos"}
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

DIR = Path(__file__).parent / "channels"
LIST = DIR / "channels.json"
UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "th,en"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def main():
    channels = json.loads(LIST.read_text(encoding="utf-8"))
    changed = False
    for ch in channels:
        handle = ch["handle"].lstrip("@")
        avatar = DIR / f"{handle}.src"
        if ch.get("id") and avatar.exists():
            continue
        page = get(f"https://www.youtube.com/@{handle}").decode("utf-8", "replace")
        if not ch.get("id"):
            m = re.search(r'"(?:externalId|channelId)":"(UC[A-Za-z0-9_-]{22})"', page)
            if not m:
                sys.exit(f"could not find the channel id for @{handle}")
            ch["id"] = m.group(1)
            changed = True
        if not ch.get("name"):
            m = re.search(r'<meta property="og:title" content="([^"]*)"', page)
            ch["name"] = m.group(1) if m else handle
            changed = True
        if not avatar.exists():
            m = re.search(r'<meta property="og:image" content="([^"]*)"', page)
            if not m:
                sys.exit(f"no avatar found for @{handle}")
            avatar.write_bytes(get(m.group(1)))
            print(f"avatar: @{handle}")
    if changed:
        LIST.write_text(json.dumps(channels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("channels.json updated")


if __name__ == "__main__":
    main()
