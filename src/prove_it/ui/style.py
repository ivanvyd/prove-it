"""The stylesheet, kept apart from the page that uses it.

Extracted when `app.py` reached 855 lines, before it crossed the thousand-line mark rather
than after. It is also the natural seam: this
is one string, it imports nothing, and nobody reading the beats needs to scroll past two
hundred lines of CSS to reach them.

Every rule here was written against a defect. The comments say which.
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

# The two type stacks: a serif for anything read as
# prose, a mono for every label, id, stat and control.
#
# The design names Source Serif 4 and IBM Plex Mono, and they are named first here — but
# they are NOT fetched. The product forbids external calls, Databricks Apps may block the request
# anyway, and a webfont on a classroom machine is a third-party request per render. Both
# faces are used when a machine already has them; otherwise the stacks land on Georgia and
# Cascadia/Consolas, which carry the same serif/mono contrast the design relies on. The
# identity is in the colour, the stamps and the folders, not the webfont.
FONTS = {
    "display": '"Source Serif 4", Georgia, "Iowan Old Style", "Palatino Linotype", serif',
    "body": '"Source Serif 4", Georgia, "Iowan Old Style", "Palatino Linotype", serif',
    "mono": '"IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, "SF Mono", monospace',
}

# The case-file drawer. Manila folders and cream paper on a dark desk, with one navy chrome
# bar across the top — the design's palette, named. Red is the case-file red: it marks what
# is sealed, what is overturned, and nothing decorative. Gold is the rank and the score.
#
# In Python rather than only in the CSS below, because `ui/verdict_slam.py` and
# `ui/interrogation.py` render into sandboxed iframes. An iframe is a separate document, so
# a custom property declared in this stylesheet stops at its boundary — those two modules
# each carried their own hardcoded copy of the colours, and when the Case Files rework
# landed here the copies did not move with it. The flip beat, the one shot the product
# exists for, went on drawing itself in the old near-white paper and a sans-serif while the
# page around it was manila and serif. Declared once here and interpolated into all three,
# so the next repaint cannot leave a frame behind.
PALETTE = {
    # The room the desk stands in. Everything above the desk is dark and everything on it
    # is paper: that inversion is what makes a folder read as an object under a lamp rather
    # than as a card on a web page. It also keeps the accessibility work intact — the text a
    # child actually reads still sits on manila and cream, which is where the contrast pairs
    # were measured.
    "room": "#0B0E12",
    "room-lift": "#12161C",
    "wood": "#503823",
    "wood-mid": "#3D2A1A",
    "wood-deep": "#2A1D10",
    # The corkboard a case is worked on, and the wooden frame around it.
    #
    # The design's gradient runs #B08A55 -> #9C7743 -> #8F6C3B. The two darker stops are
    # lifted here because ink measures 4.19:1 on the design's darkest end, under the floor —
    # and on a board where only ink clears AA at all, text near the bottom would have been
    # the unreadable part. Lifted to the least that clears 4.5 across the whole span.
    "cork": "#B08A55",
    "cork-mid": "#A88048",
    "cork-deep": "#A87F45",
    "cork-frame": "#5E4128",
    # The folder itself: a tan flap over a darker body, a brass stud, and the sheet inside on
    # the same cream the rest of the app's documents use.
    #
    # The flap is 15% lighter than the design file's #C39A5E/#B08748 and the small ink 1%
    # darker. Measured, not preferred: the design's own pairing puts the folder's mono labels
    # at 4.23:1 on the light end and 3.34:1 on the dark, both under the 4.5 floor for text
    # this size, on the card a ten-year-old reads first. This is the smallest departure that
    # clears AA on both ends of the gradient while keeping the design's hue and its two
    # distinct ink weights; darkening the ink instead collapsed both weights onto the same
    # value and took the hierarchy with it.
    "folder": "#E2B26D",
    "folder-deep": "#CC9C53",
    "folder-tab": "#D4A35E",
    "folder-ink": "#33281A",
    "folder-ink-soft": "#48381D",
    "folder-stud": "#D8B276",
    "folder-stud-rim": "#8A6A38",
    "folder-sheet-ink": "#6E6448",
    "chrome": "#1B2027",
    "chrome-line": "#4A5058",
    "manila": "#EFE4C4",
    "manila-tab": "#E6D7AE",
    "manila-line": "#D9C89A",
    "paper": "#FFFDF6",
    "sheet": "#F5F1E6",
    "rule": "#DDD5C2",
    "ink": "#1B2027",
    "pencil": "#5B6055",
    # Darkened from #8A8E80, which measured 2.97:1 on the sheet — below the 4.5:1 floor
    # for body text, on the line that tells a visitor the demo is a recording. The whole
    # docket is read by children on classroom projectors; a caption they cannot resolve is
    # not a caption. Measured, not eyeballed: this is the lightest value that clears 4.5.
    "faint": "#6C7062",
    "slate": "#3E4348",
    "bone": "#F0EBDD",
    "ash": "#9BA3AD",
    # The design's secondary prose colour on the dark ground, one step brighter than `ash`.
    "mist": "#C7CBCF",
    "gold": "#C9B37E",
    "gold-deep": "#8A6524",
    "gold-bar": "#C9A94E",
    "red": "#B3372F",
    "navy": "#1F4E79",
    "green": "#3C6E4B",
    "kraft": "#D3BC8D",
    "kraft-line": "#BCA26F",
    "kraft-flap": "#C4AC7B",
    # Semantics kept on the existing names so every component keeps working.
    "busted": "#B3372F",
    "holds": "#3C6E4B",
    "nodata": "#8A6524",
    "accent": "#1F4E79",
    "busted-soft": "#F7E9E7",
    "holds-soft": "#E7F0EA",
    "nodata-soft": "#F5EEDC",
    "accent-soft": "#E8EFF5",
    "lock": "#D3BC8D",
}


def _root_block() -> str:
    """The `:root` declaration, built from the dicts above so the values appear once."""
    rows = [f"  --f-{name}: {stack};" for name, stack in FONTS.items()]
    rows += [f"  --{token}:{value};" for token, value in PALETTE.items()]
    return ":root {\n" + "\n".join(rows) + "\n}"


# The subset the inline-HTML components reach for, resolved once here so each of them is a
# plain import instead of six repetitions of the same lookup — and so a repaint of the
# palette above reaches every frame in the app by construction rather than by memory.
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


# The palette as a bidirectional component wants it: a plain dict, handed over as an arg.
#
# The one-way frames interpolate these values into their CSS at render time, which they can
# do because Python builds their whole document. A `declare_component` frame is served as a
# static file instead, so nothing can be interpolated into it — the only route in is the
# args, and this is them. Same values, same reason, different door.
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
    """A palette colour at partial opacity, for the iframes' glows and washes.

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
    tokeniser. One copy here, for the same reason the palette is: five frames each carried
    their own, and a fix to one would have had to be found and repeated in four more.
    """
    return (
        json.dumps(payload).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    )


_CSS = """
<style>
/*PALETTE*/
/* The room the desk stands in: a dark interior, one hanging lamp above the case file, and a
   vignette pulling the corners down. Painted with gradients on the app shell rather than as
   a fixed overlay, so it scrolls with the page and costs no extra element.

   The lamp is deliberately anchored to the top centre in `vw`/`vh` rather than to the sheet:
   a light source that tracks the document reads as a glow effect, and one that stays put
   reads as a lamp. */
