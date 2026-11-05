#!/usr/bin/env python3
"""Generate the profile artwork in assets/: a Kansas City-after-dark synthwave set.

Run from the repo root (fontTools is fetched on the fly; nothing is installed):

    uv run --no-project --with fonttools python tools/build_assets.py

GitHub serves README images through a proxy that can't load web fonts, so every
display word is baked to <path> outlines from the fonts in tools/fonts/ (OFL /
Apache-2.0, licences alongside). Small labels use a system monospace stack with
fixed-width cells (textLength), so layout survives whatever font the viewer has.

Every SVG is fully visible with animation off (static renderers, reduced motion):
animations only dip opacity briefly (a neon sputter), never hide things at rest.
"""

import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
ASSETS = ROOT / "assets"

# ---- CONFIG (edit me) -------------------------------------------------------
HANDLE = "THEtheChad"
PLACE = "KANSAS CITY, MO"
TAGLINE = "AGENTIC SDLC / AI / HARDWARE"
HEADERS = (  # (file stem, index, script word, alt text)
    ("h-about", "01", "about", "About"),
    ("h-stack", "02", "the stack", "The stack"),
    ("h-lately", "03", "lately", "Lately"),
)
SIDE_A = ("Claude Code · Codex", "Multi-agent orchestration", "Plan → build → review loops", "MCP servers · hooks", "Worktrees & guardrails")
SIDE_B = ("TypeScript · React · Next.js", "Node.js · Python · Bash", "Arduino · ESP · STM32", "Anything with a serial port")
LINER_CAPTION = "recorded in Kansas City"
# -----------------------------------------------------------------------------

# Palette: The Midnight's dusk sky + React Miami's neon pink; cyan drone lights.
NIGHT, INK = "#0d0b14", "#07060d"
SKY = ("#0b0620", "#1b1240", "#4b1d6b", "#b0306a", "#ff8a6b")
VIOLET, RIM = "#2a1450", "#3a1f5c"
PINK, PINK_SOFT, MAGENTA = "#ff3ea5", "#ff65b8", "#ff10f0"
CYAN, CYAN_DEEP, CORE = "#2de2e6", "#1b6fd6", "#e6fdff"
WARM, TEXT, MUTED = "#ffcf7a", "#f3e9ff", "#b8a6d9"
RED, RED_GLOW, DRONE = "#ff4433", "#ff2a1f", "#7f89bf"  # Western Auto neon; drone frames
PINK_ON_WHITE, CYAN_ON_WHITE = "#c2186b", "#0e7490"

MONO = (
    "ui-monospace,'Geist Mono','SFMono-Regular','Cascadia Mono',Consolas,Menlo,"
    "'DejaVu Sans Mono','Liberation Mono',monospace"
)
MONO_CW = 0.6  # monospace advance per em; every label gets exact cell widths

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }"


def n(v: float) -> str:
    """Compact number formatting for path data."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


class Script:
    """Outline text from a font file into a single SVG path."""

    def __init__(self, filename: str):
        self.font = TTFont(FONTS / filename)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upm = self.font["head"].unitsPerEm

    def width(self, text: str, size: float) -> float:
        return sum(self.glyphs[self.cmap[ord(c)]].width for c in text) * size / self.upm

    def path(self, text: str, size: float, x: float = 0, y: float = 0) -> str:
        s = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=n)
        cursor = 0.0
        for c in text:
            glyph = self.glyphs[self.cmap[ord(c)]]
            glyph.draw(TransformPen(pen, (s, 0, 0, -s, x + cursor * s, y)))
            cursor += glyph.width
        return pen.getCommands()


def label(x: float, y: float, s: str, size: float, fill: str, anchor: str = "start", spacing: float = 0, extra: str = "") -> str:
    """Monospace text with exact cell widths so fallback fonts can't reflow it."""
    length = len(s) * size * MONO_CW + (len(s) - 1) * spacing
    if anchor == "middle":
        x -= length / 2
    elif anchor == "end":
        x -= length
    return (
        f'<text x="{n(x)}" y="{n(y)}" font-size="{size}" textLength="{n(length)}" lengthAdjust="spacingAndGlyphs" '
        f'fill="{fill}"{extra}>{escape(s)}</text>'
    )


