#!/usr/bin/env python3
"""
Genera nowplaying.svg — tarjeta de TrickFM con la portada real de la cancion.

Lee la API de AzuraCast, descarga la caratula, la incrusta en base64 dentro
del SVG (asi el SVG es autocontenido y no depende de que GitHub pueda
alcanzar el servidor de arte) y dibuja la tarjeta con la paleta del perfil.

Uso:  python nowplaying.py <URL_API> <fichero_salida>
"""
import base64
import html
import json
import sys
import urllib.request

API = sys.argv[1] if len(sys.argv) > 1 else "http://207.180.223.205:8081/api/nowplaying/1"
OUT = sys.argv[2] if len(sys.argv) > 2 else "nowplaying.svg"

# --- Paleta del perfil ------------------------------------------------------
BG, INK, MUTE, ACCENT, LINE = "#F0EEE9", "#111111", "#6B6B6B", "#3BA7E8", "#E3E0D9"

W, H = 880, 250
PAD = 26
ART = H - PAD * 2          # portada cuadrada
TX = PAD + ART + 28        # inicio de la columna de texto


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "trickfm-card"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def ellipsis(s, n):
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def esc(s):
    return html.escape(s or "", quote=True)


# --- Datos ------------------------------------------------------------------
try:
    d = json.loads(fetch(API).decode("utf-8"))
except Exception as e:
    sys.stderr.write("No se pudo leer la API: %s\n" % e)
    sys.exit(1)

np = d.get("now_playing") or {}
song = np.get("song") or {}
nxt = ((d.get("playing_next") or {}).get("song") or {}).get("text") or ""

title = ellipsis(song.get("title") or song.get("text") or "Sin titulo", 38)
artist = ellipsis(song.get("artist") or "", 42)
listeners = (d.get("listeners") or {}).get("current", 0)
is_live = bool((d.get("live") or {}).get("is_live"))
duration = max(int(np.get("duration") or 0), 1)
elapsed = min(max(int(np.get("elapsed") or 0), 0), duration)
pct = elapsed / duration


def mmss(s):
    return "%d:%02d" % (s // 60, s % 60)


# --- Portada incrustada -----------------------------------------------------
art_href = ""
try:
    raw = fetch(song.get("art"), timeout=25)
    # La caratula original ronda los 250 KB y este SVG se regenera cada
    # pocos minutos. Sin reescalar, el repositorio creceria varios GB al año.
    mime = "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    try:
        import io as _io

        from PIL import Image

        im = Image.open(_io.BytesIO(raw)).convert("RGB")
        im.thumbnail((320, 320), Image.LANCZOS)
        buf = _io.BytesIO()
        im.save(buf, format="JPEG", quality=78, optimize=True)
        raw, mime = buf.getvalue(), "image/jpeg"
    except ImportError:
        pass
    art_href = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode())
except Exception as e:
    sys.stderr.write("Aviso: sin caratula (%s)\n" % e)

# --- Barras del ecualizador -------------------------------------------------
bars = []
heights = [13, 22, 9, 26, 16, 30, 11, 20, 25, 14]
for i, h0 in enumerate(heights):
    x = TX + i * 9
    dur = 0.75 + (i % 4) * 0.22
    bars.append(
        '<rect x="%d" y="%d" width="5" height="%d" rx="2.5" fill="%s" opacity="0.9">'
        '<animate attributeName="height" values="%d;%d;%d" dur="%.2fs" '
        'repeatCount="indefinite" calcMode="spline" '
        'keySplines="0.4 0 0.2 1; 0.4 0 0.2 1" keyTimes="0;0.5;1"/>'
        '<animate attributeName="y" values="%d;%d;%d" dur="%.2fs" '
        'repeatCount="indefinite" calcMode="spline" '
        'keySplines="0.4 0 0.2 1; 0.4 0 0.2 1" keyTimes="0;0.5;1"/>'
        "</rect>"
        % (x, H - PAD - h0, h0, ACCENT,
           h0, max(4, h0 // 3), h0, dur,
           H - PAD - h0, H - PAD - max(4, h0 // 3), H - PAD - h0, dur)
    )
eq = "".join(bars)

art_block = (
    '<image x="%d" y="%d" width="%d" height="%d" href="%s" '
    'preserveAspectRatio="xMidYMid slice" clip-path="url(#r)"/>'
    % (PAD, PAD, ART, ART, art_href)
    if art_href
    else '<rect x="%d" y="%d" width="%d" height="%d" rx="14" fill="%s"/>'
         '<text x="%d" y="%d" font-size="42" fill="%s" text-anchor="middle" '
         'opacity="0.5">♫</text>'
         % (PAD, PAD, ART, ART, LINE, PAD + ART // 2, PAD + ART // 2 + 15, MUTE)
)

bar_w = W - TX - PAD
state = "EN DIRECTO" if is_live else "NOW PLAYING"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"
     aria-label="TrickFM — sonando ahora: {esc(title)} de {esc(artist)}">
  <defs>
    <clipPath id="r"><rect x="{PAD}" y="{PAD}" width="{ART}" height="{ART}" rx="14"/></clipPath>
    <linearGradient id="prog" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{ACCENT}"/>
      <stop offset="100%" stop-color="#1E7CC2"/>
    </linearGradient>
    <filter id="sh" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="8" flood-color="#111111" flood-opacity="0.13"/>
    </filter>
  </defs>

  <rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{LINE}"/>

  <g filter="url(#sh)">{art_block}</g>

  <g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">
    <circle cx="{TX+4}" cy="{PAD+11}" r="4" fill="{ACCENT}">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/>
    </circle>
    <text x="{TX+16}" y="{PAD+15}" font-size="11" fill="{ACCENT}"
          letter-spacing="2.4" font-weight="700">{state}</text>
    <text x="{W-PAD}" y="{PAD+15}" font-size="11" fill="{MUTE}"
          letter-spacing="1.6" text-anchor="end">TRICKFM · {listeners} OYENTES</text>

    <text x="{TX}" y="{PAD+58}" font-size="26" fill="{INK}"
          font-weight="700" font-family="system-ui,-apple-system,Segoe UI,sans-serif">{esc(title)}</text>
    <text x="{TX}" y="{PAD+86}" font-size="15" fill="{MUTE}"
          font-family="system-ui,-apple-system,Segoe UI,sans-serif">{esc(artist)}</text>

    <rect x="{TX}" y="{PAD+108}" width="{bar_w}" height="5" rx="2.5" fill="{LINE}"/>
    <rect x="{TX}" y="{PAD+108}" width="{int(bar_w*pct)}" height="5" rx="2.5" fill="url(#prog)"/>
    <text x="{TX}" y="{PAD+131}" font-size="11" fill="{MUTE}">{mmss(elapsed)}</text>
    <text x="{W-PAD}" y="{PAD+131}" font-size="11" fill="{MUTE}" text-anchor="end">{mmss(duration)}</text>

    <text x="{TX+100}" y="{H-PAD-2}" font-size="11" fill="{MUTE}">
      SIGUIENTE · {esc(ellipsis(nxt, 46))}</text>
  </g>

  {eq}
</svg>
'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)

print("OK  %s  |  %s — %s  |  %s/%s  |  %d oyentes  |  caratula: %s"
      % (OUT, title, artist, mmss(elapsed), mmss(duration), listeners,
         "si" if art_href else "NO"))
