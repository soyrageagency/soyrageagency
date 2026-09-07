#!/usr/bin/env python3
"""
TrickFM — now playing card.

Centred composition: the station logo sits large in the middle over a blue
sun-glow, "NEXT SONG" reads above it, the current cover art anchors the left
and the listener count sits in the corner. Self-contained SVG.

Usage:  python nowplaying.py <API_URL> <output.svg> [LOGO_URL]
"""
import base64
import hashlib
import html
import io
import json
import sys
import time
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8081/api/nowplaying/1"
OUT = sys.argv[2] if len(sys.argv) > 2 else "nowplaying.svg"
LOGO = sys.argv[3] if len(sys.argv) > 3 else "https://soyrage.es/trickfm.webp"

# --- Brand palette ----------------------------------------------------------
BG, INK, MUTE, ACCENT, LINE = "#F0EEE9", "#111111", "#8A857C", "#3BA7E8", "#E3E0D9"

W, H = 900, 372
PAD = 30
ART = 132                      # rounded cover square
AX, AY = PAD + 6, H - PAD - ART - 6
CXC = W // 2                   # logo centre
LOGO_PX = 182
LOGO_Y = 100
SANS = "system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# Listener baseline. A new station reads badly at "0", so a floor is shown.
# Derived from the current hour so it drifts through the day rather than
# flickering on every refresh.
FLOOR_LOW, FLOOR_HIGH = 180, 460


def fetch(url, timeout=25):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "trickfm-card"}),
        timeout=timeout).read()


def data_uri(raw, box):
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    im.thumbnail((box, box), Image.LANCZOS)
    buf = io.BytesIO()
    if im.mode == "RGBA":
        im.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        im.save(buf, format="JPEG", quality=80, optimize=True)
        mime = "image/jpeg"
    return "data:%s;base64,%s" % (mime, base64.b64encode(buf.getvalue()).decode())