def neon_filter(fid: str, color: str, blurs: tuple[float, ...], strength: int = 2) -> str:
    """React Miami-style neon: a crisp core over stacked coloured halos."""
    layers = "".join(f'<feGaussianBlur in="SourceAlpha" stdDeviation="{b}" result="b{i}"/>' for i, b in enumerate(blurs))
    merged = "".join(f'<feMergeNode in="b{i}"/>' for i in reversed(range(len(blurs))))
    halos = '<feMergeNode in="glow"/>' * strength
    return (
        f'<filter id="{fid}" x="-50%" y="-150%" width="200%" height="400%">{layers}'
        f'<feMerge result="bm">{merged}</feMerge>'
        f'<feFlood flood-color="{color}"/><feComposite in2="bm" operator="in" result="glow"/>'
        f'<feMerge>{halos}<feMergeNode in="SourceGraphic"/></feMerge></filter>'
    )


# ---- Drone light show: each lit cell of a 5x7 matrix is one quadcopter ----
MATRIX = {
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
}


def drones(word: str, x0: float, y0: float, pitch: float, rnd: random.Random) -> list[str]:
    """One <use> per drone. Each flies up from the ground into formation once;
    with animation off it simply sits in formation."""
    out = []
    for i, ch in enumerate(word):
        for row, bits in enumerate(MATRIX[ch]):
            for col, bit in enumerate(bits):
                if bit != "1":
                    continue
                x, y = x0 + (i * 6 + col) * pitch, y0 + row * pitch
                dx, dy = rnd.uniform(-70, 70), GROUND - 4 - y  # lift off from the horizon
                out.append(
                    f'<use href="#drone" x="{n(x)}" y="{n(y)}" class="fly" '
                    f'style="--dx:{dx:.0f}px;--dy:{dy:.0f}px;animation-delay:{rnd.uniform(0, 1.4):.2f}s"/>'
                )
    return out


# ---- Kansas City skyline -------------------------------------------------
GROUND = 318
SIGN_X, SIGN_Y, SIGN_R = 381, 116, 56  # Western Auto sign: centre and ring radius
WA_X, WA_W, WA_TOP = 335, 92, 200  # Western Auto building under it


