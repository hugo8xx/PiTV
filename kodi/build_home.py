# /// script
# dependencies = ["pillow"]
# ///
"""Build the PiTV Kodi home screen (dock + top shelf style, inspired by CleanYourTV's launcher).

Layout (1920x1080, pitch black):
  top-left   greeting                     top-right  thin clock + Thai date
  middle     "top shelf": name of the focused tile in large type + one line under it,
             over a soft glow in a colour taken from the tile's artwork
  bottom     the dock: a rounded translucent band of tiles; the focused tile grows,
             gets a white ring and its name underneath

Reads kodi/channels/channels.json (+ <handle>.src avatars) and writes:
  kodi/skin.pitv/xml/Home.xml, kodi/skin.pitv/media/pitv/*.png,
  kodi/plugin.video.pitv/resources/{channels.json,media/}

Run: uv run --script kodi/build_home.py      (kodi/deploy.sh runs it for you)
"""
import json
import shutil
import urllib.parse
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent
SKIN = ROOT / "skin.pitv"
MEDIA = SKIN / "media" / "pitv"
CHANNELS = json.loads((ROOT / "channels" / "channels.json").read_text())

# ---- colours (AARRGGBB)
TEXT, MUTED, DIM = "FFF5F4EF", "FFA9A7A0", "FF6F6E69"

# ---- rotating wallpaper (CC0 photos from CleanYourTV's themes, see kodi/wallpapers/CREDITS*)
WALLPAPER = True
WALLPAPER_MINUTES = 5
WALL_SRC = ROOT / "wallpapers" / "src"
WALL_OUT = MEDIA / "wallpapers"

# ---- dock geometry
TILE, GAP, PAD = 200, 44, 46
DOCK_Y, BAND_H = 742, 252
TILE_Y = DOCK_Y + (BAND_H - TILE) // 2

TH_DAYS = {"Monday": "จันทร์", "Tuesday": "อังคาร", "Wednesday": "พุธ", "Thursday": "พฤหัสบดี",
           "Friday": "ศุกร์", "Saturday": "เสาร์", "Sunday": "อาทิตย์"}
TH_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
             "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
GREETINGS = [(5, 12, "สวัสดีตอนเช้า"), (12, 18, "สวัสดีตอนบ่าย"), (18, 23, "สวัสดีตอนเย็น")]
NIGHT = "ดึกแล้ว พักผ่อนบ้างนะ"


# ================================================================== artwork
def rounded_mask(size, radius):
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def save_tile(img, name):
    """Rounded-square tile at 2x for crisp scaling."""
    s = TILE * 2
    img = img.convert("RGBA").resize((s, s), Image.LANCZOS)
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.paste(img, (0, 0), rounded_mask(s, int(s * 0.22)))
    out.save(MEDIA / f"tile_{name}.png")


def icon_tile(name, bg, glyph):
    """Solid-colour tile with a white glyph drawn by `glyph(draw, size)`."""
    s = TILE * 2
    img = Image.new("RGBA", (s, s), bg)
    glyph(ImageDraw.Draw(img), s)
    save_tile(img, name)


def dominant_colour(img):
    """A bright, saturated colour from the artwork for the glow."""
    small = img.convert("RGB").resize((64, 64))
    q = small.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:18]
    counts = sorted(q.getcolors(), reverse=True)
    best, score = (120, 120, 120), -1
    for count, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        sat = max(r, g, b) - min(r, g, b)
        s = count * (sat + 20) * (max(r, g, b) > 60)
        if s > score:
            best, score = (r, g, b), s
    return best


def glow(name, rgb):
    """Soft ambient glow, drawn small and blurred (Kodi scales it to full screen)."""
    w, h = 480, 270
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([-60, 40, 330, 300], fill=(*rgb, 150))
    d.ellipse([170, 90, 520, 330], fill=(*rgb, 70))
    img.filter(ImageFilter.GaussianBlur(55)).save(MEDIA / f"glow_{name}.png")


