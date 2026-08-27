"""The palette, the type, and the stylesheet the scenes share.

Everything visual in this app descends from the Claude Design file "Evidence Room", and
this module is where that file's values live in Python: every colour it uses, named, and
every typeface it names. The scenes themselves — the archive and the board — carry their
own CSS in `ui/archive.py`, `ui/board.py` and `ui/desk.py`; what is here is what all of them
share, plus the rules for the Streamlit widgets that have to look like they belong.

The palette is Python rather than only CSS custom properties because the board, the charts
and the interrogation room render into `st.iframe` documents, and a custom property
declared on this page stops at an iframe's boundary. Those frames get their colours by
import, which is what `tests/test_frame_palette.py` enforces: a colour a frame emits that
this dict does not declare fails the build.
"""

from __future__ import annotations

import json

from prove_it.domain.verdict import Verdict

# What a typed claim gets, since it has no case to supply them. Deliberately the spread
# argument: a free-text claim is compared on averages by the opening question, so this is
# the right objection to it.
DEFAULT_NUDGE = (
    "**Is that a fair way to check it?** An average tells you where a group sits. It says "
    "nothing about how much people inside the group differ from each other."
)
DEFAULT_REPAIR_LABEL = "Ask Genie to show the spread too"

VERDICT_TEXT = {
    Verdict.HOLDS: ("Looks true", "v-holds"),
    Verdict.BUSTED: ("Busted", "v-busted"),
    # Deliberately the fact-checker's phrase rather than a courtroom one. A general
    # audience reads "half true" fluently and correctly first time, which "true with
    # context" does not manage.
    Verdict.HALF_TRUE: ("Half true", "v-half"),
    Verdict.CANT_TELL: ("Can't tell", "v-nodata"),
}

# The design's four faces. Source Serif 4 for anything read as prose, IBM Plex Mono for every
# label and stat, Special Elite — a typewriter — for what was typed on a sheet, and Caveat for
# what was scribbled on one by hand. Fetched from Google Fonts exactly as the design file
# does; `FONT_LINK` below is that file's own link tag. This is the one request the app makes
# to a third party, and it is made so the room looks like the room. Every stack ends in a
# face the machine already has, so a classroom that blocks the fonts still reads the page.
FONTS = {
    "display": "'Source Serif 4', Georgia, 'Iowan Old Style', 'Palatino Linotype', serif",
    "body": "'Source Serif 4', Georgia, 'Iowan Old Style', 'Palatino Linotype', serif",
    "mono": "'IBM Plex Mono', ui-monospace, 'Cascadia Mono', Consolas, monospace",
    "type": "'Special Elite', ui-monospace, 'Courier New', monospace",
    "hand": "'Caveat', 'Segoe Print', 'Bradley Hand', cursive",
}

FONT_LINK = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">'
    '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@'
    "0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400;1,8..60,600&family=IBM+Plex+Mono:wght@"
    '400;500;600;700&family=Special+Elite&family=Caveat:wght@500;700&display=swap" '
    'rel="stylesheet">'
)