def skyline() -> tuple[str, str, str]:
    """(back layer, front silhouette, lit windows). Stylised, west to east:
    Liberty Memorial on its hill, the Western Auto building (its sign is drawn
    separately), City Hall, Power & Light (glowing lantern), One Kansas City
    Place, Town Pavilion, then the Bartle Hall pylons."""
    rnd = random.Random(1986)

    back = "".join(
        f'<rect x="{x}" y="{GROUND - h}" width="{w}" height="{h}"/>'
        for x, w, h in (
            (0, 40, 34), (196, 30, 52), (230, 28, 76), (296, 34, 96), (430, 30, 92), (590, 36, 74),
            (628, 30, 56), (790, 50, 40), (262, 24, 60), (560, 26, 104), (470, 28, 70),
        )
    )

    blocks = (  # (x, width, height) plain towers
        (236, 30, 46), (266, 24, 62), (290, 40, 36), (438, 26, 52), (606, 28, 50), (634, 18, 30),
    )
    shapes = [f'<rect x="{x}" y="{GROUND - h}" width="{w}" height="{h}"/>' for x, w, h in blocks]
    # Liberty Memorial: hill, flanking halls, tapering tower, torch.
    shapes.append(f'<path d="M0 {GROUND}V300Q60 284 112 282Q170 284 230 304V{GROUND}Z"/>')
    shapes.append('<rect x="78" y="274" width="20" height="10"/><rect x="126" y="274" width="20" height="10"/>')
    shapes.append('<path d="M103 284L105 182H119L121 284Z"/><rect x="101" y="176" width="22" height="8"/>')
    # Western Auto: wedge-shaped block with a deep cornice.
    shapes.append(f'<rect x="{WA_X}" y="{WA_TOP}" width="{WA_W}" height="{GROUND - WA_TOP}"/>')
    # City Hall: art-deco stepped tower.
    shapes.append(f'<path d="M464 {GROUND}V248H470V228H476V212H494V228H500V248H506V{GROUND}Z"/>')
    # Power & Light: stepped crown with a lantern.
    shapes.append(f'<path d="M508 {GROUND}V222H512V208H516V196H520V186H540V196H544V208H548V222H552V{GROUND}Z"/>')
    shapes.append('<rect x="525" y="172" width="10" height="14"/><path d="M525 172L530 164L535 172Z"/>')
    # One Kansas City Place: the tallest, with a stepped pyramid top.
    shapes.append(f'<path d="M556 {GROUND}V192H560V182H566V174H586V182H592V192H596V{GROUND}Z"/>')
    shapes.append('<path d="M570 174L576 160L582 174Z"/>')
    # Town Pavilion: angled roofline.
    shapes.append(f'<path d="M598 {GROUND}V216L626 202V{GROUND}Z"/>')
    # Bartle Hall: long low hall with four pylons carrying the Sky Stations.
    shapes.append(f'<rect x="652" y="{GROUND - 22}" width="190" height="22"/>')
    for px in (674, 718, 762, 806):
        shapes.append(
            f'<rect x="{px - 2}" y="200" width="4" height="{GROUND - 200}"/>'
            f'<path d="M{px - 9} 200L{px - 3} 186L{px + 1} 192L{px + 9} 184L{px + 5} 200Z"/>'
        )

    windows = []
    for x, w, h in (*blocks, (464, 42, 70), (508, 44, 96), (556, 40, 126), (598, 28, 102)):
        for wy in range(GROUND - h + 8, GROUND - 6, 8):
            for wx in range(x + 4, x + w - 4, 6):
                if rnd.random() < 0.18:
                    fill = PINK_SOFT if rnd.random() < 0.2 else WARM
                    windows.append(f'<rect x="{wx}" y="{wy}" width="2" height="3" fill="{fill}"/>')
    # Western Auto's regular grid of tall windows, most of them lit (it's lofts now).
    for wy in range(WA_TOP + 16, GROUND - 8, 9):
        for wx in range(WA_X + 6, WA_X + WA_W - 6, 7):
            if rnd.random() < 0.55:
                windows.append(f'<rect x="{wx}" y="{wy}" width="3" height="5" fill="{WARM}"/>')
    windows.append(f'<rect class="blink" x="570" y="196" width="2" height="3" fill="{WARM}"/>')

    return back, "".join(shapes), "".join(windows)


def western_auto_sign() -> str:
    """The 1952 Western Auto rooftop sign, reworded: red slab-serif neon inside a
    ring of white bulbs that runs clockwise and ends in an arrowhead, all on a
    steel lattice. The bulbs chase, as the original's once did."""
    ultra = Script("Ultra-Regular.ttf")
    cx, cy, r = SIGN_X, SIGN_Y, SIGN_R

    def at(clock_deg: float, radius: float = r) -> tuple[float, float]:
        a = math.radians(clock_deg)
        return cx + radius * math.sin(a), cy - radius * math.cos(a)

    # Ring: from ~8 o'clock, clockwise over the top, round to just past 6.
    (sx, sy), (ex, ey) = at(240), at(528)
    ring = f"M{n(sx)} {n(sy)}A{r} {r} 0 1 1 {n(ex)} {n(ey)}"
    # Arrowhead at the end, pointing along the direction of travel.
    tx, ty = math.cos(math.radians(528)), math.sin(math.radians(528))
    tip = (ex + tx * 14, ey + ty * 14)
    barbs = []
    for turn in (145, -145):
        a = math.atan2(ty, tx) + math.radians(turn)
        barbs.append(f"M{n(tip[0])} {n(tip[1])}L{n(tip[0] + 17 * math.cos(a))} {n(tip[1] + 17 * math.sin(a))}")
    head = f"M{n(ex)} {n(ey)}L{n(tip[0])} {n(tip[1])}" + "".join(barbs)
    # Fletching at the start.
    ux, uy = math.cos(math.radians(240)), math.sin(math.radians(240))
    tail = "".join(
        f"M{n(sx)} {n(sy)}L{n(sx + 10 * math.cos(math.atan2(uy, ux) + math.radians(t)))} "
        f"{n(sy + 10 * math.sin(math.atan2(uy, ux) + math.radians(t)))}"
        for t in (40, -40)
    )
    bulbs = ring + head + tail

    size = 46
    word = ultra.path("the", size, cx - ultra.width("the", size) / 2, cy + 14)

    posts = "".join(f"M{x} {cy - 20}V{WA_TOP}" for x in range(cx - 40, cx + 41, 20))
    braces = "".join(
        f"M{x} {y}L{x + 20} {y + 20}M{x + 20} {y}L{x} {y + 20}"
        for x in range(cx - 40, cx + 40, 20)
        for y in range(int(cy) + 40, WA_TOP - 10, 20)
    )
    return f"""<g fill="none" stroke="#4b3a6e" stroke-width="1.6">
      <path d="{posts}"/><path d="{braces}" stroke-width="1"/><path d="M{cx - 44} {WA_TOP}H{cx + 44}"/>
    </g>
    <g fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="{bulbs}" stroke="#ffe6c7" stroke-opacity=".22" stroke-width="5"/>
      <path d="{bulbs}" stroke="#fff4e0" stroke-width="3.2" stroke-dasharray="0 5.2" opacity=".55"/>
      <path class="chase" d="{bulbs}" stroke="#fffaf0" stroke-width="3.6" stroke-dasharray="0 15.6" filter="url(#glowBulb)"/>
    </g>
    <path class="ign2" d="{word}" fill="{RED}" stroke="#ffd2c4" stroke-width="1" filter="url(#glowRed)"/>"""