def wallpapers():
    """1920x1080 JPEGs, dimmed, darker at the bottom (dock) and on the left (title)."""
    if WALL_OUT.exists():
        shutil.rmtree(WALL_OUT)
    WALL_OUT.mkdir(parents=True)
    w, h = 1920, 1080
    shade = Image.new("L", (w, h), 0)
    px = shade.load()
    for y in range(h):
        for x in range(0, w, 4):
            v = 70                                          # overall dim
            v += int(150 * max(0, (y - 560) / 520) ** 1.3)  # bottom: dock
            v += int(70 * max(0, (900 - x) / 900) ** 1.5)   # left: shelf title
            v = min(v, 235)
            for dx in range(4):
                px[x + dx, y] = v
    black = Image.new("RGB", (w, h), (0, 0, 0))
    n = 0
    for src in sorted(WALL_SRC.glob("*.jpg")):
        img = Image.open(src).convert("RGB")
        img = img.resize((w, h), Image.LANCZOS) if img.size != (w, h) else img
        Image.composite(black, img, shade).save(WALL_OUT / src.name, quality=86, optimize=True)
        n += 1
    return n


def ring():
    """White focus ring that sits just outside a tile."""
    s = (TILE + 16) * 2
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([3, 3, s - 4, s - 4], radius=int(s * 0.23),
                                          outline=(255, 255, 255, 235), width=7)
    img.save(MEDIA / "ring.png")


def band(width):
    img = Image.new("RGBA", (width, BAND_H), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, width - 1, BAND_H - 1], radius=58,
                                          fill=(255, 255, 255, 22), outline=(255, 255, 255, 30), width=2)
    img.save(MEDIA / "dock.png")


def g_play(d, s):
    d.polygon([(s * .40, s * .30), (s * .40, s * .70), (s * .72, s * .50)], fill="white")


def g_film(d, s):
    w = int(s * .045)
    d.rounded_rectangle([s * .26, s * .26, s * .74, s * .74], radius=s * .06, outline="white", width=w)
    d.line([(s * .38, s * .26), (s * .38, s * .74)], fill="white", width=w)
    d.line([(s * .62, s * .26), (s * .62, s * .74)], fill="white", width=w)


def g_gear(d, s):
    import math
    c = s / 2
    for i in range(8):
        a = math.radians(i * 45)
        d.line([(c + s * .17 * math.cos(a), c + s * .17 * math.sin(a)),
                (c + s * .27 * math.cos(a), c + s * .27 * math.sin(a))], fill="white", width=int(s * .09))
    d.ellipse([c - s * .19, c - s * .19, c + s * .19, c + s * .19], fill="white")
    d.ellipse([c - s * .08, c - s * .08, c + s * .08, c + s * .08], fill=(58, 58, 60))


def g_power(d, s):
    w = int(s * .05)
    d.arc([s * .28, s * .30, s * .72, s * .74], start=-55, end=235, fill="white", width=w)
    d.line([(s / 2, s * .22), (s / 2, s * .50)], fill="white", width=w)


# ================================================================== tiles (dock order)
def tiles():
    """Return the dock as a list of dicts: id, key, name, sub, action, colour, live."""
    out, nid = [], 9001
    for ch in CHANNELS:
        src = Image.open(ROOT / "channels" / f"{ch['handle']}.src")
        save_tile(src, ch["handle"])
        live = ch.get("tile") == "live"
        if live:
            action = f'PlayMedia("plugin://plugin.video.pitv/?{urllib.parse.urlencode({"live": ch["id"]})}")'
            sub = "ดูสด · ถ้าไม่ไลฟ์จะเปิดคลิปล่าสุด"
        else:
            q = urllib.parse.urlencode({"channel": ch["id"], "name": ch["name"]})
            action = f'ActivateWindow(Videos,"plugin://plugin.video.pitv/?{q}",return)'
            sub = "คลิปล่าสุด 15 คลิป · มีปุ่มดูสด"
        out.append(dict(id=nid, key=ch["handle"], name=ch["name"], sub=sub, action=action,
                        colour=dominant_colour(src), live=live))
        nid += 1
    fixed = [
        ("youtube", "YouTube", "ค้นหาและเปิดคลิปทั้งหมด", (196, 43, 28), g_play,
         "ActivateWindow(Videos,plugin://plugin.video.youtube/,return)"),
        ("videos", "วิดีโอ", "ไฟล์ในเครื่องและในบ้าน", (24, 95, 165), g_film,
         "ActivateWindow(Videos,sources://video/,return)"),
        ("settings", "ตั้งค่า", "Kodi และ PiTV", (58, 58, 60), g_gear, "ActivateWindow(Settings)"),
        ("power", "ปิดทีวี", "พักหน้าจอ ทีวีเข้า standby", (40, 40, 42), g_power, "CECStandby"),
    ]
    for key, name, sub, rgb, glyph, action in fixed:
        icon_tile(key, rgb, glyph)
        out.append(dict(id=nid, key=key, name=name, sub=sub, action=action, colour=rgb, live=False))
        nid += 1
    return out


