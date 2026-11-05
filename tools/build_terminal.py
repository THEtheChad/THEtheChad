#!/usr/bin/env python3
"""Generate assets/terminal.svg: a retro CRT boot screen with subtle animation.

Edit the CONFIG block, then run from the repo root:

    python3 tools/build_terminal.py

Every character gets a fixed-width cell (textLength), so the layout looks the
same whichever monospace font the viewer's machine falls back to.
"""

from pathlib import Path
from xml.sax.saxutils import escape

# ---- CONFIG (edit me) -------------------------------------------------------
HANDLE = "THEtheChad"
TAGLINE = "code / hardware / tinkering"  # EDIT: your one-liner
BIOS = f"PHOSPHOR BIOS v1.986   (C) {HANDLE} SYSTEMS"
CHECKS = (  # (label, value) rows; each ends in [ OK ]
    ("CPU", "CAFFEINE-8086"),
    ("MEMORY TEST", "640K"),
)
COMMAND = "whoami"
PROMPT = "C:\\> "
# -----------------------------------------------------------------------------

W, H = 840, 340
SX, SY, SW, SH = 24, 22, 792, 278  # screen rect
X0, Y0 = 60, 64  # first text baseline
FS, CW, LH = 16, 9.6, 30  # font size, cell width, line height

GREEN, DIM, BRIGHT = "#33ff66", "#1c8a3f", "#c6ffd6"
FONT = (
    "'IBM Plex Mono','Cascadia Mono',Consolas,'SFMono-Regular',Menlo,"
    "'DejaVu Sans Mono','Liberation Mono','Courier New',monospace"
)


def x(col: float) -> float:
    return round(X0 + col * CW, 2)


def y(row: int) -> int:
    return Y0 + row * LH


def text(col: float, row: int, s: str, t: float, fill: str = GREEN) -> str:
    """One run of text that pops on at time t (seconds)."""
    return (
        f'<text class="a" x="{x(col)}" y="{y(row)}" textLength="{round(len(s) * CW, 2)}" '
        f'lengthAdjust="spacing" fill="{fill}" style="animation-delay:{t:.2f}s">{escape(s)}</text>'
    )