def hero() -> str:
    W, H = 840, 400
    rnd = random.Random(7)

    pitch, top = 13, 72
    gap = 2 * SIGN_R + 46  # room for the Western Auto sign between THE and CHAD
    the_w, chad_w = (3 * 6 - 1) * pitch, (4 * 6 - 1) * pitch
    x0 = SIGN_X - gap / 2 - the_w + pitch / 2
    fleet = drones("THE", x0, top, pitch, rnd) + drones("CHAD", x0 + the_w + gap, top, pitch, rnd)

    TWINKLE = ' class="tw" style="animation-delay:{:.1f}s"'
    stars = "".join(
        f'<circle cx="{rnd.randrange(16, W - 16)}" cy="{rnd.randrange(14, 120)}" r="{rnd.choice((0.6, 0.8, 1.1))}"'
        f'{TWINKLE.format(rnd.uniform(0, 6)) if i % 4 == 0 else ""}/>'
        for i in range(34)
    )
    back, front, windows = skyline()
    frame = f"M0 18Q0 0 18 0H{W - 18}Q{W} 0 {W} 18V350Q{W / 2} 412 0 350Z"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(HANDLE)}: a drone light show spells THE and CHAD over the Kansas City skyline at dusk, with the Western Auto sign reading 'the' between them">
  <title>{escape(HANDLE)} :: {escape(TAGLINE.lower())}</title>
  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
    .fly {{ animation: fly 2.8s cubic-bezier(.25,.7,.25,1) backwards; }}
    @keyframes fly {{ from {{ transform: translate(var(--dx), var(--dy)); }} }}
    .ign2 {{ animation: ign 1.6s steps(1) 2.6s; }}
    @keyframes ign {{ 0% {{ opacity: .12; }} 10% {{ opacity: 1; }} 16% {{ opacity: .25; }} 28% {{ opacity: 1; }} 34% {{ opacity: .5; }} 42%, 100% {{ opacity: 1; }} }}
    .chase {{ animation: chase .9s steps(3) infinite; }}
    @keyframes chase {{ to {{ stroke-dashoffset: -15.6; }} }}
    .tw {{ animation: tw 5s ease-in-out infinite; }}
    @keyframes tw {{ 50% {{ opacity: .2; }} }}
    .blink {{ animation: blink 9s steps(1) infinite; }}
    @keyframes blink {{ 60% {{ opacity: 0; }} }}
    {REDUCED_MOTION}
  </style>
  <defs>
    <clipPath id="frame"><path d="{frame}"/></clipPath>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="{GROUND}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{SKY[0]}"/><stop offset=".35" stop-color="{SKY[1]}"/><stop offset=".65" stop-color="{SKY[2]}"/>
      <stop offset=".88" stop-color="{SKY[3]}"/><stop offset="1" stop-color="{SKY[4]}"/>
    </linearGradient>
    <radialGradient id="haze" cx=".5" cy="1" r=".6"><stop offset="0" stop-color="{PINK}" stop-opacity=".45"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></radialGradient>
    <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#120826"/><stop offset="1" stop-color="{INK}"/></linearGradient>
    <radialGradient id="led"><stop offset="0" stop-color="{CORE}"/><stop offset=".25" stop-color="{CYAN}" stop-opacity=".9"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
    <radialGradient id="vignette" cx=".5" cy=".45" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
    <linearGradient id="lantern" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.5" fill="#000" opacity=".22"/></pattern>
    <filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .5 0"/></filter>
    {neon_filter("glowRed", RED_GLOW, (2, 5, 10))}
    {neon_filter("glowBulb", "#ffc890", (1.5, 4))}
    {neon_filter("glowSoft", PINK, (2, 5))}
    <g id="drone">
      <circle r="{pitch * 0.72:.1f}" fill="url(#led)"/>
      <path d="M-4.6 -4.6L4.6 4.6M4.6 -4.6L-4.6 4.6" stroke="{DRONE}" stroke-width="1"/>
      <g fill="none" stroke="{DRONE}" stroke-width=".8"><circle cx="-4.6" cy="-4.6" r="2.1"/><circle cx="4.6" cy="-4.6" r="2.1"/><circle cx="-4.6" cy="4.6" r="2.1"/><circle cx="4.6" cy="4.6" r="2.1"/></g>
      <circle r="1.8" fill="{CORE}"/>
    </g>
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    <g fill="#fff" opacity=".8">{stars}</g>
    <ellipse cx="{W / 2}" cy="{GROUND}" rx="{W * 0.6}" ry="150" fill="url(#haze)"/>
    <g fill="{VIOLET}" opacity=".75">{back}</g>

    <g fill="{INK}">{front}</g>
    <rect x="{WA_X - 3}" y="{WA_TOP}" width="{WA_W + 6}" height="7" fill="#5a3360"/>
    <rect x="525" y="174" width="10" height="12" fill="url(#lantern)" filter="url(#glowSoft)"/>
    <circle cx="112" cy="172" r="3.5" fill="{WARM}" filter="url(#glowSoft)"/>
    <g opacity=".85">{windows}</g>
    {western_auto_sign()}
    <rect y="{GROUND}" width="{W}" height="{H - GROUND}" fill="url(#ground)"/>
    <rect y="{GROUND}" width="{W}" height="1" fill="{PINK}" opacity=".55"/>

    <!-- Drone show: drawn last among the scenery so drones climb in front of it -->
    <g>{"".join(fleet)}</g>

    {label(W / 2, 352, f"{PLACE}  ·  {TAGLINE}", 12, MUTED, "middle", 2.4, ' letter-spacing="2.4"')}

    <rect width="{W}" height="{H}" filter="url(#grain)" opacity=".07"/>
    <rect width="{W}" height="{H}" fill="url(#scan)"/>
    <rect width="{W}" height="{H}" fill="url(#vignette)"/>
  </g>
  <path d="{frame}" fill="none" stroke="{RIM}" stroke-width="2"/>
