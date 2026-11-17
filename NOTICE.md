# Third-party material in PiTV

## CleanYourTV — design inspiration and wallpapers

The PiTV Kodi home screen (`kodi/build_home.py`) follows the look of the CleanYourTV
launcher: a black home, a rounded dock band, a "top shelf" with the focused item's
name and an ambient glow in its artwork colour, and a thin clock. No launcher code or
image assets from CleanYourTV are used, apart from the wallpapers below.

Repository: https://github.com/Gathin23/cleanyourtv

```
MIT License

Copyright (c) 2026 Gathin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Wallpapers (`kodi/wallpapers/src/`)

Eight landscape photos from CleanYourTV's `themes/ambient-glass/wallpapers`, released
under CC0 1.0 / the Unsplash License. Photographers and sources are listed in
`kodi/wallpapers/CREDITS-ambient-glass.md` (copied unchanged from that theme).
`kodi/build_home.py` dims them and darkens the bottom and left for the TV.

## Kodi skin

`kodi/setup-kodi.sh` makes `skin.pitv` on the Pi by copying Kodi's Estuary skin
(GPL-2.0-or-later, by phil65 and Ichabod Fletchman, shipped with Kodi) and adds the
PiTV `Home.xml` and alarm window. Estuary itself is not stored in this repository.

## Downloaded at install time (not in this repository)

- Pi-hole (EUPL-1.2), installed with its official installer from install.pi-hole.net.
- Kodi YouTube add-on `plugin.video.youtube` (GPL-2.0), from the official Kodi repository.
- YouTube channel avatars, fetched by `kodi/fetch_channels.py` for your own TV; they
  belong to their channels and are git-ignored.

## Fonts

- Outfit (ExtraLight 200, Light 300) — SIL Open Font License 1.1, `kodi/fonts/OFL.txt`.
- Garuda (TLWG, Debian `fonts-thai-tlwg-ttf`) — used on the Pi for Thai text.