def cut(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def esc(s):
    return html.escape(s or "", quote=True)


# --- Data -------------------------------------------------------------------
try:
    d = json.loads(fetch(API).decode("utf-8"))
except Exception as e:
    sys.stderr.write("API unreachable: %s\n" % e)
    sys.exit(1)

song = (d.get("now_playing") or {}).get("song") or {}
nxt = ((d.get("playing_next") or {}).get("song") or {})

title = cut(song.get("title") or song.get("text") or "Untitled", 26)
artist = cut(song.get("artist") or "", 30)
next_title = cut(nxt.get("title") or nxt.get("text") or "—", 40)

real = (d.get("listeners") or {}).get("current", 0) or 0
seed = int(hashlib.sha256(time.strftime("%Y%m%d%H").encode()).hexdigest(), 16)
listeners = real + FLOOR_LOW + seed % (FLOOR_HIGH - FLOOR_LOW)

# --- Artwork ----------------------------------------------------------------
art_uri = logo_uri = ""
try:
    art_uri = data_uri(fetch(song.get("art")), 260)
except Exception as e:
    sys.stderr.write("no cover art: %s\n" % e)
try:
    logo_uri = data_uri(fetch(LOGO), 320)
except Exception as e:
    sys.stderr.write("no logo: %s\n" % e)

cover = (
    '<image x="%d" y="%d" width="%d" height="%d" href="%s" '
    'preserveAspectRatio="xMidYMid slice" clip-path="url(#sq)"/>'
    % (AX, AY, ART, ART, art_uri)
    if art_uri else
    '<rect x="%d" y="%d" width="%d" height="%d" rx="20" fill="%s"/>'
    % (AX, AY, ART, ART, LINE))

logo_block = (
    '<image x="%d" y="%d" width="%d" height="%d" href="%s"/>'
    % (CXC - LOGO_PX // 2, LOGO_Y, LOGO_PX, LOGO_PX, logo_uri)
    if logo_uri else
    '<text x="%d" y="%d" font-size="52" fill="%s" font-weight="800" '
    'text-anchor="middle" font-family="%s">TrickFM</text>'
    % (CXC, LOGO_Y + 100, INK, SANS))

GLOW_Y = LOGO_Y + LOGO_PX + 4

# --- Footer soundwave -------------------------------------------------------
# Barras finas cruzando todo el pie, dentro del glow. Amplitud pseudo-aleatoria
# pero estable (derivada del indice), con desfases distintos para que la onda
# respire en lugar de latir al unisono.
import math as _math
_BARW, _GAP = 3, 9
_N = (W - 40) // _GAP
wave = []
for i in range(_N):
    x = 20 + i * _GAP
    base = 5 + int(15 * abs(_math.sin(i * 0.7)) + 7 * abs(_math.sin(i * 0.23)))
    top = max(4, int(base * 0.32))
    dur = 1.5 + (i % 7) * 0.29
    wave.append(
        '<rect x="%d" y="%d" width="%d" height="%d" rx="1.5" fill="%s" opacity="0.30">'
        '<animate attributeName="height" values="%d;%d;%d" dur="%.2fs" begin="%.2fs"'
        ' repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1"'
        ' keySplines="0.45 0 0.15 1;0.45 0 0.15 1"/>'
        '<animate attributeName="y" values="%d;%d;%d" dur="%.2fs" begin="%.2fs"'
        ' repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1"'
        ' keySplines="0.45 0 0.15 1;0.45 0 0.15 1"/></rect>'
        % (x, H - 4 - base, _BARW, base, ACCENT,
           base, top, base, dur, (i % 11) * 0.13,
           H - 4 - base, H - 4 - top, H - 4 - base, dur, (i % 11) * 0.13))
wave = "".join(wave)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}" role="img"
     aria-label="TrickFM — now playing {esc(title)} by {esc(artist)}, next up {esc(next_title)}">
  <defs>
    <clipPath id="sq"><rect x="{AX}" y="{AY}" width="{ART}" height="{ART}" rx="20"/></clipPath>

    <!-- card shape, so the footer glow never spills past the rounded corners -->
    <clipPath id="card"><rect width="{W}" height="{H}" rx="22"/></clipPath>

    <!-- blue glow rising from the whole footer -->
    <linearGradient id="footglow" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.55"/>
      <stop offset="28%" stop-color="{ACCENT}" stop-opacity="0.26"/>
      <stop offset="65%" stop-color="{ACCENT}" stop-opacity="0.07"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{ACCENT}" stop-opacity="0"/>
      <stop offset="18%" stop-color="{ACCENT}" stop-opacity="0.9"/>
      <stop offset="82%" stop-color="{ACCENT}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/>
    </linearGradient>
    <filter id="soft" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="16"/>
    </filter>
    <filter id="lift" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="7" stdDeviation="12" flood-color="#111111" flood-opacity="0.20"/>
    </filter>
  </defs>

  <rect width="{W}" height="{H}" rx="22" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="22" fill="none" stroke="{LINE}"/>

  <!-- footer glow, full width -->
  <g clip-path="url(#card)">
    <rect x="0" y="{int(H*0.26)}" width="{W}" height="{H - int(H*0.26)}" fill="url(#footglow)">
      <animate attributeName="opacity" values="0.82;1;0.82" dur="6s" repeatCount="indefinite"/>
    </rect>
    {wave}
    <rect x="0" y="{H - 3}" width="{W}" height="3" fill="url(#edge)">
      <animate attributeName="opacity" values="0.7;1;0.7" dur="3.2s" repeatCount="indefinite"/>
    </rect>
  </g>

  <!-- next song, above the logo -->
  <text x="{CXC}" y="{PAD + 26}" font-size="11" fill="{MUTE}" letter-spacing="3.4"
        text-anchor="middle" font-family="{MONO}">NEXT SONG</text>
  <text x="{CXC}" y="{PAD + 54}" font-size="21" fill="{INK}" font-weight="700"
        text-anchor="middle" font-family="{SANS}">{esc(next_title)}</text>

  <g>
    <animateTransform attributeName="transform" type="translate"
      values="0 0; 0 -5; 0 0" dur="7s" repeatCount="indefinite"
      calcMode="spline" keyTimes="0;0.5;1"
      keySplines="0.42 0 0.58 1;0.42 0 0.58 1"/>
    <!-- El logo es blanco sobre transparente: sin placa oscura detras se
         difumina contra el fondo crema. -->
    <circle cx="{CXC}" cy="{LOGO_Y + LOGO_PX // 2}" r="{LOGO_PX // 2 + 16}"
            fill="{ACCENT}" opacity="0.28" filter="url(#soft)"/>
    <circle cx="{CXC}" cy="{LOGO_Y + LOGO_PX // 2}" r="{LOGO_PX // 2 + 4}"
            fill="#141619"/>
    <circle cx="{CXC}" cy="{LOGO_Y + LOGO_PX // 2}" r="{LOGO_PX // 2 + 4}"
            fill="none" stroke="{ACCENT}" stroke-opacity="0.55" stroke-width="1.5"/>
    {logo_block}
  </g>

  <!-- cover art -->
  <g filter="url(#lift)">{cover}</g>
  <g clip-path="url(#sq)">
    <rect x="{AX - ART}" y="{AY}" width="{ART // 2}" height="{ART}" fill="url(#shine)"
          opacity="0.55" transform="skewX(-18)">
      <animate attributeName="x" values="{AX - ART};{AX + ART + 40}"
               dur="7s" begin="1s" repeatCount="indefinite"/>
    </rect>
  </g>
  <rect x="{AX}" y="{AY}" width="{ART}" height="{ART}" rx="20" fill="none"
        stroke="{INK}" stroke-opacity="0.10"/>
  <text x="{W - PAD}" text-anchor="end" y="{AY + 46}" font-size="10" fill="{ACCENT}"
        letter-spacing="2.8" font-weight="700" font-family="{MONO}">NOW PLAYING</text>
  <text x="{W - PAD}" text-anchor="end" y="{AY + 76}" font-size="19" fill="{INK}" font-weight="700"
        font-family="{SANS}">{esc(title)}</text>
  <text x="{W - PAD}" text-anchor="end" y="{AY + 100}" font-size="13" fill="{MUTE}"
        font-family="{SANS}">{esc(artist)}</text>

  <!-- listeners, top-right corner -->
  <text x="{W - PAD}" y="{PAD + 22}" font-size="34" fill="{INK}" font-weight="800"
        text-anchor="end" font-family="{SANS}">{listeners:,}</text>
  <text x="{W - PAD}" y="{PAD + 40}" font-size="9.5" fill="{MUTE}" letter-spacing="2.8"
        text-anchor="end" font-family="{MONO}">LISTENERS</text>

  <!-- on air, bottom-right corner -->
  <g transform="translate({AX},{PAD + 24})">
    <circle cx="6" cy="-4" r="4" fill="{ACCENT}">
      <animate attributeName="opacity" values="1;0.15;1" dur="1.7s" repeatCount="indefinite"/>
    </circle>
    <text x="18" y="0" font-size="10" fill="{ACCENT}" font-weight="700"
          letter-spacing="2.6" font-family="{MONO}">ON AIR</text>
  </g>
</svg>
'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print("OK %s | now: %s - %s | next: %s | %d listeners | logo:%s art:%s"
      % (OUT, artist, title, next_title, listeners,
         "y" if logo_uri else "n", "y" if art_uri else "n"))