</svg>
"""


def header(index: str, word: str, theme: str) -> str:
    """Section header: neon script word + a rule that fades out to the right."""
    W, H = 840, 64
    yellowtail = Script("Yellowtail-Regular.ttf")
    size, x = 44, 62
    script = yellowtail.path(word, size, x, 44)
    end = x + yellowtail.width(word, size) + 18
    dark = theme == "dark"
    core, accent, second = ("#fff0fa", PINK, CYAN) if dark else (PINK_ON_WHITE, PINK_ON_WHITE, CYAN_ON_WHITE)
    word_filter = ' filter="url(#neon)"' if dark else ""
    rule_filter = ' filter="url(#soft)"' if dark else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(word)}">
  <title>{escape(word)}</title>
  <style>
    text {{ font-family: {MONO}; white-space: pre; }}
    .flk {{ animation: flk 7s steps(1) infinite; }}
    @keyframes flk {{ 0%, 90%, 92%, 94%, 100% {{ opacity: 1; }} 91% {{ opacity: .55; }} 93% {{ opacity: .8; }} }}
    {REDUCED_MOTION}
  </style>
  <defs>
    {neon_filter("neon", PINK, (1.5, 4, 8))}
    <filter id="soft" x="-5%" y="-400%" width="110%" height="900%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <linearGradient id="rule" x1="{n(end)}" y1="0" x2="{W}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{accent}"/><stop offset=".6" stop-color="{second}" stop-opacity=".6"/><stop offset="1" stop-color="{second}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  {label(8, 40, index, 13, second, extra=' letter-spacing="1"')}
  <rect x="32" y="30" width="18" height="1.5" fill="{second}"/>
  <path class="flk" d="{script}" fill="{core}" stroke="{core}" stroke-width=".5"{word_filter}/>
  <rect x="{n(end)}" y="34" width="{n(W - end)}" height="2" rx="1" fill="url(#rule)"{rule_filter}/>
</svg>
"""


