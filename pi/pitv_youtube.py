"""Small YouTube helpers for PiTV that need no API key.

Installed on the Pi as /usr/local/lib/pitv/pitv_youtube.py and imported by
pitv-ctl, pitv-alarm and the Kodi add-on plugin.video.pitv.

  channel_id("@Krobkruakao3") -> "UCirZPTc9IoKM_DsA9aKbc4g"
  live_video("UC...")         -> ("HVOMJ5idbS4", "title")  or None when not live
  newest_video("UC...")       -> ("gIIMMv9Hld0", "title")  from the public RSS feed
"""
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "th,en"}
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
HANDLE_RE = re.compile(r"^@?[A-Za-z0-9._-]{3,100}$")


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _channel_url(channel):
    """Accept a UC id, @handle, or a youtube.com/@handle or /channel/UC... URL."""
    c = channel.strip()
    m = re.search(r"youtube\.com/(?:channel/(UC[A-Za-z0-9_-]{22})|(@[A-Za-z0-9._-]+))", c)
    if m:
        c = m.group(1) or m.group(2)
    if ID_RE.match(c):
        return f"https://www.youtube.com/channel/{c}"
    if HANDLE_RE.match(c):
        return "https://www.youtube.com/@" + urllib.parse.quote(c.lstrip("@"))
    raise ValueError("channel must be a UC... id, an @handle, or a youtube.com channel URL")


def channel_id(channel):
    c = channel.strip()
    if ID_RE.match(c):
        return c
    page = _get(_channel_url(c))
    m = re.search(r'"(?:externalId|channelId)":"(UC[A-Za-z0-9_-]{22})"', page)
    if not m:
        raise ValueError(f"could not find the channel id for {channel}")
    return m.group(1)


def live_video(channel):
    """Return (video_id, title) if the channel is live right now, else None."""
    page = _get(_channel_url(channel) + "/live")
    # When the channel is live, /live points (canonical link) at the live video.
    # The page served for /channel/UC.../live has no "isLiveNow", only "isLive":true,
    # while the /@handle/live page has both - accept either, but skip scheduled streams.
    canon = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"', page)
    live = '"isLiveNow":true' in page or '"isLive":true' in page
    if not canon or not live or '"isUpcoming":true' in page:
        return None
    t = re.search(r'<meta name="title" content="([^"]*)"', page)
    return canon.group(1), html.unescape(t.group(1)) if t else canon.group(1)


def newest_video(channel):
    root = ET.fromstring(_get(FEED.format(channel_id(channel))))
    e = root.find("a:entry", NS)
    if e is None:
        return None
    return e.findtext("yt:videoId", namespaces=NS), e.findtext("a:title", namespaces=NS)


def play_url(video_id):
    return f"plugin://plugin.video.youtube/play/?video_id={video_id}"
