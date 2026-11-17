"""PiTV channels: latest videos of favourite YouTube channels via public RSS (no API key).

URLs:
  plugin://plugin.video.pitv/                      list favourite channels
  plugin://plugin.video.pitv/?channel=UC...        latest 15 videos of a channel
Playback is handed to plugin.video.youtube (works without an API key).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import xbmcaddon
import xbmcgui
import xbmcplugin

HANDLE = int(sys.argv[1])
ARGS = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))
ADDON = xbmcaddon.Addon()
HERE = ADDON.getAddonInfo("path")
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "m": "http://search.yahoo.com/mrss/",
}
CHANNEL_ID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


def channels():
    with open(os.path.join(HERE, "resources", "channels.json"), encoding="utf-8") as f:
        return json.load(f)


def url(**kw):
    return sys.argv[0] + "?" + urllib.parse.urlencode(kw)


def list_channels():
    for ch in channels():
        li = xbmcgui.ListItem(ch["name"])
        icon = os.path.join(HERE, "resources", "media", f"ch_{ch['handle']}.png")
        li.setArt({"thumb": icon, "icon": icon})
        xbmcplugin.addDirectoryItem(HANDLE, url(channel=ch["id"], name=ch["name"]), li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def list_videos(channel_id, name):
    if not (channel_id.startswith("UC") and len(channel_id) == 24 and set(channel_id) <= CHANNEL_ID_CHARS):
        xbmcgui.Dialog().notification("PiTV", "channel id ไม่ถูกต้อง", xbmcgui.NOTIFICATION_ERROR)
        return xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    try:
        req = urllib.request.Request(FEED.format(channel_id), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            root = ET.fromstring(r.read())
    except Exception as e:  # noqa: BLE001 - show any network/parse error on screen
        xbmcgui.Dialog().notification("PiTV", f"โหลดรายการไม่ได้: {e}", xbmcgui.NOTIFICATION_ERROR, 6000)
        return xbmcplugin.endOfDirectory(HANDLE, succeeded=False)

    xbmcplugin.setPluginCategory(HANDLE, name)
    xbmcplugin.setContent(HANDLE, "videos")
    live = xbmcgui.ListItem("[COLOR FFE24B4A]●[/COLOR] ดูสด (ถ้ากำลังไลฟ์)")
    live.setProperty("IsPlayable", "true")
    live.getVideoInfoTag().setPlot("เปิดไลฟ์ของช่องนี้ ถ้าไม่ได้ไลฟ์อยู่จะเปิดคลิปล่าสุดแทน")
    xbmcplugin.addDirectoryItem(HANDLE, url(live=channel_id), live, isFolder=False)
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        title = e.findtext("a:title", namespaces=NS) or vid
        published = (e.findtext("a:published", namespaces=NS) or "")[:10]
        thumb = e.find("m:group/m:thumbnail", NS)
        desc = e.findtext("m:group/m:description", namespaces=NS) or ""
        li = xbmcgui.ListItem(title)
        if thumb is not None:
            li.setArt({"thumb": thumb.get("url"), "fanart": thumb.get("url")})
        info = li.getVideoInfoTag()
        info.setTitle(title)
        info.setPlot(desc)
        info.setPremiered(published)
        info.setStudios([name])
        li.setProperty("IsPlayable", "true")
        play = f"plugin://plugin.video.youtube/play/?video_id={vid}"
        xbmcplugin.addDirectoryItem(HANDLE, play, li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def play_live(channel_id):
    """Resolve the channel's live stream (or newest video) and hand it to Kodi."""
    sys.path.insert(0, "/usr/local/lib/pitv")
    import pitv_youtube as yt

    try:
        found = yt.live_video(channel_id)
        if not found:
            xbmcgui.Dialog().notification("PiTV", "ช่องนี้ไม่ได้ไลฟ์อยู่ เปิดคลิปล่าสุดแทน", xbmcgui.NOTIFICATION_INFO, 5000)
            found = yt.newest_video(channel_id)
    except Exception as e:  # noqa: BLE001
        xbmcgui.Dialog().notification("PiTV", f"เปิดไลฟ์ไม่ได้: {e}", xbmcgui.NOTIFICATION_ERROR, 6000)
        found = None
    if not found:
        return xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
    li = xbmcgui.ListItem(found[1], path=yt.play_url(found[0]))
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


if "live" in ARGS:
    play_live(ARGS["live"])
elif "channel" in ARGS:
    list_videos(ARGS["channel"], ARGS.get("name", "YouTube"))
else:
    list_channels()