# ================================================================== xml helpers
def label(left, top, width, height, font, color, text, extra=""):
    return (f'\t\t<control type="label"><left>{left}</left><top>{top}</top><width>{width}</width>'
            f'<height>{height}</height><font>{font}</font><textcolor>{color}</textcolor>{extra}'
            f'<label>{text}</label></control>\n')


FADE = ('<animation effect="fade" time="350">VisibleChange</animation>')


def hour_cond(a, b):
    return f"Integer.IsGreaterOrEqual(System.Time(HH),{a}) + Integer.IsLess(System.Time(HH),{b})"


def header():
    x = []
    for a, b, text in GREETINGS:
        x.append(label(120, 64, 900, 50, "pitv_greet", MUTED, text, f"<visible>{hour_cond(a, b)}</visible>"))
    night = "[Integer.IsGreaterOrEqual(System.Time(HH),23) | Integer.IsLess(System.Time(HH),5)]"
    x.append(label(120, 64, 900, 50, "pitv_greet", MUTED, NIGHT, f"<visible>{night}</visible>"))
    x.append(label(1000, 30, 800, 150, "pitv_clock", TEXT, "$INFO[System.Time(HH:mm)]", "<align>right</align>"))
    # Thai date, right-aligned: grouplist laid out right-to-left would reverse words,
    # so build the line in a left-to-right grouplist anchored at the right edge.
    parts = []
    for en, th in TH_DAYS.items():
        parts.append(f'<control type="label"><width>auto</width><height>46</height><font>pitv_greet</font>'
                     f'<textcolor>{MUTED}</textcolor><label>วัน{th}ที่ </label>'
                     f'<visible>String.Contains(System.Date,{en})</visible></control>')
    parts.append(f'<control type="label"><width>auto</width><height>46</height><font>pitv_greet</font>'
                 f'<textcolor>{MUTED}</textcolor><label>$INFO[System.Date(d)] </label></control>')
    for i, m in enumerate(TH_MONTHS, 1):
        parts.append(f'<control type="label"><width>auto</width><height>46</height><font>pitv_greet</font>'
                     f'<textcolor>{MUTED}</textcolor><label>{m}</label>'
                     f'<visible>String.IsEqual(System.Date(MM),{i:02d})</visible></control>')
    x.append(f'\t\t<control type="grouplist"><left>1000</left><top>178</top><width>800</width><height>46</height>'
             f'<orientation>horizontal</orientation><align>right</align><itemgap>0</itemgap>{"".join(parts)}</control>\n')
    return "".join(x)


def shelf(ts):
    """Glow + big title + subtitle for whichever tile has focus."""
    x = []
    glow_tint = "90FFFFFF" if WALLPAPER else "FFFFFFFF"   # softer glow over a photo
    for t in ts:
        vis = f"<visible>Control.HasFocus({t['id']})</visible>{FADE}"
        x.append(f'\t\t<control type="image"><left>-200</left><top>-60</top><width>2320</width><height>1300</height>'
                 f'<texture colordiffuse="{glow_tint}">pitv/glow_{t["key"]}.png</texture>{vis}</control>\n')
    for t in ts:
        vis = f"<visible>Control.HasFocus({t['id']})</visible>{FADE}"
        x.append(label(120, 420, 1680, 120, "pitv_shelf", TEXT, escape(t["name"]), vis))
        sub = ("[COLOR FFE24B4A]● LIVE[/COLOR]  " if t["live"] else "") + escape(t["sub"])
        x.append(label(124, 545, 1680, 56, "pitv_greet", MUTED, sub, vis))
    return "".join(x)