def build() -> str:
    out: list[str] = []
    t = 0.6

    # Row 0: BIOS banner
    out.append(text(0, 0, BIOS, t, BRIGHT))
    t += 0.45

    # Rows 1..n: hardware checks, dotted leaders then value + OK
    row = 1
    for label, value in CHECKS:
        dots = "." * (30 - len(label) - 1)
        out.append(text(0, row, label, t))
        out.append(text(len(label) + 1, row, dots, t, DIM))
        out.append(text(31, row, value, t + 0.25))
        out.append(text(46, row, "[ OK ]", t + 0.35, BRIGHT))
        t += 0.6
        row += 1

    # Loading bar: blocks fill in one by one
    label = "LOADING PROFILE"
    out.append(text(0, row, label, t))
    out.append(text(17, row, "[", t, DIM))
    out.append(text(38, row, "]", t, DIM))
    t += 0.2
    for i in range(20):
        out.append(
            f'<rect class="a" x="{x(18 + i) + 1}" y="{y(row) - 12}" width="{CW - 2}" height="14" '
            f'fill="{GREEN}" style="animation-delay:{t:.2f}s"/>'
        )
        t += 0.06
    out.append(text(40, row, "100%", t + 0.05, BRIGHT))
    t += 0.5
    row += 2  # blank line

    # Prompt + typed command
    out.append(text(0, row, PROMPT, t))
    t += 0.35
    for i, ch in enumerate(COMMAND):
        out.append(text(len(PROMPT) + i, row, ch, t, BRIGHT))
        t += 0.13
    t += 0.4
    row += 1

    # Command output
    out.append(text(0, row, HANDLE, t, BRIGHT))
    out.append(text(len(HANDLE) + 1, row, f":: {TAGLINE}", t))
    t += 0.45
    row += 1

    # Final prompt with blinking block cursor
    out.append(text(0, row, PROMPT, t))
    cursor = (
        f'<rect class="cur" x="{x(len(PROMPT)) + 0.5}" y="{y(row) - 13}" width="{CW - 1}" '
        f'height="16" fill="{GREEN}" style="animation-delay:{t:.2f}s"/>'
    )

    body = "\n      ".join(out)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Retro CRT terminal booting {escape(HANDLE)}'s profile">
  <title>{escape(HANDLE)} :: {escape(TAGLINE)}</title>
  <style>
    text {{ font-family: {FONT}; font-size: {FS}px; white-space: pre; }}
    .a {{ opacity: 0; animation: on 1ms linear forwards; }}
    @keyframes on {{ to {{ opacity: 1; }} }}
    .cur {{ opacity: 0; animation: blink 1.1s steps(1) infinite; }}
    @keyframes blink {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
    .pwr {{ transform-box: view-box; transform-origin: {SX + SW / 2}px {SY + SH / 2}px;
            animation: pwr .55s cubic-bezier(.2,.8,.2,1) both; }}
    @keyframes pwr {{ 0% {{ transform: scale(.6,.004); opacity: 0; }}
                      25% {{ transform: scale(1,.004); opacity: 1; }}
                      100% {{ transform: scale(1,1); opacity: 1; }} }}
    .flash {{ opacity: 0; animation: flash .9s ease-out both; }}
    @keyframes flash {{ 0% {{ opacity: .5; }} 100% {{ opacity: 0; }} }}
    .flk {{ animation: flk 9s linear infinite; }}
    @keyframes flk {{ 0%, 60%, 62%, 64%, 100% {{ opacity: 1; }} 61% {{ opacity: .92; }} 63% {{ opacity: .96; }} }}
    .scan {{ animation: scan 8s linear infinite; }}
    @keyframes scan {{ from {{ transform: translateY(-90px); }} to {{ transform: translateY({SH + 30}px); }} }}
    .led {{ animation: led 3.2s ease-in-out infinite; }}
    @keyframes led {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .4; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .a, .cur {{ opacity: 1; animation: none; }}
      .pwr, .flk, .led {{ animation: none; }}
      .flash, .scan {{ display: none; }}
    }}
  </style>
  <defs>
    <linearGradient id="bezel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#34362f"/><stop offset="1" stop-color="#1a1b17"/>
    </linearGradient>
    <radialGradient id="tube" cx=".5" cy=".45" r=".75">
      <stop offset="0" stop-color="#0c1d11"/><stop offset="1" stop-color="#020503"/>
    </radialGradient>
    <radialGradient id="vignette" cx=".5" cy=".5" r=".72">
      <stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".65"/>
    </radialGradient>
    <linearGradient id="glare" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity=".07"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{GREEN}" stop-opacity="0"/>
      <stop offset=".5" stop-color="{GREEN}" stop-opacity=".07"/>
      <stop offset="1" stop-color="{GREEN}" stop-opacity="0"/>
    </linearGradient>
    <pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="2" fill="#000" opacity=".28"/>
    </pattern>
    <filter id="glow" x="-5%" y="-20%" width="110%" height="140%">
      <feGaussianBlur stdDeviation="1.3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="ledglow" x="-200%" y="-200%" width="500%" height="500%">
      <feGaussianBlur stdDeviation="2.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="screen"><rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="14"/></clipPath>
  </defs>

  <!-- Case -->
  <rect width="{W}" height="{H}" rx="22" fill="url(#bezel)"/>
  <rect x="{SX - 7}" y="{SY - 7}" width="{SW + 14}" height="{SH + 14}" rx="19" fill="#0b0c0a"/>
  <rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="14" fill="url(#tube)"/>

  <!-- Screen -->
  <g clip-path="url(#screen)">
    <g class="pwr">
      <rect class="flash" x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="{GREEN}"/>
      <g class="flk" filter="url(#glow)">
      {body}
      {cursor}
      </g>
    </g>
    <rect class="scan" x="{SX}" y="{SY}" width="{SW}" height="90" fill="url(#beam)"/>
    <rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="url(#lines)"/>
    <rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="url(#vignette)"/>
    <rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" fill="url(#glare)"/>
  </g>

  <!-- Case badge, vents, power LED -->
  <text x="42" y="326" fill="#7a7c72" font-size="11" letter-spacing="3" font-weight="700">{escape(HANDLE.upper())} PC-1986</text>
  <g fill="#0e0f0d">
    <rect x="600" y="316" width="22" height="3" rx="1.5"/><rect x="628" y="316" width="22" height="3" rx="1.5"/>
    <rect x="656" y="316" width="22" height="3" rx="1.5"/><rect x="684" y="316" width="22" height="3" rx="1.5"/>
    <rect x="600" y="323" width="22" height="3" rx="1.5"/><rect x="628" y="323" width="22" height="3" rx="1.5"/>
    <rect x="656" y="323" width="22" height="3" rx="1.5"/><rect x="684" y="323" width="22" height="3" rx="1.5"/>
  </g>
  <text x="776" y="325" fill="#7a7c72" font-size="10" letter-spacing="2" text-anchor="end">PWR</text>
  <circle class="led" cx="792" cy="321" r="4" fill="#ffb000" filter="url(#ledglow)"/>
</svg>
"""


if __name__ == "__main__":
    dest = Path(__file__).resolve().parent.parent / "assets" / "terminal.svg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(build(), encoding="utf-8")
    print(f"wrote {dest}")