# Every colour in the design file, named for what it paints. Grouped by the surface it
# belongs to; a hex appears here once and nowhere else.
PALETTE = {
    # -- the room -----------------------------------------------------------------------
    "room": "#0B0E12",
    "wall": "#10151C",
    "wall-mid": "#131920",
    "wall-low": "#0D1116",
    "wall-foot": "#0A0D11",
    "cabinet": "#171D24",
    "cabinet-deep": "#10151B",
    "desk-top": "#4A3421",
    "desk-mid": "#3D2A1A",
    "desk-deep": "#2E1F12",
    "cord": "#2A313A",
    "cord-lit": "#4A5058",
    "shade": "#3A4048",
    "shade-deep": "#23262B",
    "bulb": "#FFF3D0",
    "bulb-warm": "#F2C877",
    "board-night": "#0E1319",
    # -- the board and its frame --------------------------------------------------------
    "frame": "#5C4028",
    "frame-deep": "#4A3120",
    "cork": "#B08A55",
    "cork-mid": "#9C7743",
    "cork-deep": "#8F6C3B",
    "fixture": "#3E444C",
    "fixture-deep": "#22262C",
    "string": "#C03A2E",
    "pin-red": "#E86A5E",
    "pin-red-deep": "#A32E24",
    "pin-blue": "#7FA3C8",
    "pin-blue-deep": "#35608C",
    # -- paper and ink ------------------------------------------------------------------
    "paper": "#FFFDF6",
    "cream": "#F3EBD8",
    "clipping": "#EFE6D0",
    "sheet": "#F5F1E6",
    "manila": "#EFE4C4",
    "manila-tab": "#E6D7AE",
    "manila-line": "#D9C89A",
    "rule": "#DDD5C2",
    "rule-soft": "#DDD2B8",
    "rule-clip": "#D6C9A8",
    "rule-dash": "#C9BB93",
    "row-line": "#EFE9D8",
    "table-head": "#F1ECDD",
    "ink": "#1B2027",
    "ink-warm": "#241E12",
    "ink-brown": "#33281A",
    "ink-type": "#2A2418",
    "pencil": "#5B6055",
    "pencil-warm": "#6E6448",
    "pencil-strip": "#5E635A",
    "slate": "#3E4348",
    "faint": "#6C7062",
    "label": "#64685C",
    "chit-ink": "#6E6042",
    "chit": "#FFF7DC",
    # -- kraft: the bag, the tags, the slate ---------------------------------------------
    "kraft": "#C9A86B",
    "kraft-mid": "#B49257",
    "kraft-deep": "#A8874C",
    "kraft-line": "#96793F",
    "kraft-band": "#B79459",
    "kraft-band-deep": "#A5824A",
    "kraft-dash": "#8A6E38",
    # The design's #4A3A1E, darkened 18%. Measured where the folder's TRAP line actually
    # sits — 45% down a #C39A5E→#B08748 flap — the design's ink is 3.79:1, under the 4.5
    # floor for text this size, on the card a ten-year-old reads first. The flap keeps its
    # colour; the ink takes the smallest step that clears the floor there and on the lower
    # half of the evidence bag (4.17:1 as designed).
    "kraft-ink": "#3C2F18",
    "kraft-ink-soft": "#3A3018",
    # Case file Nº 0 is the dimmest folder, and the design's #3A3018 measures 3.26:1 on it.
    # Its own label ink rather than a darker kraft-ink-soft everywhere, because the slate
    # and the custody tag clear the floor with the design's value as it is.
    "folder-own-label": "#1B160B",
    # Plain black and white, for the shadows and highlights the frames draw at partial
    # opacity — declared so the frame-palette guard can name them.
    "black": "#000000",
    "white": "#FFFFFF",
    # The cork's tooth, the cones the board's lamps throw, and the shadow inside the frame.
    "tooth": "#3C2610",
    "tooth-light": "#FFE6BE",
    "cone": "#FFD68C",
    "cork-shadow": "#281808",
    "kraft-blocks": "#8A7344",
    "tag": "#D8C9A4",
    "tag-line": "#BCA26F",
    # -- the folders --------------------------------------------------------------------
    "folder": "#C39A5E",
    "folder-deep": "#B08748",
    "folder-body": "#A8834C",
    "folder-body-deep": "#96733E",
    "folder-tab": "#B98E52",
    "folder-next": "#D2A960",
    "folder-next-deep": "#BC9250",
    "folder-next-body": "#B08A55",
    "folder-next-body-deep": "#9C7743",
    "folder-next-tab": "#C9A251",
    "folder-own": "#9A855C",
    "folder-own-deep": "#877348",
    "folder-own-body": "#7A6840",
    "folder-own-body-deep": "#6A5A36",
    "folder-own-tab": "#8F7B54",
    "folder-own-ink": "#2E2718",
    "stud": "#D8B276",
    "stud-rim": "#8A6A38",
    "stud-own": "#B89A64",
    "stud-own-rim": "#6E5C36",
    # -- the case-file red, the two greens, the navy, the golds --------------------------
    "red": "#B3372F",
    "red-sql": "#A23B32",
    "red-hand": "#7A2B24",
    "red-lit": "#C4483C",
    "wax": "#8E2A20",
    "wax-deep": "#6E1F17",
    "wax-ink": "#F5E9E2",
    "certain": "#D46A5E",
    "certain-ink": "#F0B9B0",
    # The stake coins, struck as gold and copper. The label is embossed in dark ink — it
    # measured 7.7:1 on the gold face and 5.6:1 on the copper, where the pale label the
    # coins carried before was 1.6:1 and unreadable. Hunch is one coin, fairly-sure two,
    # certain three, the stack drawn in edge bands beneath the top face.
    "coin-hi": "#F4E4AE",
    "coin": "#DFC271",
    "coin-mid": "#C4A24C",
    "coin-rim": "#A6822F",
    "coin-edge": "#8A6C2E",
    "coin-ink": "#3A2E12",
    "copper-hi": "#E8A87C",
    "copper": "#D98A5E",
    "copper-edge": "#8E4A28",
    "copper-ink": "#3A1E12",
    "green": "#3C6E4B",
    "green-deep": "#2E5D3A",
    "green-mark": "#DCE9D8",
    "navy": "#1F4E79",
    "gold": "#C9B37E",
    "gold-lit": "#E8B45A",
    "gold-pale": "#E8D9B0",
    "gold-fill": "#E3CE96",
    "gold-bar": "#C9A94E",
    "gold-deep": "#8A6524",
    "bone": "#F0EBDD",
    "mist": "#C7CBCF",
    "ash": "#9BA3AD",
    "chrome": "#1B2027",
    "hand-ink": "#4A4426",
    # -- the desk's props ----------------------------------------------------------------
    "brass": "#B8934E",
    "brass-lit": "#E8CE90",
    "brass-deep": "#6E5626",
    "brass-mid": "#8A6C36",
    "handle": "#241608",
    "handle-lit": "#5E4128",
    "handle-mid": "#3A2716",
    "handle-deep": "#180E04",
    "handle-cap": "#C9A860",
    "pad-ink": "#A83A30",
    "pad-ink-deep": "#7A241C",
    "stamp-knob": "#8A6A44",
    "stamp-base": "#6E5236",
    "stamp-base-mid": "#4A3520",
    "stamp-base-deep": "#332412",
    # -- semantics kept on the names every component already uses -----------------------
    "busted": "#B3372F",
    "holds": "#3C6E4B",
    "nodata": "#8A6524",
    "accent": "#1F4E79",
    "busted-soft": "#F7E9E7",
    "holds-soft": "#E7F0EA",
    "nodata-soft": "#F5EEDC",
    "accent-soft": "#E8EFF5",
}