def dock(ts):
    n = len(ts)
    width = n * TILE + (n - 1) * GAP + 2 * PAD
    band(width)
    x0 = (1920 - width) // 2
    out = [f'\t\t<control type="image"><left>{x0}</left><top>{DOCK_Y}</top><width>{width}</width>'
           f'<height>{BAND_H}</height><texture>pitv/dock.png</texture></control>\n']
    zoom = ('<animation effect="zoom" end="110" center="auto" time="180" tween="cubic" easing="out">Focus</animation>'
            '<animation effect="zoom" start="110" end="100" center="auto" time="180">Unfocus</animation>')
    for i, t in enumerate(ts):
        x = x0 + PAD + i * (TILE + GAP)
        left = ts[i - 1]["id"] if i else ts[-1]["id"]
        right = ts[(i + 1) % n]["id"]
        # tile = a button whose textures are the artwork (dimmed when not focused)
        out.append(
            f'\t\t<control type="button" id="{t["id"]}"><left>{x}</left><top>{TILE_Y}</top>'
            f'<width>{TILE}</width><height>{TILE}</height><label></label>'
            f'<texturenofocus colordiffuse="FFB8B8B8">pitv/tile_{t["key"]}.png</texturenofocus>'
            f'<texturefocus>pitv/tile_{t["key"]}.png</texturefocus>'
            f'<onleft>{left}</onleft><onright>{right}</onright><onup>{t["id"]}</onup><ondown>{t["id"]}</ondown>'
            f'<onclick>{escape(t["action"])}</onclick>{zoom}</control>\n')
        vis = f"<visible>Control.HasFocus({t['id']})</visible>"
        # ring + name beneath, only on the focused tile (sized for the 110% zoom)
        r = int((TILE + 16) * 1.10)
        out.append(f'\t\t<control type="image"><left>{x + TILE // 2 - r // 2}</left><top>{TILE_Y + TILE // 2 - r // 2}</top>'
                   f'<width>{r}</width><height>{r}</height><texture>pitv/ring.png</texture>{vis}{FADE}</control>\n')
        out.append(label(x - 60, DOCK_Y + BAND_H + 14, TILE + 120, 44, "font27", TEXT, escape(t["name"]),
                         f"<align>center</align>{vis}"))
        if t["live"]:
            out.append(f'\t\t<control type="image"><left>{x + 12}</left><top>{TILE_Y + 12}</top><width>70</width>'
                       f'<height>30</height><texture colordiffuse="FFE24B4A">colors/white.png</texture></control>\n')
            out.append(label(x + 12, TILE_Y + 12, 70, 30, "font12", "FFFFFFFF", "LIVE",
                             "<align>center</align><aligny>center</aligny>"))
    return "".join(out)


# ================================================================== build
def build():
    MEDIA.mkdir(parents=True, exist_ok=True)
    ts = tiles()
    for t in ts:
        glow(t["key"], t["colour"])
    ring()
    wall = ""
    if WALLPAPER and (n := wallpapers()):
        wall = (f'\t\t<control type="multiimage"><left>0</left><top>0</top><width>1920</width><height>1080</height>'
                f'<imagepath>special://skin/media/pitv/wallpapers/</imagepath>'
                f'<timeperimage>{WALLPAPER_MINUTES * 60000}</timeperimage><fadetime>2500</fadetime>'
                f'<randomize>true</randomize><loop>yes</loop><aspectratio>scale</aspectratio></control>\n')
        print(f"{n} wallpapers, rotating every {WALLPAPER_MINUTES} min")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!-- GENERATED by kodi/build_home.py - edit that script, not this file. -->\n"
        "<window>\n\t<defaultcontrol always=\"true\">9001</defaultcontrol>\n"
        "\t<backgroundcolor>FF000000</backgroundcolor>\n\t<controls>\n"
        '\t\t<control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height>'
        '<texture colordiffuse="FF000000">colors/white.png</texture></control>\n'
        + wall + shelf(ts) + header() + dock(ts)
        + "\t</controls>\n</window>\n"
    )
    (SKIN / "xml" / "Home.xml").write_text(xml, encoding="utf-8")

    res = ROOT / "plugin.video.pitv" / "resources"
    (res / "media").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "channels" / "channels.json", res / "channels.json")
    for ch in CHANNELS:
        shutil.copy(MEDIA / f"tile_{ch['handle']}.png", res / "media" / f"ch_{ch['handle']}.png")
    print(f"Home.xml written: {len(ts)} tiles ({len(CHANNELS)} channels)")


if __name__ == "__main__":
    build()
