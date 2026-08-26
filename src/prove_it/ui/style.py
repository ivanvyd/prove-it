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
    "desk": "#23262B",
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
/* The desk the folders lie on. */
.stApp { background:var(--desk); }

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
.stMainBlockContainer, .block-container {
  max-width:1240px; margin:0 auto; background:var(--sheet); color:var(--ink);
  padding:0 56px 72px !important; border-radius:3px;
  box-shadow:0 10px 40px rgba(0,0,0,.45);
  /* The masthead bleeds to the sheet's edges with a negative margin; without this the
     bleed pushes a horizontal scrollbar onto the page. */
  overflow-x:hidden; }
html, body, [class*="css"] { font-family:var(--f-body); color:var(--ink); }
h1,h2,h3 { font-family:var(--f-display) !important; letter-spacing:-.015em; color:var(--ink); }
.stApp, .stMarkdown { color:var(--ink); }
[data-testid="stCaptionContainer"] { color:var(--faint); }

/* --- the masthead ----------------------------------------------------------------- */
/* A navy chrome bar across the top of the sheet, the way the design draws it: wordmark,
   a CASE FILES plate, and the run's numbers pushed to the right. */
.pi-mast { display:flex; align-items:center; gap:18px; flex-wrap:nowrap;
  background:var(--chrome); color:var(--bone); margin:0 -56px 26px;
  padding:0 28px; height:56px; overflow:hidden; }
/* An h1 rather than a span, so the document has a top-level heading — margin and line
   height are reset because a browser's default h1 would push the 56px masthead open. */
.pi-logo { font-family:var(--f-display); font-weight:700; font-size:19px; color:var(--bone);
  margin:0; line-height:1.2; display:inline-block; }
.pi-logo span { color:var(--gold); }
.pi-plate { font-family:var(--f-mono); font-size:10px; letter-spacing:.22em;
  border:1px solid var(--chrome-line); border-radius:2px; padding:3px 8px; color:var(--gold); }
.pi-mast-spacer { flex:1; }
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
/* Each case is a manila folder: a tab with its number, then the folder body. The tab is
   drawn on the eyebrow so no extra markup is needed in app.py. */
.pi-case-trick { display:inline-block; font-family:var(--f-mono); font-size:10.5px;
  letter-spacing:.16em; text-transform:uppercase; color:#6B5D3F; font-weight:500;
  background:var(--manila-tab); border:1px solid var(--manila-line); border-bottom:none;
  border-radius:6px 6px 0 0; padding:8px 18px; margin:22px 0 0 18px; }
/* The folder itself. The negative top margin tucks it under the tab. */
.pi-case-claim { font-family:var(--f-display); font-size:23px; font-weight:700;
  line-height:1.3; letter-spacing:-.01em; color:var(--ink);
  background:var(--manila); border:1px solid var(--manila-line);
  border-radius:0 4px 0 0; padding:22px 26px 14px; margin:0; min-height:2.3em;
  box-shadow:0 2px 10px rgba(27,32,39,.08); }
/* The source line continues the folder; the Open button below it closes the folder, so a
   case reads as one object rather than a card with a control floating under it. */
.pi-case-source { font-family:var(--f-mono); font-size:12px; line-height:1.65;
  letter-spacing:.06em; color:#6E6042; background:var(--manila);
  border:1px solid var(--manila-line); border-top:none;
  padding:0 26px 16px; margin:0; min-height:3.2em; }
/* The Open control, tucked into the bottom of its folder. Scoped to the docket by the
   key prefix Streamlit puts on the element, so no other button on the app is affected. */
.stElementContainer:has(.pi-case-source) + .stElementContainer .stButton > button,
[class*="st-key-case-"] .stButton > button {
  width:100%; margin:0; border-radius:0 0 4px 4px; border-color:var(--manila-line);
  border-top:1px dashed var(--manila-line); background:var(--manila);
  box-shadow:0 2px 10px rgba(27,32,39,.08); }
/* Hovering anywhere on a folder opens it. The folder is three Streamlit elements — tab,
   cover and source line in one markdown block, the Open button in the next — so the hover
   target is the column they share: the cover tilts up from its bottom edge, the shadow
   deepens, and the clasp darkens. The clasp rule carries the same specificity as the
   resting rule above it on purpose: a plainer selector lost to it, and on hover the button
   kept its manila while the text went bone — white on a pale folder, unreadable. */
[data-testid="stColumn"]:has(.pi-case-claim) { perspective:1400px; }
.stElementContainer:has(.pi-case-claim) { transform-origin:50% 100%;
  transition:transform .3s cubic-bezier(.2,.8,.2,1); }
.pi-case-claim { transition:box-shadow .3s ease; }
[data-testid="stColumn"]:has(.pi-case-claim):hover .stElementContainer:has(.pi-case-claim) {
  transform:rotateX(-8deg) translateY(-4px); }
[data-testid="stColumn"]:has(.pi-case-claim):hover .pi-case-claim {
  box-shadow:0 18px 34px rgba(27,32,39,.22); }
[data-testid="stColumn"]:has(.pi-case-claim):hover .stElementContainer .stButton > button,
.stElementContainer:has(.pi-case-source) + .stElementContainer .stButton > button:hover,
[class*="st-key-case-"] .stButton > button:hover {
  background:var(--ink); color:var(--bone); border-color:var(--ink); transform:none; }
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
  .stElementContainer:has(.pi-case-claim), .pi-case-claim { transition:none; }
  [data-testid="stColumn"]:has(.pi-case-claim):hover .stElementContainer:has(.pi-case-claim) {
    transform:none; }
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
  .stMainBlockContainer, .block-container { padding-left:18px !important;
    padding-right:18px !important; }
  .pi-mast { margin-left:-18px; margin-right:-18px; gap:10px; padding:0 14px; }
  .pi-hud { gap:12px; font-size:10.5px; }
  .pi-hud-docket { display:none; }
  .pi-plate { display:none; }
}
@media (max-width: 520px) {
  .pi-hud-streak { display:none; }
  .pi-logo { font-size:16px; }
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