/* The whole archive, as one stack of background layers on the app shell.
   It was a div of positioned children until a measurement showed why that cannot work here:
   Streamlit gives no way to render outside the block container, and its `stVerticalBlock`
   carries `z-index:1`, which makes a stacking context that traps a `z-index:-1` child inside
   it — so the room painted over the corkboard it was supposed to sit behind, and every word
   on the board went dark-on-dark. A background on `.stApp` paints behind all content by
   construction and nothing downstream can trap it.
   Topmost layer first: vignette, bulb, glow, shade, cord, light cone, desk lip, desk grain,
   desk, the two cabinets, then the wall. */
.stApp {
  background-color:var(--room);
  background-image:
    radial-gradient(ellipse 78% 62% at 50% 44%, transparent 44%, rgba(0,0,0,.72) 100%),
    radial-gradient(circle 13px at 50% 137px, #FFF3D0, #F2C877 55%,
      rgba(242,200,119,.25) 78%, transparent 82%),
    radial-gradient(circle 58px at 50% 137px, rgba(242,200,119,.34), transparent 72%),
    radial-gradient(ellipse 23px 13px at 50% 112px, #3A4048 60%, transparent 62%),
    linear-gradient(180deg, #2A313A, var(--chrome-line)),
    radial-gradient(ellipse 46% 58% at 50% 18%, rgba(238,196,118,.17),
      rgba(238,196,118,.055) 46%, transparent 72%),
    linear-gradient(180deg, rgba(255,230,180,.22), transparent),
    repeating-linear-gradient(94deg, rgba(0,0,0,.13) 0 2px, transparent 2px 26px,
      rgba(255,240,200,.02) 26px 27px, transparent 27px 90px),
    linear-gradient(180deg, #4A3421 0%, var(--wood-mid) 30%, #2E1F12 100%),
    linear-gradient(90deg, #171D24, #10151B),
    linear-gradient(270deg, #171D24, #10151B),
    linear-gradient(180deg, #10151C 0%, #131920 42%, #0D1116 62%, #0A0D11 100%);
  background-size:
    100% 100%,                /* vignette */
    100% 100%,                /* bulb */
    100% 100%,                /* glow */
    100% 100%,                /* shade */
    2px 108px,                /* cord */
    min(1150px, 120vw) 70%,   /* cone */
    100% 5px,                 /* desk lip */
    100% 46%,                 /* desk grain */
    100% 46%,                 /* desk */
    min(230px, 16vw) 54%,     /* left cabinet */
    min(250px, 17vw) 54%,     /* right cabinet */
    100% 100%;                /* wall */
  background-position:
    center, center, center, center,
    center top,               /* cord */
    center 130px,             /* cone */
    left 54%,                 /* desk lip */
    left bottom, left bottom, /* desk grain, desk */
    -40px 14%, calc(100% + 60px) 12%,
    center;
  background-repeat:no-repeat;
  background-attachment:fixed; }

/* The design's bulb flickers. Dropped rather than reproduced: on a background layer there is
   nothing to animate without repainting the whole shell, and a light that never settles is
   perpetual movement behind text a child is reading. The glow stays; the failing tube goes.
   This is a deliberate deviation from the design file, not an omission. */
@media (prefers-reduced-motion: reduce) {
  /* The source link's hover fade, on the same terms as the copy button's in query_panel.py. */
  .pi-mast-src { transition:none; }
}

/* Streamlit's own header — a 60px bar carrying a "Deploy" button and a hamburger — sits
   over the top of the page. Measured, not assumed: it is there at every viewport. On a
   document that is pretending to be a case file, framework chrome is the one thing that
   breaks the conceit, and the menu behind it offers a child "Record a screencast" and
   "Report a bug with Streamlit". There is no sidebar and no menu_items, so nothing here
   is load-bearing. */
header[data-testid="stHeader"] { display:none; }

/* The anchor icon Streamlit hangs off every heading on hover. Pure noise here, and at
   16x16 it was the smallest tap target on the page. */
[data-testid="stHeaderActionElements"] { display:none; }

/* Streamlit's own help bubble — the "?" beside the stake question — draws at 16x16 with no
   larger clickable wrapper, which is under the 24px floor WCAG 2.5.8 asks of a pointer
   target. Measured on the case screen at 768px, where a child is using a finger rather than
   a mouse. The hit area is grown with an overlay rather than by padding the control, so the
   icon stays the size the rest of the line is set for — the same trick the copy button on
   the query panel uses. */
[data-testid="stTooltipHoverTarget"] { position:relative; }
[data-testid="stTooltipHoverTarget"]::after {
  content:""; position:absolute; left:50%; top:50%; transform:translate(-50%, -50%);
  width:24px; height:24px; }

/* The default 96px of padding existed to clear that header. With it gone the space is
   just a gap, and 52px of it is worth more given to the claim above the fold. */
.stMainBlockContainer, .block-container { padding-top:44px; }

/* The layout is "wide" so the two query panels sit side by side, but wide is not the same
   as unbounded: on a 1920px screen the container fills the viewport and headings run to
   nearly 100 characters, well past what anyone reads comfortably — let alone a child.
   Capped and centred, which still leaves each SQL panel roughly 580px. */
/* The whole page is one case sheet laid on the desk: cream, squared off, with a shadow
   that lifts it. The dark ground shows only at the edges, which is what makes the sheet
   read as an object rather than as the window's background. */
/* There is no page. The room IS the page: the archive is a dark space with objects lying in
   it, and every document — folder, warrant, evidence bag, result table — is a lit thing on
   that dark ground rather than ink on a sheet.
   An earlier attempt kept the old cream sheet and put a wooden frame round it. That is not
   this design; it is the previous one wearing a border, and it read as exactly that. */
.stMainBlockContainer, .block-container {
  max-width:min(1240px, calc(100vw - 48px)); margin:0 auto;
  background:transparent; color:var(--bone);
  padding:0 24px 72px !important;
  /* The masthead bleeds past these paddings with a negative margin; without this the bleed
     pushes a horizontal scrollbar onto the page. */
  overflow-x:hidden; }
html, body, [class*="css"] { font-family:var(--f-body); color:var(--bone); }
/* Headings sit on the room, so they are bone rather than ink. The exception is any heading
   inside a document — those are handled where the document is styled. */
h1,h2,h3 { font-family:var(--f-display) !important; letter-spacing:-.015em; color:var(--bone); }
.stApp, .stMarkdown { color:var(--bone); }
[data-testid="stCaptionContainer"] { color:var(--ash); }

/* --- the masthead ----------------------------------------------------------------- */
/* A navy chrome bar across the top of the sheet, the way the design draws it: wordmark,
   a CASE FILES plate, and the run's numbers pushed to the right. */
/* No chrome bar. The design has no masthead: the archive opens on a bordered plate at the
   left and the run's numbers at the right, both floating on the room, so the eye goes
   straight to the desk. The bar was the old design's furniture and it was the loudest thing
   left in the room. Wrapping is allowed here rather than clipped — this row has no fixed
   height to protect, so a narrow screen puts the numbers on their own line instead of
   silently cutting the rank plate off the right edge, which is how this bar failed twice. */
.pi-mast { display:flex; align-items:center; justify-content:space-between;
  gap:10px 14px; flex-wrap:wrap; background:transparent; color:var(--bone);
  margin:0 0 4px; padding:clamp(10px,2vh,20px) 0 0; min-height:44px; }
/* The design's plate carries the whole name, so the h1 IS the plate — a bordered gold
   nameplate on the wall rather than a wordmark beside a badge. It stays an h1 because the
   document needs exactly one top-level heading and a screen-reader user pressing "1" has
   to land somewhere. */
/* `!important` on the size and weight for the same reason the block above needs it on the
   family: Streamlit styles `h1` by a selector this cannot outrank, and without it the
   nameplate renders at heading size and fills the wall. */
.pi-logo { font-family:var(--f-mono) !important; font-weight:400 !important;
  font-size:11px !important; letter-spacing:.2em;
  text-transform:uppercase; color:var(--gold) !important; margin:0; line-height:1.4;
  display:inline-block; white-space:nowrap;
  border:1px solid rgba(201,179,126,.5); border-radius:2px; padding:8px 14px;
  background:linear-gradient(180deg, rgba(201,179,126,.14), rgba(201,179,126,.04)); }
/* The old design split the name across two colours inside the wordmark. On the plate the
   whole line is one colour, so this only has to stop inheriting a different one. */
.pi-logo span { color:inherit; }
/* The source link. Sized to the 24px floor WCAG 2.5.8 asks of a pointer target rather than
   to the 15px icon inside it, and it keeps a visible focus ring because it is the one
   control on the masthead a keyboard reaches. */
.pi-mast-src { display:inline-flex; align-items:center; gap:7px; flex:0 0 auto;
  font-family:var(--f-mono); font-size:10px; letter-spacing:.14em; text-decoration:none;
  color:var(--gold); border:1px solid var(--chrome-line); border-radius:2px;
  padding:5px 9px; min-height:24px; transition:color .15s ease, border-color .15s ease; }
.pi-mast-src:hover { color:var(--bone); border-color:var(--gold); }
.pi-mast-src:focus-visible { outline:2px solid var(--gold); outline-offset:2px; }
/* Below the tablet breakpoint the masthead has to give something up before it wraps. The
   word goes and the icon stays: it is still a 24px target and still reachable, and the
   anchor's own `aria-label` keeps it named for anyone who cannot see the mark — which is
   why the name lives there rather than on the text this rule hides. */
@media (max-width: 720px) { .pi-mast-src span { display:none; } }
/* The run's numbers and the source link, held together at the right so they wrap as one
   group rather than the link peeling off on its own. */
.pi-mast-right { display:inline-flex; align-items:center; gap:12px; flex-wrap:wrap;
  justify-content:flex-end; }
.pi-eyebrow { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.18em;
  text-transform:uppercase; color:var(--red); font-weight:600; }
.pi-bigq { font-family:var(--f-display); font-size:44px; font-weight:700;
  line-height:1.12; letter-spacing:-.015em; margin:12px 0 16px; color:var(--ink);
  text-wrap:pretty; }
.pi-claim { font-family:var(--f-display); font-size:29px; font-weight:700;
  line-height:1.25; letter-spacing:-.01em; color:var(--ink); }

/* --- native Streamlit widgets, made to belong ------------------------------------- */
/* Controls are mono, uppercase and squared — evidence-room stamps, not web buttons. The
   default is outlined ink; the primary one (open a file, cross-examine, print) is filled. */
.stButton > button, .stFormSubmitButton > button {
  font-family:var(--f-mono) !important; text-transform:uppercase; letter-spacing:.12em;
  font-weight:500; font-size:12px; border-radius:3px; border:1.5px solid var(--ink);
  background:transparent; color:var(--ink); padding:10px 18px; transition:all .14s ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background:var(--ink); color:var(--bone); border-color:var(--ink);
  transform:translateY(-1px); box-shadow:0 4px 14px rgba(27,32,39,.22); }
.stButton > button[kind="primary"], .stFormSubmitButton > button {
  background:var(--ink); color:var(--bone); border-color:var(--ink); }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
  background:var(--red); border-color:var(--red); color:var(--bone); }
/* The stake radio, as the design's three certainty cards. */
[data-testid="stRadio"] label { color:var(--ink) !important;
  font-family:var(--f-mono) !important; font-size:12px !important; letter-spacing:.08em; }
[data-testid="stRadio"] [data-baseweb="radio"] div:first-child {
  border-color:var(--faint) !important; width:22px !important; height:22px !important; }
/* The stake is the one control a child changes under time pressure, and its hit area was
   13px. The label carries the real target, so this grows the row rather than the dot. */
[data-testid="stRadio"] label { min-height:34px; display:flex; align-items:center; }
/* The typed claim, on the design's ruled line. */
[data-testid="stTextInput"] input {
  background:var(--paper) !important; color:var(--ink) !important;
  border:none !important; border-bottom:2px solid var(--ink) !important;
  border-radius:0 !important; font-family:var(--f-mono) !important; font-size:15px !important; }
[data-testid="stTextInput"] input::placeholder { color:var(--faint) !important; }
[data-testid="stDivider"] hr, hr { border-color:var(--rule) !important; }
/* The result rows are the evidence strip: cream paper, ruled, mono. */
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
  --gdg-bg-cell:#FFFDF6; --gdg-bg-header:#F1ECDD; --gdg-text-dark:#1B2027;
  --gdg-text-header:#6E7266; --gdg-border-color:#DDD5C2;
  --gdg-horizontal-border-color:#EFE9D8; --gdg-bg-header-hovered:#E9E3D2;
  --gdg-bg-cell-medium:#F7F3E8; --gdg-font-family:"IBM Plex Mono", ui-monospace, monospace;
  border:1px solid var(--rule); }

/* pre-wrap, not pre. Genie emits a query as one long line; with `pre` that overflowed the
   panel by three times its width and a child saw a truncated query with a scrollbar.
   Wrapping keeps the text verbatim and keeps all of it on screen. */
/* The warrant: the query, typed onto a filed sheet with a red margin rule down the left,
   the way the design draws it. Not a code block — a document. */
.pi-sql { font-family:var(--f-mono); font-size:13px; line-height:1.9; color:var(--ink);
  background:var(--paper); border:1px solid var(--rule); border-radius:2px;
  padding:22px 26px 20px 44px; white-space:pre-wrap; overflow-wrap:anywhere;
  position:relative; box-shadow:0 2px 12px rgba(27,32,39,.07); }
.pi-sql::before { content:""; position:absolute; left:30px; top:0; bottom:0; width:1px;
  background:#E8B7B0; }
/* Additions are inline marks, so the new columns highlight wherever they fall rather than
   depending on the query being split across lines. */
/* The added columns, highlighted the way a marker pen would on the filed sheet. */
.pi-sql mark.add { background:#DDEBE1; color:var(--green); font-weight:700;
  box-shadow:0 0 0 2px #DDEBE1; border-radius:2px; }
.pi-sql .del { background:#F4DEDC; opacity:.7; text-decoration:line-through;
  color:var(--red); }

/* Genie's reasoning: dashed-ruled rows on cream, each labelled in navy. */
.pi-step { border-bottom:1px dashed var(--rule); padding:12px 0; }
.pi-step:last-child { border-bottom:0; }
.pi-step .t { font-family:var(--f-mono); font-size:9.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--navy); font-weight:600; }
.pi-step .b { font-size:16px; line-height:1.6; margin-top:5px; color:var(--ink); }

.pi-verdict { display:inline-block; font-family:var(--f-display);
  font-weight:700; font-size:12px; letter-spacing:.05em; text-transform:uppercase;
  padding:6px 13px; }
/* A verdict is a rubber stamp: heavy mono, a 2.5px box in its own colour, tilted. */
.pi-verdict { border-width:2.5px; border-style:solid; border-radius:3px;
  transform:rotate(-4deg); background:transparent; }
.v-busted { color:var(--red); border-color:var(--red); }
.v-holds { color:var(--green); border-color:var(--green); }
.v-nodata { color:var(--gold-deep); border-color:var(--gold-deep); }
/* Half true reads between the other two on purpose: navy, not a third warm colour.
   Green/gold/red would put it on a severity scale it does not belong on — it is not a
   weaker BUSTED, it is a different kind of answer. */
.v-half { color:var(--navy); border-color:var(--navy); }

.pi-punch { font-family:var(--f-display); font-weight:600; font-size:18px;
  line-height:1.45; margin-top:14px; color:var(--ink); }

/* --- the antibody wall -------------------------------------------------------------- */
.pi-wall-summary { font-family:var(--f-display); font-weight:600; font-size:18px;
  line-height:1.45; margin-bottom:16px; color:var(--ink); }
/* Auto-fit rather than a fixed column count: the wall holds one card after a single case
   and four after a full session, and a three-column grid with one card in it looks like
   two cards failed to load. */
.pi-wall { display:grid; gap:14px; margin-bottom:18px;
  grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); }
/* The antibody kit: each trick survived is a collectible card, minted on the manila stock
   with a gold rule — a thing you earned rather than a paragraph you read. */
.pi-card { border:1px solid var(--manila-line); border-top:3px solid var(--gold-bar);
  background:var(--manila); padding:16px 18px; border-radius:0 0 3px 3px;
  box-shadow:0 2px 10px rgba(27,32,39,.08); }
.pi-card-trick { font-family:var(--f-display); font-weight:700; font-size:19px;
  color:var(--ink); margin-bottom:7px; letter-spacing:-.01em; }
.pi-card-lesson { font-size:13.5px; line-height:1.6; color:var(--slate); }
.pi-card-wild { font-family:var(--f-mono); font-size:11px; line-height:1.55;
  /* Measured 4.17:1 on the antibody card's manila. This is the line naming where the
     trick shows up in the wild — the one sentence a child is meant to carry out of the
     room, so it has to be legible on a projector. */
  color:#845F1E; margin-top:9px; }

/* --- the docket: a drawer of case files -------------------------------------------- */
.pi-lede { font-size:16.5px; line-height:1.65; color:var(--pencil); max-width:56ch;
  margin-bottom:30px; }
/* --- scene two: the desk and the board ---------------------------------------------- */
/* A case is worked on a corkboard in a wooden frame, not on the bare desk. The marker is
   emitted by the case beats, so the archive keeps its dark room and only the screens that
   hold a case get the board.

   Nothing sits bare on the cork. Measured: the app's prose colour is 2.04:1 on #B08A55 and
   only `ink` clears AA there at 5.16 — which is why the design pins every piece of content
   to a card, and why the reasoning column below becomes one instead of floating. */
.stMainBlockContainer:has(.pi-board), .block-container:has(.pi-board) {
  background:linear-gradient(160deg, var(--cork), var(--cork-mid) 55%, var(--cork-deep));
  border:clamp(9px,1.1vw,15px) solid var(--cork-frame);
  border-image:linear-gradient(180deg, #5C4028, #4A3120) 1;
  border-radius:6px; margin:14px auto 44px;
  padding:0 clamp(16px,2.4vw,34px) 56px !important;
  box-shadow:0 18px 60px rgba(0,0,0,.6), inset 0 0 80px rgba(40,24,8,.55); }
/* The cork's own tooth. */
.stMainBlockContainer:has(.pi-board)::before, .block-container:has(.pi-board)::before {
  content:""; position:absolute; inset:0; pointer-events:none; z-index:0;
  background-image:
    radial-gradient(rgba(60,38,16,.22) 1.2px, transparent 1.3px),
    radial-gradient(rgba(255,230,190,.1) 1px, transparent 1.1px);
  background-size:26px 26px, 34px 34px; background-position:0 0, 12px 9px; }
.stMainBlockContainer:has(.pi-board), .block-container:has(.pi-board) { position:relative; }
.stMainBlockContainer:has(.pi-board) > *, .block-container:has(.pi-board) > * {
  position:relative; z-index:1; }
/* The marker itself shows nothing. */
.pi-board { display:none; }

/* On the board, every word is either on a card or in ink. These are the ones that were
   floating: the claim, the rail label and the custody line. */
.pi-board ~ * .pi-claim, .stMainBlockContainer:has(.pi-board) .pi-claim,
.stMainBlockContainer:has(.pi-board) h2 { color:var(--ink) !important;
  text-shadow:0 1px 0 rgba(255,240,214,.25); }
.stMainBlockContainer:has(.pi-board) .pi-rail-label,
.stMainBlockContainer:has(.pi-board) .pi-vlabel { color:var(--ink); }
.stMainBlockContainer:has(.pi-board) [data-testid="stCaptionContainer"] { color:var(--ink); }
/* The header and the custody line ride on the board too, and the room's own gold measures
   1.5:1 on cork. Everything up here goes to ink, which is the one colour that clears AA on
   it, and the nameplate's wash goes with it. */
.stMainBlockContainer:has(.pi-board) .pi-logo { color:var(--ink) !important;
  border-color:rgba(51,40,26,.45); background:rgba(255,247,225,.28); }
.stMainBlockContainer:has(.pi-board) .pi-hud,
.stMainBlockContainer:has(.pi-board) .pi-hud-docket,
.stMainBlockContainer:has(.pi-board) .pi-hud-rank,
.stMainBlockContainer:has(.pi-board) .pi-hud-chips,
.stMainBlockContainer:has(.pi-board) .pi-custody,
.stMainBlockContainer:has(.pi-board) .pi-mast-src { color:var(--ink); }
.stMainBlockContainer:has(.pi-board) .pi-hud-rank,
.stMainBlockContainer:has(.pi-board) .pi-mast-src { border-color:rgba(51,40,26,.45); }
.stMainBlockContainer:has(.pi-board) .pi-mast-src:hover { color:var(--busted); }
/* Genie's reasoning is a document like the warrant beside it, so on the board it becomes a
   pinned card. Matched on the column that holds the steps rather than wrapped in markup: a
   Streamlit container created inside a column and written to afterwards re-emits that
   column, which is what once put a second, greyed-out copy of a case on the docket. */
.stMainBlockContainer:has(.pi-board) [data-testid="stColumn"]:has(.pi-step) {
  background:var(--paper); border:1px solid var(--rule); border-radius:2px;
  padding:14px 18px 4px; box-shadow:0 10px 26px rgba(0,0,0,.4);
  align-self:flex-start; }
/* Its own label rides on the card, so it goes back to the quiet ink it had on paper. */
.stMainBlockContainer:has(.pi-board) [data-testid="stColumn"]:has(.pi-step) .pi-vlabel {
  color:var(--pencil); }

/* --- the archive's opening --------------------------------------------------------- */
/* Centred under the lamp. The line lengths are capped in `ch` rather than px so the balance
   holds at every size the clamp produces. */
.pi-hero { text-align:center; padding:clamp(26px,6vh,76px) 8px clamp(20px,4vh,44px); }
.pi-hero-where { font-family:var(--f-mono); font-size:clamp(10px,1.3vw,13px);
  letter-spacing:.5em; text-transform:uppercase; color:var(--gold); margin:0;
  /* The letter-spacing pushes the last glyph off centre; this puts it back. */
  text-indent:.5em; }
/* Centred explicitly rather than by inheritance: these are an h2 and a p inside a Streamlit
   markdown block, and Streamlit sets its own alignment and margins on both, which left the
   headline ranged against the left edge of a centred box. */
.pi-hero-line { font-family:var(--f-display); font-size:clamp(28px,4.6vw,54px) !important;
  font-weight:700; letter-spacing:-.01em; line-height:1.1; color:var(--bone);
  margin:12px auto 0 !important; max-width:18ch; text-align:center; text-wrap:balance;
  padding:0; text-shadow:0 4px 30px rgba(0,0,0,.6); }
/* `!important` on the alignment for the same reason the headline needs it: Streamlit styles
   `p` inside a markdown block by a selector this cannot outrank, and both of these sat
   ranged left under a centred headline. */
.pi-hero-sub { font-family:var(--f-display); font-size:clamp(16px,2vw,22px); font-style:italic;
  color:var(--mist); margin:8px auto 0 !important; max-width:34ch;
  text-align:center !important; text-wrap:balance; }
.pi-hero-rule { font-family:var(--f-mono); font-size:clamp(10px,1.2vw,12px);
  letter-spacing:.14em; text-transform:uppercase; color:var(--ash); line-height:1.8;
  margin:16px auto 0 !important; max-width:62ch; text-align:center !important;
  text-wrap:balance; }
.pi-hero-where { text-align:center !important; }

/* The two standing facts, along the bottom of the archive. Both are checkable, which is why
   they are chrome rather than copy: the first is what the build gate enforces, the second is
   what having no account store means. */
.pi-standing { display:flex; justify-content:space-between; gap:8px 22px; flex-wrap:wrap;
  font-family:var(--f-mono); font-size:10.5px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--ash); line-height:1.7; margin:38px 0 0;
  border-top:1px solid rgba(155,163,173,.18); padding-top:16px; }

/* --- the folder ------------------------------------------------------------------- */
/* A closed case folder lying in the drawer: a tab, a sheet inside carrying the claim, and a
   flap over the front carrying the case number and the trick. Reaching for it lifts the flap
   and slides the sheet up, so the claim is what opening it reveals — which is the design's
   whole gesture, and the reason the front says "The Paradox" rather than the claim itself.
   Three layers, stacked in one positioned box so nothing depends on source order. */
/* The drawer wraps. Streamlit columns do not answer to a breakpoint — asked for five they
   give five at any width, and at 768px that meant five 128px slivers with their labels
   wrapping to different heights. Turning the row into a wrapping flex of fixed-width
   folders is what makes the docket responsive: five abreast on a desktop, two on a tablet,
   one on a phone, and the folder itself the same object at every one of them. */
[data-testid="stHorizontalBlock"]:has(.pi-folder) {
  flex-wrap:wrap; justify-content:center; gap:18px; }
[data-testid="stHorizontalBlock"]:has(.pi-folder) > [data-testid="stColumn"] {
  flex:0 0 auto; width:230px; min-width:0; }

/* A folder is an object with a shape. Stretched to fill a column it stopped being one and
   became a banner, so it takes the design's own width and the column is sized to it. */
.pi-folder { position:relative; height:186px; margin:26px auto 0; width:100%;
  --tilt:0deg; --lift:0px; --scale:1;
  transform:rotate(var(--tilt)) translateY(var(--lift)) scale(var(--scale));
  transform-origin:50% 92%; transition:transform .34s cubic-bezier(.2,.9,.3,1.15); }
/* The tab, sitting proud of the folder's top-left corner. */
.pi-folder-tab { position:absolute; left:0; top:-15px; width:108px; height:22px;
  background:var(--folder-tab); border-radius:5px 5px 0 0; z-index:1; }
/* The sheet inside. Tucked down behind the flap at rest and never hidden: `display:none`
   would take the claim out of the accessibility tree, and the claim is the case. */
.pi-folder-sheet { position:absolute; left:11px; right:11px; top:-4px; bottom:26px;
  background:var(--paper); border:1px solid var(--manila-line); border-radius:2px;
  padding:13px 15px; box-sizing:border-box; z-index:2; overflow:hidden;
  box-shadow:0 -4px 14px rgba(0,0,0,.28);
  transform:translateY(30px); transition:transform .34s ease; }
.pi-folder-claim { font-family:var(--f-display); font-size:16.5px; font-weight:700;
  line-height:1.42; color:var(--ink); margin:0; }
.pi-folder-source { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.07em;
  line-height:1.6; color:var(--folder-sheet-ink); margin:7px 0 0; }
/* The flap over the front. Hinged at the bottom, so lifting it reads as opening a cover
   rather than as a card sliding away. */
.pi-folder-flap { position:absolute; inset:0; z-index:3; display:flex;
  flex-direction:column; gap:6px; padding:16px 18px; box-sizing:border-box;
  background:linear-gradient(180deg, var(--folder), var(--folder-deep));
  border-radius:0 4px 4px 4px; box-shadow:0 12px 26px rgba(0,0,0,.5);
  transform-origin:bottom center; transition:transform .34s ease; }
.pi-folder-no { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.18em;
  text-transform:uppercase; color:var(--folder-ink-soft); }
.pi-folder-title { font-family:var(--f-display); font-size:19px; font-weight:700;
  line-height:1.25; color:var(--folder-ink); }
.pi-folder-shape { font-family:var(--f-mono); font-size:10px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--folder-ink-soft); }
/* The brass stud on the flap, bottom-left, the way the design draws it. */
.pi-folder-stud { position:absolute; left:18px; bottom:14px; width:15px; height:15px;
  border-radius:50%; border:2px solid var(--folder-stud-rim);
  background:radial-gradient(circle at 35% 35%, var(--folder-stud), var(--folder-stud-rim)); }

/* Folders do not lie square in a drawer. The angle is a custom property rather than a
   `transform` of its own so the reduced-motion block can cancel the lift and leave the
   angle standing: an earlier version set `transform:none` on hover, which stripped the
   resting rotation too, so a reader who asked for less motion got the folder snapping
   square the instant a pointer touched it — a jump, from the rule meant to prevent jumps.
   Matched on a class the card carries, not `:nth-of-type` on the column: Streamlit renders
   each docket row as its own columns container, so the count restarts every row and three
   of these five angles never appeared at all. */
[data-testid="stColumn"]:has(.pi-tilt-0) .pi-folder { --tilt:-2.6deg; }
[data-testid="stColumn"]:has(.pi-tilt-1) .pi-folder { --tilt:-.6deg; }
[data-testid="stColumn"]:has(.pi-tilt-2) .pi-folder { --tilt:1.4deg; }
[data-testid="stColumn"]:has(.pi-tilt-3) .pi-folder { --tilt:2.6deg; }
[data-testid="stColumn"]:has(.pi-tilt-4) .pi-folder { --tilt:3.8deg; }

/* Reaching for a folder opens it. The hover target is the whole column, because a folder is
   two Streamlit elements — the markdown block and the button under it — and lifting only
   one of them tears the object in half. Focus does the same thing, so the reveal is
   reachable by keyboard rather than being a pointer-only affordance. */
[data-testid="stColumn"]:has(.pi-folder):hover .pi-folder,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder {
  --lift:-12px; --scale:1.03; }
[data-testid="stColumn"]:has(.pi-folder):hover,
[data-testid="stColumn"]:has(.pi-folder):focus-within { z-index:3; }
[data-testid="stColumn"]:has(.pi-folder):hover .pi-folder-flap,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder-flap {
  transform:rotateX(-64deg); }
[data-testid="stColumn"]:has(.pi-folder):hover .pi-folder-sheet,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder-sheet {
  transform:translateY(0); }
/* The flap hinges in three dimensions, so the column it lives in needs the depth. */
[data-testid="stColumn"]:has(.pi-folder) { perspective:900px; }

/* The Open control, the folder's bottom lip. Scoped by the key prefix Streamlit puts on the
   element, so no other button on the app is touched. */
[class*="st-key-case-"] .stButton > button {
  width:100%; margin:0 auto;
  border-radius:0 0 4px 4px;
  border:1px solid var(--folder-deep); border-top:none;
  background:var(--folder-deep); color:var(--folder-ink);
  font-family:var(--f-mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase;
  line-height:1.4; padding:6px 8px;
  /* Every lip the same height whether its label wraps to one line or two: five folders
     standing at five different heights is not a drawer, it is a bar chart. Sized to the
     two-line case, which is the longest title at the widest the folder ever gets, and
     centred so a one-line label sits in the middle of it rather than at the top. Well
     clear of the 24px pointer-target floor. */
  min-height:58px; display:flex; align-items:center; justify-content:center; }
/* Streamlit puts a gap between every two elements. Between the folder and its own bottom
   lip that gap is a seam through the middle of one object. */
[class*="st-key-case-"] { margin-top:-8px; }
[class*="st-key-case-"] .stButton > button:hover,
[data-testid="stColumn"]:has(.pi-folder):hover [class*="st-key-case-"] .stButton > button {
  background:var(--ink); color:var(--bone); border-color:var(--ink); transform:none; }

/* A drawer of folders that flip open as a pointer crosses them is exactly the motion a
   vestibular disorder reacts to. The angle stays — it is identity, not animation — and
   every movement goes. The claim has to stay reachable, so with motion off the sheet is
   simply not covered: the flap drops out rather than swinging away. */
@media (prefers-reduced-motion: reduce) {
  .pi-folder, .pi-folder-sheet, .pi-folder-flap { transition:none; }
  [data-testid="stColumn"]:has(.pi-folder):hover .pi-folder,
  [data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder {
    --lift:0px; --scale:1; }
  [data-testid="stColumn"]:has(.pi-folder):hover .pi-folder-flap,
  [data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder-flap {
    transform:none; opacity:0; }
}
/* The scroll frame is a script with nothing to show. Hidden outright rather than left as a
   one-pixel row, which would still cost the block's gap under the masthead. One pixel
   rather than none because `st.iframe` rejects a height of zero.
   `[srcdoc]` keeps this to inline frames: the estimate ruler is a component served from a
   URL, and Streamlit gives it height="0" until it reports its own size — a rule without
   that guard hid the ruler for good, since a hidden frame never gets to report. */
.stElementContainer:has(iframe[height="1"][srcdoc]) { display:none; }

/* Streamlit's info box, repainted. Its stock blue text on a blue wash measured 2.05:1 —
   on the line that says why reading the query matters more than reading the answer, which
   is the sentence the entire app exists to deliver. */
[data-testid="stAlert"], [data-testid="stAlertContainer"] {
  background:var(--accent-soft) !important; border-left:3px solid var(--accent) !important;
  border-radius:2px !important; }
[data-testid="stAlert"] *, [data-testid="stAlertContainer"] * {
  color:var(--ink) !important; }

/* Where you are in the case. "Step 2 of 5" used to be 10.5px uppercase mono — the smallest
   text on a screen whose whole job is momentum. A rail states the same fact at a glance:
   the end is visible from the start, and each beat is a segment earned. */
.pi-rail { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin:6px 0 18px; }
.pi-rail-track { display:flex; gap:5px; flex:none; }
.pi-rail-seg { width:34px; height:7px; border-radius:4px; background:var(--rule);
  transition:background .3s ease, transform .3s ease; }
.pi-rail-seg.is-done { background:var(--gold-bar); }
/* The current beat is wider and in the case-file red, so the eye lands on "you are here"
   rather than counting filled segments. */
.pi-rail-seg.is-now { background:var(--red); width:46px; }
.pi-rail-label { font-family:var(--f-mono); font-size:12.5px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--red); font-weight:600; }
@media (prefers-reduced-motion: reduce) { .pi-rail-seg { transition:none; } }
@media (max-width: 520px) {
  .pi-rail-seg { width:20px; }
  .pi-rail-seg.is-now { width:28px; }
  .pi-rail-label { font-size:11px; }
}

/* --- the retrial ------------------------------------------------------------------ */
.pi-chiprow { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:2px 0 4px; }

/* One letter, used three times: on the highlight in the SQL, and on the line that says
   what that column revealed. Same letter, same thing. */
.pi-ex { display:inline-grid; place-items:center; width:17px; height:17px; flex:none;
  font-family:var(--f-display); font-size:11px; font-weight:700; line-height:1;
  color:var(--paper); background:var(--holds); border-radius:3px; margin-right:6px;
  vertical-align:baseline; }

.pi-exhibits { display:flex; flex-direction:column; gap:10px; margin:16px 0 4px; }
.pi-exhibit { display:flex; gap:2px; align-items:flex-start; font-size:15px;
  color:var(--ink); line-height:1.55; padding:11px 15px; background:var(--paper);
  border:1px solid var(--rule); border-left:3px solid var(--green); border-radius:2px;
  opacity:0; animation:pi-rise .45s ease-out forwards; }
.pi-exhibit code { font-family:var(--f-mono); font-size:13px; background:var(--sheet);
  color:var(--ink); padding:1px 5px; border:1px solid var(--rule); margin-right:6px; }

/* Only fires when lesson_landed is true, i.e. the first verdict really was overturned. */
.pi-stamp { font-family:var(--f-display); font-weight:700; font-size:13px;
  letter-spacing:.08em; text-transform:uppercase; color:var(--busted);
  border:2px solid var(--busted); border-radius:3px; padding:3px 9px;
  transform:rotate(-7deg); opacity:0;
  animation:pi-stamp .5s cubic-bezier(.2,1.4,.4,1) 1.6s forwards; }

@keyframes pi-rise { from { opacity:0; transform:translateY(6px); }
                     to   { opacity:1; transform:none; } }
@keyframes pi-stamp { 0% { opacity:0; transform:rotate(-7deg) scale(1.9); }
                      60%{ opacity:1; transform:rotate(-7deg) scale(.94); }
                      100%{ opacity:1; transform:rotate(-7deg) scale(1); } }

/* Motion is decoration here; the content must be complete without it. */
@media (prefers-reduced-motion: reduce) {
  .pi-exhibit, .pi-stamp { animation:none; opacity:1; transform:rotate(-7deg); }
  .pi-seal--open .blocks, .pi-verdict--arrive { animation:none; opacity:1; transform:none; }
  .pi-exhibit { transform:none; }
}
.pi-said { font-family:var(--f-mono); font-size:12.5px; background:var(--paper);
  color:var(--slate); border:1px solid var(--rule); border-left:3px solid var(--red);
  border-radius:2px; padding:11px 15px; margin:14px 0; }
/* --- the run: chips, streak, rank ------------------------------------------------ */
/* The HUD: a status readout on the board, same three numbers on every screen. Boxed and
   tabular so it reads as instrumentation the way a game's score bar does, not a sentence. */
/* The HUD lives in the navy chrome bar, so it reads as instrumentation on the app rather
   than as a line of text on the page. */
.pi-hud { display:inline-flex; gap:20px; align-items:center; font-family:var(--f-mono);
  font-size:11.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ash);
  font-variant-numeric:tabular-nums; min-width:0; }
.pi-hud-chips { color:var(--gold); font-weight:700; }
.pi-hud-streak.is-on { color:var(--gold); font-weight:700; }
/* The rank plate, outlined in gold like the design's EVIDENCE CLERK badge. */
.pi-hud-rank { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.12em;
  border:1px solid var(--gold); color:var(--gold); border-radius:2px; padding:4px 10px;
  white-space:nowrap; }

/* On a narrow screen the masthead cannot hold all four readouts, and it clips from the
   right — which silently took the RANK PLATE off screen, the one part of the HUD that is
   the reward. So the strip sheds detail in order of what it can afford to lose: the
   docket count first (the receipt says it too), then the streak. The score and the rank
   always survive, because those are what the player is playing for. */
@media (max-width: 720px) {
  /* The sheet's 56px margins are a desk-sized luxury; on a phone they cost a third of the
     line. The masthead's negative margin has to shrink with them or it stops bleeding to
     the edges and leaves a cream gutter beside the navy bar. */
  /* The room gives up its margin before the text does. A 104px gutter is a desk on a
     monitor and a third of the line on a phone, so below this width the case file runs
     nearly edge to edge and the frame thins to match. */
  .stMainBlockContainer, .block-container { padding-left:18px !important;
    padding-right:18px !important;
    max-width:calc(100vw - 16px); margin:8px auto 20px; border-width:5px; }
  .pi-mast { margin-left:-18px; margin-right:-18px; gap:10px; padding:0 14px; }
  .pi-hud { gap:12px; font-size:10.5px; }
  .pi-plate { display:none; }
}
/* The docket counter sheds earlier than the rest, because between 721px and 849px the bar
   has its full chrome — plate, counter, score, streak, rank, source — and not the width for
   it. Measured at 768px, an iPad in portrait and one of this app's four target widths: the
   row overflowed by 17px and `overflow:hidden` took the RANK PLATE off the right edge with
   no cue, which is the same silent clip this bar was fixed for once before. The counter is
   the right thing to drop: the step rail on every case screen already says where the player
   is, so it is the one readout here that is duplicated elsewhere. */
@media (max-width: 860px) { .pi-hud-docket { display:none; } }
@media (max-width: 520px) {
  .pi-hud-streak { display:none; }
  .pi-logo { font-size:16px; }
}
/* Below the smallest width in the device matrix there is still a real phone — a 320px
   handset — and on it the longest rank title, FIELD INVESTIGATOR at 155px, was pushing the
   plate off the right edge by 26px. The plate is tightened rather than dropped: rank is the
   readout the whole score exists to move, and a player who has earned one should be able to
   see it on whatever they are holding. */
@media (max-width: 374px) {
  .pi-hud-rank { font-size:9px; letter-spacing:.06em; padding:3px 6px; }
  .pi-hud { gap:9px; }
}
.pi-stakeline { font-family:var(--f-mono); font-size:11px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--red); font-weight:600; margin:-4px 0 10px; }
/* The call standing at the reveal, and what it paid at the retrial. The payout borrows
   the verdict colours because the outcome IS a verdict on the player, and the only alarm
   colour on the page stays reserved for a loss. */
.pi-call { font-family:var(--f-mono); font-size:12px; letter-spacing:.06em;
  background:var(--paper); color:var(--slate); padding:12px 18px; margin:6px 0 12px;
  border:1px solid var(--rule); border-left:3px solid var(--navy); border-radius:2px; }
.pi-call b { color:var(--navy); }
/* The payout chit: a torn slip pinned at an angle, the way the design lands points. */
.pi-payout { display:inline-block; font-family:var(--f-mono); font-weight:600;
  font-size:13.5px; letter-spacing:.04em; padding:10px 16px; margin:14px 0;
  background:#FFF7DC; border:1.5px dashed var(--gold); border-radius:2px;
  color:#6E6042; transform:rotate(-1.5deg); box-shadow:0 4px 10px rgba(27,32,39,.15); }
.pi-payout--win { border-color:var(--green); color:var(--green); background:#EEF5F0; }
.pi-payout--loss { border-color:var(--red); color:var(--red); background:#FBEDEC; }
.pi-payout--void { border-color:var(--gold-deep); color:var(--gold-deep); }
/* Case closed: the run's plinth, on manila with a gold rule and the rank in serif. */
.pi-run { border:1px solid var(--manila-line); border-top:3px solid var(--gold-bar);
  padding:22px 26px; background:var(--manila); margin:16px 0;
  box-shadow:0 4px 18px rgba(27,32,39,.12); }
.pi-rank { font-family:var(--f-display); font-weight:700; font-size:38px;
  letter-spacing:-.02em; margin:2px 0 8px; color:var(--ink); }
.pi-runrow { font-family:var(--f-mono); font-size:12px; color:#6E6042; margin-top:5px;
  letter-spacing:.06em; }

/* The receipt stays a LIGHT card — it is the printed artifact you leave with, and a paper
   receipt on the dark board is exactly right. */
.pi-receipt { border:1px solid var(--rule); padding:18px; background:var(--paper);
  color:var(--ink); }
.pi-receipt .pi-claim { color:var(--ink); }
.pi-rrow { display:flex; justify-content:space-between; gap:12px; font-size:13.5px;
  border-bottom:1px dotted var(--rule); padding:6px 0; color:var(--ink); }
.pi-rrow span:last-child { font-family:var(--f-mono); color:var(--pencil); }
/* Air above, because this is a section label and something always precedes it. Without
   the top margin the columns stack on a phone and it butts straight onto the step
   eyebrow above — two lines of small uppercase mono running together as one block. */
.pi-vlabel { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.18em;
  text-transform:uppercase; color:#64685C; font-weight:600;
  margin:16px 0 8px; }

/* --- the seal, and where the queries came from ------------------------------------ */

/* The locked and open states are one element with one class swapped, because they have
   to line up as stills: the video cuts between them, and a cut only reads as an unlock
   if nothing but the lock moves. */
/* The evidence bag: kraft paper, a torn-tape zigzag along the top, and a red SEALED band
   struck across it at an angle. This is the design's centrepiece for the withheld result,
   and it is the one element that has to read as a physical object. */
.pi-seal { position:relative; background:var(--kraft); border:1px solid var(--kraft-line);
  border-radius:3px; padding:74px 26px 30px; text-align:center; margin-top:20px;
  overflow:hidden; }
/* The torn top edge. */
.pi-seal::before { content:""; position:absolute; left:0; right:0; top:0; height:16px;
  background:
    linear-gradient(-45deg, var(--sheet) 8px, transparent 0),
    linear-gradient(45deg, var(--sheet) 8px, transparent 0);
  background-size:16px 16px; background-repeat:repeat-x; }
/* The red band. Tilted, wider than the bag, shadowed — tape over the opening. */
.pi-seal::after { content:"SEALED — DO NOT OPEN UNTIL A CALL IS IN";
  position:absolute; top:34px; left:-14px; right:-14px; height:44px;
  background:rgba(179,55,47,.92); transform:rotate(-2.5deg);
  display:flex; align-items:center; justify-content:center;
  font-family:var(--f-mono); font-weight:700; font-size:12px; letter-spacing:.28em;
  color:#F5E9E2; box-shadow:0 3px 10px rgba(27,32,39,.25); }
/* Opened, the band is gone and the bag is torn: same object, spent. */
.pi-seal--open { background:var(--kraft); }
.pi-seal--open::after { content:"SEAL BROKEN ON A COMMITTED CALL";
  background:rgba(179,55,47,.5); letter-spacing:.24em; }
.pi-seal .k { font-family:var(--f-mono); font-size:10px; letter-spacing:.2em;
  text-transform:uppercase; color:#5A4C2E; }
.pi-seal--open .k { color:#5A4C2E; }
/* Blocked-out digits where the number will be. The result is not merely absent, it is
   visibly withheld — which is the product's first rule, drawn. */
.pi-seal .blocks { font-family:var(--f-mono); font-size:32px; letter-spacing:.12em;
  color:#7E6430; margin:12px 0 6px; user-select:none; }
/* Struck through, not removed: the geometry has to match the sealed pose for the cut to
   land, but the digits must stop claiming to hide anything. */
.pi-seal--open .blocks { color:#7E6430; text-decoration:line-through;
  text-decoration-thickness:2.5px; animation:pi-unseal .55s cubic-bezier(.34,1.56,.64,1) both; }
/* Wordle's flip, in one axis: the blocked digits collapse to a line and come back struck
   through. The colour change happens at the midpoint, where nothing is visible, so the
   eye reads "flip, then struck" as one event rather than a swap. */
@keyframes pi-unseal {
  0% { transform:scaleY(1); text-decoration-color:transparent; }
  45% { transform:scaleY(.06); text-decoration-color:transparent; }
  55% { transform:scaleY(.06); text-decoration-color:currentColor; }
  100% { transform:scaleY(1); text-decoration-color:currentColor; } }
/* The first verdict chip arrives with the same overshoot as the slam's stamp, a beat after
   the seal has opened, so the order on screen is seal, then verdict. */
.pi-verdict--arrive { animation:pi-arrive .3s cubic-bezier(.34,1.56,.64,1) .45s both; }
@keyframes pi-arrive { from { opacity:0; transform:scale(1.6); } to { opacity:1; transform:none; } }
/* The bet, written on the bag in marker. */
.pi-seal .wager { font-family:var(--f-display); font-weight:700; font-size:17px;
  color:var(--red); margin-top:10px; letter-spacing:.01em; }
.pi-seal--open .wager { color:#5A4C2E; }
.pi-seal .q { font-family:var(--f-display); font-weight:600; font-size:18px;
  margin-top:10px; line-height:1.35; color:#4A4426; }
/* The tag is Genie's real attachment id: a paper chit taped to the bag, tilted. */
.pi-tag { display:inline-block; font-family:var(--f-mono); font-size:10.5px;
  letter-spacing:.1em; color:var(--slate); margin-top:14px;
  background:var(--paper); border:1px solid var(--kraft-line); border-radius:2px;
  padding:8px 14px; transform:rotate(-1deg); box-shadow:0 2px 6px rgba(27,32,39,.15); }
.pi-tag b { color:var(--ink); font-weight:700; letter-spacing:.16em; }

.pi-custody { font-family:var(--f-mono); font-size:10.5px; color:var(--slate);
  margin:8px 0 0; line-height:1.7; overflow-wrap:anywhere; letter-spacing:.05em; }
.pi-custody .same { color:var(--navy); font-weight:700; }

/* The provenance table stays a LIGHT card: it is the judge-facing receipt of ids, folded
   away in an expander, and a light ledger reads as the document it is. */
.pi-prov { border:1px solid var(--rule); background:var(--paper); padding:14px 16px;
  margin-top:12px; color:var(--ink); }
.pi-prov table { width:100%; border-collapse:collapse; font-family:var(--f-mono);
  font-size:11px; }
.pi-prov th { text-align:left; font-size:9.5px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--pencil); font-weight:600;
  padding:0 10px 6px 0; }
.pi-prov td { padding:5px 10px 5px 0; border-top:1px dotted var(--rule);
  overflow-wrap:anywhere; color:var(--ink); }
.pi-prov .note { font-family:var(--f-body); font-size:12.5px; line-height:1.55;
  color:var(--pencil); margin-top:10px; }

/* A case built from the player's own catalog rather than from the checked docket. Marked
   because it has never been run: the curated five advertise an arc someone measured, and
   this one cannot make that claim. */
.pi-case-new { font-family:var(--f-mono); font-size:9px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--gold-deep); border:1px solid var(--gold);
  border-radius:2px; padding:1px 5px; margin-left:8px; white-space:nowrap; }

/* --- the estimate, laid over the truth ------------------------------------------- */
/* Two marks on the ruler the player was given. The distance between them is the whole
   point — a number beside a number makes the reader do the comparison, and it is the
   seeing of the gap that does the teaching. */
.pi-est { margin:14px 0 16px; padding:12px 14px 10px; background:var(--paper);
  border:1px solid var(--rule); border-left:3px solid var(--faint); }
.pi-est--hit { border-left-color:var(--holds); }
.pi-est--miss { border-left-color:var(--gold-deep); }
.pi-est-rule { position:relative; height:22px; margin:2px 10px 8px;
  background:linear-gradient(var(--rule),var(--rule)) 0 50%/100% 2px no-repeat; }
/* The truth is a full-height stroke in case red; the player's mark is a ring. Different
   shapes as well as different colours, so the two never rely on hue alone to be told
   apart. */
.pi-est-truth { position:absolute; top:0; width:2px; height:100%; margin-left:-1px;
  background:var(--red); }
.pi-est-truth::after { content:"the data"; position:absolute; top:-2px; left:6px;
  font-family:var(--f-mono); font-size:9px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--red); white-space:nowrap; }
.pi-est-you { position:absolute; top:50%; width:14px; height:14px; margin:-7px 0 0 -7px;
  border-radius:50%; border:2px solid var(--ink); background:var(--paper); }
.pi-est-read { font-size:13.5px; line-height:1.5; color:var(--ink); }
.pi-est-read b { font-variant-numeric:tabular-nums; }
.pi-est--hit .pi-est-read b:last-child { color:var(--holds); }

/* OVERTURNED, stamped bigger and harder than a verdict chip — it is the moment the case
   turns, and the design gives it the largest stamp on the page. */
.pi-stamp { font-size:15px !important; letter-spacing:.1em !important;
  border-width:3px !important; padding:6px 14px !important;
  transform:rotate(-12deg) !important; }
</style>
"""

CSS = _CSS.replace("/*PALETTE*/", _root_block())