def _root_block() -> str:
    """The `:root` declaration, built from the dicts above so the values appear once."""
    rows = [f"  --f-{name}: {stack};" for name, stack in FONTS.items()]
    rows += [f"  --{token}:{value};" for token, value in PALETTE.items()]
    return ":root {\n" + "\n".join(rows) + "\n}"


# The subset the inline-HTML components reach for, resolved once here so each of them is a
# plain import — and so a repaint of the palette reaches every frame by construction.
INK = PALETTE["ink"]
PAPER = PALETTE["paper"]
PENCIL = PALETTE["pencil"]
RULE = PALETTE["rule"]
NAVY = PALETTE["accent"]
RED = PALETTE["busted"]
GREEN = PALETTE["holds"]
GOLD_DEEP = PALETTE["nodata"]
GOLD_SOFT = PALETTE["nodata-soft"]
CHROME = PALETTE["chrome"]
BONE = PALETTE["bone"]
ASH = PALETTE["ash"]
SLATE = PALETTE["slate"]
GOLD_BAR = PALETTE["gold-bar"]
SERIF = FONTS["body"]
MONO = FONTS["mono"]
TYPEWRITER = FONTS["type"]
HAND = FONTS["hand"]

# The palette as a bidirectional component wants it: a plain dict, handed over as an arg.
# A `declare_component` frame is served as a static file, so nothing can be interpolated
# into it — the only route in is the args, and this is them.
FRAME_THEME: dict[str, str] = {
    "ink": INK,
    "pencil": PENCIL,
    "rule": RULE,
    "paper": PAPER,
    "gold": PALETTE["gold"],
    "red": RED,
    "serif": SERIF,
    "mono": MONO,
}