def liner_notes() -> str:
    """Album back cover: SIDE A agentic SDLC, SIDE B software + hardware, on a dark plate (theme-proof)."""
    W, H = 840, 256
    cedarville = Script("CedarvilleCursive-Regular.ttf")
    rows = []
    for col, (side, title, tracks, start) in enumerate(
        (("SIDE A", "AGENTIC SDLC", SIDE_A, 1), ("SIDE B", "SOFTWARE + HARDWARE", SIDE_B, len(SIDE_A) + 1))
    ):
        x = 48 + col * 400
        rows.append(label(x, 58, f"{side}  ·  {title}", 12, CYAN, spacing=2.4, extra=' letter-spacing="2.4"'))
        rows.append(f'<rect x="{x}" y="68" width="320" height="1" fill="{RIM}"/>')
        for i, track in enumerate(tracks):
            y = 98 + i * 28
            rows.append(label(x, y, f"{start + i:02d}", 13, PINK_SOFT))
            rows.append(label(x + 36, y, track, 15, TEXT))

    caption = cedarville.path(LINER_CAPTION, 24, 0, 0)
    cap_w = cedarville.width(LINER_CAPTION, 24)
    # A little PCB trace running along the bottom edge: the hardware nod.
    trace = (
        f'<g fill="none" stroke="{RIM}" stroke-width="2" stroke-linecap="round">'
        '<path d="M24 236H120L132 224H220"/><path d="M24 244H150L162 232H260"/></g>'
        f'<g fill="{NIGHT}" stroke="{RIM}" stroke-width="2"><circle cx="220" cy="224" r="4"/><circle cx="260" cy="232" r="4"/></g>'
    )
    alt = "Side A, agentic SDLC: " + ", ".join(SIDE_A) + ". Side B, software and hardware: " + ", ".join(SIDE_B) + "."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(alt)}">
  <title>{escape(alt)}</title>
  <style>text {{ font-family: {MONO}; white-space: pre; }}</style>
  <defs>{neon_filter("neon", PINK, (1, 3), 1)}</defs>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="16" fill="{NIGHT}" stroke="{RIM}" stroke-width="2"/>
  <rect x="420" y="44" width="1" height="164" fill="{RIM}"/>
  {"".join(rows)}
  {trace}
  <path d="{caption}" fill="{PINK_SOFT}" filter="url(#neon)" transform="translate({n(W - 56 - cap_w)} 224) rotate(-4)"/>
</svg>
"""


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    out = {"hero.svg": hero(), "liner-notes.svg": liner_notes()}
    for stem, index, word, _ in HEADERS:
        out[f"{stem}.svg"] = header(index, word, "dark")
        out[f"{stem}-light.svg"] = header(index, word, "light")
    for name, svg in out.items():
        (ASSETS / name).write_text(svg, encoding="utf-8")
        print(f"wrote assets/{name} ({len(svg.encode()) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
