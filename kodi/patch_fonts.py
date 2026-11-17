"""Add PiTV fonts to the skin's Font.xml (every fontset). Runs ON the Pi; idempotent.

  pitv_clock  Outfit ExtraLight (Latin digits only) - the thin clock
  pitv_shelf  Garuda Bold (Thai)                     - big top-shelf title
  pitv_greet  Garuda (Thai)                          - greeting, date, subtitles
"""
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/pi/.kodi/addons/skin.pitv/xml/Font.xml")
FONTS = """
		<font><name>pitv_clock</name><filename>Outfit-200.ttf</filename><size>132</size></font>
		<font><name>pitv_shelf</name><filename>NotoSans-Bold.ttf</filename><size>84</size></font>
		<font><name>pitv_greet</name><filename>NotoSans-Regular.ttf</filename><size>34</size></font>"""

xml = path.read_text(encoding="utf-8")
xml = re.sub(r"\s*<font><name>pitv_[a-z]+</name>.*?</font>", "", xml)          # drop old copies
xml, n = re.subn(r"(<fontset [^>]*>)", r"\1" + FONTS, xml)
path.write_text(xml, encoding="utf-8")
print(f"PiTV fonts added to {n} fontset(s)")