def rgba(token: str, alpha: float) -> str:
    """A palette colour at partial opacity, for the frames' glows and washes.

    `color-mix()` would do this in CSS, but only where a custom property is in scope — and
    inside those frames none is, which is the whole reason this module hands the values
    over in Python.
    """
    value = PALETTE[token].lstrip("#")
    red, green, blue = (int(value[at : at + 2], 16) for at in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def script_json(payload: object) -> str:
    """JSON for embedding inside a frame's <script> block.

    `json.dumps` leaves `<` and `>` alone, and the browser's script-end detection is a raw
    text scan rather than a JavaScript parse — so a group label containing the literal
    `</script>` closes the block early and everything after it is parsed as page markup.
    Labels come straight out of Genie's result rows, which is data this app does not
    control. Escaping them as unicode keeps the JSON identical to a parser and inert to the
    tokeniser.
    """
    return (
        json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


_CSS = """
<style>
/*PALETTE*/

/* --- the room ---------------------------------------------------------------------- */
/* The city archive after hours, as one stack of background layers on the app shell — the
   design's backdrop, layer for layer: a wall, two filing cabinets at the edges, a wooden
   desk across the bottom, and one lamp hanging over it.
   On the shell rather than on an element because Streamlit gives no way to render outside
   the block container, and its `stVerticalBlock` carries `z-index:1`: a stacking context
   that traps a `z-index:-1` child inside it, so a room drawn as an element painted OVER the
   corkboard it was meant to sit behind. A background paints behind everything by
   construction. Topmost first: vignette, bulb, glow, shade, cord, cone, desk lip, desk
   grain, desk, two cabinets, wall. */
.stApp {
  background-color:var(--room);
  background-image:
    radial-gradient(ellipse 78% 62% at 50% 44%, transparent 44%, rgba(0,0,0,.72) 100%),
    url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 170 200'><defs><radialGradient id='b' cx='42%25' cy='38%25' r='75%25'><stop offset='0' stop-color='%23FFF7DC'/><stop offset='.55' stop-color='%23FFF3D0'/><stop offset='1' stop-color='%23F2C877'/></radialGradient><linearGradient id='s' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='%23464D58'/><stop offset='.6' stop-color='%233A4048'/><stop offset='1' stop-color='%2323262B'/></linearGradient></defs><rect x='80' y='0' width='10' height='9' rx='2' fill='%232A313A'/><rect x='84' y='7' width='2' height='108' fill='%232A313A'/><circle cx='85' cy='158' r='17' fill='%23F2C877' opacity='.25'/><circle cx='85' cy='158' r='12' fill='url(%23b)'/><path d='M85 110 C 64 112 51 130 48 151 L 122 151 C 119 130 106 112 85 110 Z' fill='url(%23s)'/><ellipse cx='85' cy='151' rx='37' ry='6' fill='%2323262B'/><ellipse cx='85' cy='152' rx='30' ry='4' fill='%23F2C877' opacity='.75'/></svg>"),
    radial-gradient(ellipse 46% 58% at 50% 18%, rgba(238,196,118,.17),
      rgba(238,196,118,.055) 46%, transparent 72%),
    linear-gradient(180deg, rgba(255,230,180,.22), transparent),
    repeating-linear-gradient(94deg, rgba(0,0,0,.13) 0 2px, transparent 2px 26px,
      rgba(255,240,200,.02) 26px 27px, transparent 27px 90px),
    linear-gradient(180deg, var(--desk-top) 0%, var(--desk-mid) 30%, var(--desk-deep) 100%),
    linear-gradient(90deg, var(--cabinet), var(--cabinet-deep)),
    linear-gradient(270deg, var(--cabinet), var(--cabinet-deep)),
    linear-gradient(180deg, var(--wall) 0%, var(--wall-mid) 42%, var(--wall-low) 62%,
      var(--wall-foot) 100%);
  background-size:
    100% 100%, 170px 200px, min(1150px, 120vw) 70%, 100% 5px, 100% 46%, 100% 46%,
    min(230px, 16vw) 54%, min(250px, 17vw) 54%, 100% 100%;
  background-position:
    center, center top, center 145px, left 54%,
    left bottom, left bottom, -40px 14%, calc(100% + 60px) 12%, center;
  background-repeat:no-repeat;
  background-attachment:fixed; }

/* --- Streamlit's own chrome, removed ----------------------------------------------- */
/* The 60px header carrying a "Deploy" button and a hamburger. Framework chrome is the one
   thing that breaks the conceit; nothing behind it is load-bearing here. */
header[data-testid="stHeader"] { display:none; }
[data-testid="stHeaderActionElements"] { display:none; }
/* Streamlit's help bubble draws at 16x16 with no larger wrapper, under the 24px floor
   WCAG 2.5.8 asks of a pointer target. The hit area is grown with an overlay. */
[data-testid="stTooltipHoverTarget"] { position:relative; }
[data-testid="stTooltipHoverTarget"]::after {
  content:""; position:absolute; left:50%; top:50%; transform:translate(-50%, -50%);
  width:24px; height:24px; }
/* The scroll and wiring frames: scripts with nothing to show. One pixel rather than none
   because `st.iframe` rejects a height of zero; `[srcdoc]` keeps this off the estimate
   ruler, which is served from a URL and reports its own size. */
.stElementContainer:has(iframe[height="1"][srcdoc]) { display:none; }

/* There is no page. The room is the page, the scenes lay their objects in it, and the
   container is nothing but the viewport. Both scenes set their own gutters. */
.stMainBlockContainer, .block-container {
  max-width:none; margin:0; padding:0 !important; background:transparent;
  color:var(--bone); overflow-x:hidden; }
[data-testid="stVerticalBlock"] { gap:0 !important; }
html, body, [class*="css"] { font-family:var(--f-body); color:var(--bone); }
h1,h2,h3 { font-family:var(--f-display) !important; color:var(--bone); }
.stApp, .stMarkdown { color:var(--bone); }
.stMarkdown p { margin:0; }
[data-testid="stCaptionContainer"] { color:var(--ash); }

/* --- native widgets, dressed for the room ------------------------------------------ */
/* Every button is a mono, uppercase, letter-spaced control the way the design draws them.
   The default is the outlined one ("← THE ARCHIVE", "RETURN TO THE ARCHIVE →"); the
   primary is the gold one ("CLOSE THE CASE"). The scenes recolour the rest by key. */
.stButton > button, .stFormSubmitButton > button {
  font-family:var(--f-mono) !important; text-transform:uppercase; letter-spacing:.12em;
  font-weight:500; font-size:12.5px; border-radius:3px; padding:12px 18px;
  border:1.5px solid rgba(240,235,221,.6); background:transparent; color:var(--bone);
  transition:background .14s ease, color .14s ease, transform .14s ease; min-height:44px; }
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background:rgba(240,235,221,.1); color:var(--bone); border-color:var(--bone); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background:linear-gradient(180deg, var(--gold-fill), var(--gold)); color:var(--chrome);
  border-color:transparent; font-weight:700; box-shadow:0 6px 18px rgba(0,0,0,.5); }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  background:linear-gradient(180deg, var(--gold-fill), var(--gold)); color:var(--chrome);
  transform:translateY(-2px); }
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible {
  outline:2px solid var(--gold-lit); outline-offset:3px; }
.stButton > button:disabled, .stButton > button:disabled:hover {
  opacity:.42; transform:none; cursor:not-allowed; }
/* A typed line on a sheet: the claim the player brings, and the cross-examination. */
[data-testid="stTextInput"] input {
  background:var(--cream) !important; color:var(--ink-warm) !important;
  border:none !important; border-bottom:2px solid var(--ink-warm) !important;
  border-radius:2px 2px 0 0 !important; font-family:var(--f-type) !important;
  font-size:15px !important; padding:12px 14px !important; }
[data-testid="stTextInput"] input::placeholder { color:var(--pencil-warm) !important; }
[data-testid="stTextInput"] > label { display:none; }
/* Streamlit's alert, which only carries a refused claim now. */
[data-testid="stAlert"], [data-testid="stAlertContainer"] {
  background:rgba(20,16,10,.55) !important; border:1px solid rgba(201,179,126,.35) !important;
  border-left:3px solid var(--gold) !important; border-radius:6px !important; }
[data-testid="stAlert"] *, [data-testid="stAlertContainer"] * { color:var(--bone) !important; }
/* Expanders hold the judge-facing ledgers: provenance, and where the docket came from. */
[data-testid="stExpander"] { border:1px solid rgba(201,179,126,.35); border-radius:6px;
  background:rgba(20,16,10,.55); margin:14px 0; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {
  color:var(--mist) !important; font-family:var(--f-mono) !important; font-size:11px;
  letter-spacing:.12em; text-transform:uppercase; }
[data-testid="stExpander"] summary:hover * { color:var(--bone) !important; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p { color:var(--mist); }
/* The share strip, a code block the player can copy from. */
[data-testid="stCode"] pre, .stCode pre { background:var(--cream) !important;
  border:1px solid var(--rule-soft) !important; }
[data-testid="stCode"] code, .stCode code { color:var(--ink-warm) !important;
  font-family:var(--f-mono) !important; }
/* The result rows on the receipt: cream paper, ruled, mono. */
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
  --gdg-bg-cell:#FFFDF6; --gdg-bg-header:#F1ECDD; --gdg-text-dark:#1B2027;
  --gdg-text-header:#5E635A; --gdg-border-color:#DDD5C2;
  --gdg-horizontal-border-color:#EFE9D8; --gdg-bg-header-hovered:#E9E3D2;
  --gdg-bg-cell-medium:#F7F3E8; --gdg-font-family:"IBM Plex Mono", ui-monospace, monospace;
  border:1px solid var(--rule); }

/* --- the verdict as a rubber stamp -------------------------------------------------- */
.pi-verdict { display:inline-block; font-family:var(--f-mono); font-weight:700;
  font-size:11.5px; letter-spacing:.1em; text-transform:uppercase; padding:3px 8px;
  border:2px solid currentColor; border-radius:3px; transform:rotate(-8deg);
  white-space:nowrap; }
.v-busted { color:var(--red); }
.v-holds { color:var(--green); }
.v-nodata { color:var(--gold-deep); }
/* Half true reads between the other two on purpose: navy, not a third warm colour. It is
   not a weaker BUSTED, it is a different kind of answer. */
.v-half { color:var(--navy); }
.pi-verdict--arrive { opacity:0; animation:pi-stamp .45s cubic-bezier(.2,1.4,.4,1) .9s forwards; }
@keyframes pi-stamp {
  0% { opacity:0; transform:rotate(-8deg) scale(2.1); }
  55% { opacity:1; transform:rotate(-8deg) scale(.93); }
  100% { opacity:1; transform:rotate(-8deg) scale(1); } }

/* --- documents laid on the desk ---------------------------------------------------- */
/* Everything below the board is a paper object on wood. */
.pi-vlabel { font-family:var(--f-mono); font-size:11px; letter-spacing:.2em;
  text-transform:uppercase; color:var(--gold); margin:26px 0 10px; }
.pi-punch { font-family:var(--f-display); font-weight:600; font-size:19px;
  line-height:1.45; color:var(--bone); margin:12px 0; }
/* The receipt: the printed artifact you leave with. Cream, because a receipt on the dark
   desk is exactly the object it is. */
.pi-receipt { background:var(--cream); color:var(--ink-warm); padding:22px 24px;
  border-radius:2px; box-shadow:0 10px 26px rgba(0,0,0,.45); margin:8px 0 14px;
  width:min(680px, 100%); }
.pi-receipt .pi-claim { font-family:var(--f-display); font-size:22px; font-weight:700;
  font-style:italic; line-height:1.3; color:var(--ink-warm) !important; }
.pi-rrow { display:flex; justify-content:space-between; gap:12px; font-size:13.5px;
  border-bottom:1px dotted var(--rule-dash); padding:6px 0; color:var(--ink-warm); }
.pi-rrow span:last-child { font-family:var(--f-mono); color:var(--pencil-warm); }
/* The run's plinth: rank in serif on kraft. */
.pi-run { background:var(--kraft); border:1px solid var(--kraft-line); border-radius:3px;
  padding:16px 18px; color:var(--ink-warm); width:min(420px, 100%); margin:8px 0 14px;
  box-shadow:0 10px 24px rgba(0,0,0,.45); transform:rotate(-1.2deg); }
.pi-run .pi-vlabel { color:var(--kraft-ink-soft); margin:0; }
.pi-rank { font-family:var(--f-display); font-weight:700; font-size:26px;
  letter-spacing:-.01em; margin:6px 0 4px; color:var(--ink-warm); }
.pi-runrow { font-family:var(--f-mono); font-size:10px; letter-spacing:.08em;
  color:var(--kraft-ink-soft); line-height:1.9; }
/* The antibody kit: every trick met this session, as cards on the desk. */
.pi-wall-summary { font-family:var(--f-display); font-weight:600; font-size:18px;
  line-height:1.45; margin-bottom:14px; color:var(--bone); }
.pi-wall { display:grid; gap:14px; margin-bottom:18px;
  grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); }
.pi-card { background:var(--paper); border:1.5px solid var(--chrome); border-radius:8px;
  padding:16px 18px; color:var(--ink); box-shadow:0 14px 34px rgba(0,0,0,.5); }
.pi-card-trick { font-family:var(--f-display); font-weight:700; font-size:19px;
  color:var(--ink); margin-bottom:7px; letter-spacing:-.01em; }
.pi-card-lesson { font-size:13.5px; line-height:1.5; color:var(--slate); }
.pi-card-wild { font-family:var(--f-mono); font-size:10.5px; line-height:1.55;
  color:var(--red); margin-top:9px; letter-spacing:.04em; }
/* The added columns, named, with what each one revealed. */
.pi-exhibits { display:flex; flex-direction:column; gap:10px; margin:14px 0 4px; }
.pi-exhibit { display:flex; gap:2px; align-items:flex-start; font-size:15px;
  color:var(--ink-warm); line-height:1.55; padding:11px 15px; background:var(--paper);
  border:1px solid var(--rule-soft); border-left:3px solid var(--green); border-radius:2px;
  opacity:0; animation:pi-rise .45s ease-out forwards; }
.pi-exhibit code { font-family:var(--f-mono); font-size:13px; background:var(--table-head);
  color:var(--ink-warm); padding:1px 5px; border:1px solid var(--rule-soft); margin-right:6px; }
.pi-ex { display:inline-grid; place-items:center; width:17px; height:17px; flex:none;
  font-family:var(--f-display); font-size:11px; font-weight:700; line-height:1;
  color:var(--paper); background:var(--green); border-radius:3px; margin-right:6px; }
@keyframes pi-rise { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }
/* The provenance ledger, folded away. */
.pi-prov { border:1px solid var(--rule-soft); background:var(--paper); padding:14px 16px;
  color:var(--ink-warm); border-radius:2px; }
.pi-prov table { width:100%; border-collapse:collapse; font-family:var(--f-mono);
  font-size:11px; }
.pi-prov th { text-align:left; font-size:9.5px; letter-spacing:.13em; text-transform:uppercase;
  color:var(--pencil-warm); font-weight:600; padding:0 10px 6px 0; }
.pi-prov td { padding:5px 10px 5px 0; border-top:1px dotted var(--rule-dash);
  overflow-wrap:anywhere; color:var(--ink-warm); }
.pi-prov .note { font-family:var(--f-body); font-size:12.5px; line-height:1.55;
  color:var(--pencil-warm); margin-top:10px; }
/* A case built from the player's own catalog rather than the checked docket. */
.pi-case-new { font-family:var(--f-mono); font-size:8.5px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--red); border:1px solid var(--red);
  border-radius:2px; padding:1px 5px; margin-left:6px; white-space:nowrap; }
/* The payout chit: a torn slip, the design's `er-chit`. */
.pi-chit { display:inline-block; background:var(--chit); border:1.5px dashed var(--gold);
  border-radius:2px; padding:8px 12px; font-family:var(--f-mono); font-size:12px;
  font-weight:600; letter-spacing:.04em; color:var(--chit-ink); transform:rotate(2deg);
  opacity:0; animation:pi-chit .4s ease-out .9s forwards; margin:0 8px 8px 0; }
.pi-chit--void { border-color:var(--gold-deep); color:var(--gold-deep); }
@keyframes pi-chit { 0% { opacity:0; transform:rotate(2deg) translateY(-14px); }
                     100% { opacity:1; transform:rotate(2deg) translateY(0); } }
/* The estimate, laid over the truth: two marks on the ruler the player was given. */
.pi-est { margin:10px 0 4px; padding:10px 12px 8px; background:var(--chit);
  border:1.5px dashed var(--gold); border-radius:2px; width:min(420px, 100%); }
.pi-est-rule { position:relative; height:22px; margin:2px 10px 8px;
  background:linear-gradient(var(--rule-dash),var(--rule-dash)) 0 50%/100% 2px no-repeat; }
.pi-est-truth { position:absolute; top:0; width:2px; height:100%; margin-left:-1px;
  background:var(--red); }
.pi-est-truth::after { content:"the data"; position:absolute; top:-2px; left:6px;
  font-family:var(--f-mono); font-size:9px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--red); white-space:nowrap; }
.pi-est-you { position:absolute; top:50%; width:14px; height:14px; margin:-7px 0 0 -7px;
  border-radius:50%; border:2px solid var(--ink-warm); background:var(--paper); }
.pi-est-read { font-family:var(--f-mono); font-size:11px; letter-spacing:.04em;
  line-height:1.6; color:var(--chit-ink); }
.pi-est-read b { font-variant-numeric:tabular-nums; }

/* A scene arrives the way the design swaps them: from slightly too large and invisible. */
@keyframes pi-scene-in { from { opacity:0; transform:scale(1.05); } to { opacity:1; transform:none; } }
.pi-scene-enter [data-testid="stVerticalBlock"] { animation:pi-scene-in .6s ease both; }

/* Motion is decoration; the content must be complete without it. This is the design's own
   rule, applied to the whole page. */
@media (prefers-reduced-motion: reduce) {
  * { animation:none !important; transition:none !important; }
  .pi-verdict--arrive, .pi-chit, .pi-exhibit { opacity:1; }
}
</style>
"""

CSS = _CSS.replace("/*PALETTE*/", _root_block())
