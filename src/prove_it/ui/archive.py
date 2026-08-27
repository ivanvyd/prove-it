"""Scene one: the archive. The design file's opening screen, on the page.

A dark room, one lamp, a wooden desk across the bottom of the viewport, and the case files
lying on it as closed folders. Reaching for a folder lifts it, squashes its flap and slides
the sheet inside up far enough to read the claim; opening it flies the folder up out of
frame and the scene gives way to the board.

Everything here is markup and CSS. The room itself is painted by `ui/style.py` on the app
shell; this module lays the objects in it. Every measurement — folder sizes, rotations,
paddings, the hover physics — is the design's own, taken from the file rather than
approximated, and the one thing this module adds is that the folders wrap: the design shows
four abreast and this docket can hold fifteen.
"""

from __future__ import annotations

import html

from prove_it.domain.cases import Case
from prove_it.domain.game import CANT_TELL_POINTS, Run, rank_for
from prove_it.domain.verdict import Verdict
from prove_it.ui.render import source_link
from prove_it.ui.style import VERDICT_TEXT

# The design's five tilts, in the order its five folders carry them. A docket longer than
# five cycles through them; two folders three places apart sharing an angle still read as
# a drawer, and inventing more angles only makes the tilt look arbitrary.
TILTS = (-2.6, -0.6, 1.4, 2.6, 3.8)
OWN_TILT = 3.8

NUMBER_WORDS = {
    1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
    8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve",
}  # fmt: skip


def rumours_line(count: int) -> str:
    """The design's headline, with this docket's count in it: "Four rumours on the desk."

    The design was drawn for four. The number is the one thing on the line that is data,
    so it comes from the docket rather than being copied from the file.
    """
    word = NUMBER_WORDS.get(count, str(count))
    noun = "rumour" if count == 1 else "rumours"
    return f"{word} {noun} on the desk."


def trap_dots(trap: int) -> str:
    """TRAP ●●●○ — how deep the trap runs, out of four."""
    filled = max(0, min(4, trap))
    return "●" * filled + "○" * (4 - filled)


def source_tag(case: Case) -> str:
    """The short provenance line on the sheet inside a folder.

    The design writes these as tags — "REAL · SCIENCE 187 (1975)" — and a sheet 140px tall
    has no room for a full citation. The full source is on the claim clipping the moment
    the folder opens; this is the label on the drawer.
    """
    if not case.real_data:
        return "SYNTHETIC · FIXED SEED"
    head = case.source.split(" — ")[0].strip().rstrip(".")
    if len(head) > 28:
        head = head[:27].rstrip() + "…"
    return f"REAL · {head.upper()}" if head else "REAL DATA"


def header_bar(run: Run, kit: int, docket_size: int, source_url: str) -> str:
    """The design's top row: the nameplate at the left; the mark, the score, the rank and
    the kit at the right. The plate is the page's one h1."""
    rank = rank_for(run.points)
    return (
        '<div class="pi-hdr">'
        '<h1 class="pi-plate">Prove It &middot; The Evidence Room</h1>'
        '<div class="pi-hdr-r">'
        f"{source_link(source_url)}"
        f'<span class="pi-hdr-k">PTS <b>{run.points}</b></span>'
        f'<span class="pi-hdr-rank">{html.escape(rank.title.upper())}</span>'
        f'<span class="pi-hdr-k">KIT <b>{kit}/{docket_size}</b></span>'
        "</div></div>"
    )


def hero(count: int) -> str:
    return (
        '<div class="pi-hero">'
        '<div class="pi-hero-where">City archive &middot; after hours</div>'
        f'<h2 class="pi-hero-line">{html.escape(rumours_line(count))}</h2>'
        '<div class="pi-hero-sub">The archive will not tell you which are true.</div>'
        '<div class="pi-hero-rule">Genie writes the query &middot; the result stays sealed '
        "until you stake a prediction</div>"
        "</div>"
    )


def folder(case: Case, index: int, *, up_next: bool, closed: Verdict | None) -> str:
    """One case, as a closed folder on the desk.

    `up_next` marks the first case not yet closed: it gets the design's brighter flap, the
    UP NEXT badge and the reward line. `closed` is the verdict a case already called this
    session reached, stamped on its flap.

    The sheet inside is behind the flap, never hidden. `display:none` would take the claim
    out of the accessibility tree, and the claim is the case.
    """
    number = index + 1
    kind = "next" if up_next else "case"
    tilt = TILTS[index % len(TILTS)]
    unchecked = (
        '<span class="pi-case-new">found in your data &middot; unchecked</span>'
        if not case.probed
        else ""
    )
    badge = '<span class="pi-fnext">Up next</span>' if up_next else ""
    reward = f"<span>Reward: antibody N&ordm;{number}</span>" if up_next else ""
    stamp = (
        f'<span class="pi-fstamp">Closed &middot; {html.escape(VERDICT_TEXT[closed][0])}</span>'
        if closed is not None
        else ""
    )
    note = f'<span class="pi-fnote">{html.escape(case.note)}</span>' if case.note else ""
    return (
        f'<div class="pi-folder pi-folder--{kind}" style="--rot:{tilt}deg">'
        '<span class="pi-fbody"></span>'
        '<div class="pi-peek">'
        f'<div class="pi-peek-claim">&ldquo;{html.escape(case.claim)}&rdquo;</div>'
        f'<div class="pi-peek-src">{html.escape(source_tag(case))}</div>'
        "</div>"
        '<span class="pi-ftab"></span>'
        '<div class="pi-flap">'
        f'<div class="pi-flap-row"><span class="pi-fno">Case file N&ordm; {number:02d}</span>{badge}</div>'
        f'<div class="pi-ftitle">{html.escape(case.title)}{unchecked}</div>'
        f'<div class="pi-fmeta"><span>Trap {trap_dots(case.trap)}</span>{reward}</div>'
        f"{stamp}"
        '<span class="pi-stud"></span>'
        f"{note}"
        "</div></div>"
    )


def own_folder() -> str:
    """Case file Nº 0: bring your own rumour. The design's fifth, darker folder."""
    return (
        f'<div class="pi-folder pi-folder--own" style="--rot:{OWN_TILT}deg">'
        '<span class="pi-fbody"></span>'
        '<div class="pi-peek">'
        '<div class="pi-peek-claim pi-peek-claim--own">write your own rumour here .........</div>'
        f'<div class="pi-peek-src">Most end &ldquo;can&rsquo;t tell&rdquo; &middot; '
        f"calling it = +{CANT_TELL_POINTS}</div>"
        "</div>"
        '<span class="pi-ftab"></span>'
        '<div class="pi-flap">'
        '<div class="pi-flap-row"><span class="pi-fno">Case file N&ordm; 0</span></div>'
        '<div class="pi-ftitle">Bring your own</div>'
        f'<div class="pi-fmeta"><span>Trap ????</span><span>+{CANT_TELL_POINTS} can&rsquo;t-tell</span></div>'
        '<span class="pi-stud"></span>'
        "</div></div>"
    )


def footer(offline_note: str | None) -> str:
    """The two standing facts along the bottom of the archive, and — when the app is
    replaying a recording — the line that says so. Both facts are checkable: the first is
    what `tests/test_no_sql_in_app_code.py` enforces, the second is what having no account
    store means."""
    middle = f"<span>{html.escape(offline_note)}</span>" if offline_note else ""
    return (
        '<div class="pi-foot">'
        "<span>Every query is written by Genie &mdash; this app ships zero SQL</span>"
        f"{middle}"
        "<span>No accounts &middot; the session dies with the tab</span>"
        "</div>"
    )


def archive_script() -> str:
    """The one thing CSS cannot do: play the design's open-folder flight on the click.

    Clicking a folder starts a rerun that replaces the whole page, and the design's
    `openFolder` flies the folder up and out (`translateY(-140px) scale(1.5)`, fading) while
    the archive fades to scale 1.05 underneath. This reaches up into the parent document,
    the way `bring_into_view` does, and wires one delegated listener; the classes it adds
    are styled below and are simply gone when the next screen arrives.
    """
    return (
        "<script>(function () {"
        "  var d = window.parent.document;"
        "  if (d.__piArchiveWired) return;"
        "  d.__piArchiveWired = true;"
        "  d.addEventListener('click', function (e) {"
        "    var b = e.target.closest('[class*=\"st-key-case-\"] button');"
        "    if (!b) return;"
        "    var col = b.closest('[data-testid=\"stColumn\"]');"
        "    if (col) col.classList.add('is-opening');"
        "    var main = d.querySelector('.stMainBlockContainer');"
        "    if (main) main.classList.add('is-leaving');"
        "  }, true);"
        "})();</script>"
    )


ARCHIVE_CSS = """
<style>
/* The scene is the viewport: header at the top, the desk's folders at the bottom, the
   hero between. `min-height:100vh` with the folder row pushed down by `margin-top:auto`
   is the design's own `#er-root { height:100vh }` + `margin-top:auto` on the drawer. */
.stMainBlockContainer:has(.pi-archive) > [data-testid="stVerticalBlock"] {
  min-height:100vh; display:flex; flex-direction:column; }
.pi-archive { display:none; }

/* --- the header row ---------------------------------------------------------------- */
.pi-hdr { position:relative; z-index:1; display:flex; align-items:center;
  justify-content:space-between; gap:12px; flex-wrap:wrap;
  padding:clamp(14px,2.4vh,26px) clamp(14px,2.6vw,36px) 0; }
.pi-plate { font-family:var(--f-mono) !important; font-weight:400 !important;
  font-size:11px !important; letter-spacing:.2em; text-transform:uppercase;
  color:var(--gold) !important; margin:0 !important; padding:8px 14px !important;
  line-height:1.4; white-space:nowrap; display:inline-block;
  border:1px solid rgba(201,179,126,.5); border-radius:2px;
  background:linear-gradient(180deg, rgba(201,179,126,.14), rgba(201,179,126,.04)); }
.pi-hdr-r { display:flex; align-items:center; gap:12px; flex-wrap:wrap;
  font-family:var(--f-mono); }
.pi-hdr-k { font-size:12px; letter-spacing:.1em; color:var(--ash); white-space:nowrap; }
.pi-hdr-k b { color:var(--gold); }
.pi-hdr-rank { font-size:11px; letter-spacing:.12em; border:1px solid var(--gold);
  color:var(--gold); border-radius:2px; padding:4px 10px; white-space:nowrap; }
/* The GitHub mark, the design's own. */
.pi-mast-src { display:inline-flex; align-items:center; color:var(--ash);
  text-decoration:none; padding:3px; border-radius:3px; }
.pi-mast-src:hover { color:var(--bone); }
.pi-mast-src:focus-visible { outline:2px solid var(--gold); outline-offset:2px; }

/* --- the opening ------------------------------------------------------------------- */
.pi-hero { position:relative; z-index:1; text-align:center;
  padding:clamp(48px,11vh,124px) 16px 0; }
.pi-hero-where { font-family:var(--f-type); font-size:clamp(12px,1.4vw,15px);
  letter-spacing:.5em; text-transform:uppercase; color:var(--gold); opacity:.85; }
.pi-hero-line { font-family:var(--f-display) !important; font-size:clamp(30px,4.6vw,54px) !important;
  font-weight:700 !important; letter-spacing:-.01em; line-height:1.15; color:var(--bone) !important;
  margin:12px 0 0 !important; padding:0 !important; text-align:center !important;
  text-shadow:0 4px 30px rgba(0,0,0,.6); text-wrap:balance; }
.pi-hero-sub { font-family:var(--f-display); font-size:clamp(17px,2vw,22px); font-style:italic;
  color:var(--mist); margin-top:8px; text-wrap:balance; }
.pi-hero-rule { font-family:var(--f-mono); font-size:clamp(10.5px,1.2vw,12px);
  letter-spacing:.14em; text-transform:uppercase; color:var(--ash); margin-top:16px;
  line-height:1.8; }

/* --- the drawer -------------------------------------------------------------------- */
/* The design's folder row, wrapping: `display:flex; flex-wrap:wrap; justify-content:center;
   align-items:flex-end`. Streamlit columns do not wrap on their own — asked for six they
   give six slivers at any width — so the row is made to. */
[data-testid="stHorizontalBlock"]:has(.pi-folder) {
  position:relative; z-index:1; flex-wrap:wrap !important; justify-content:center;
  align-items:flex-end;
  /* Row gap larger than the column gap: a folder's tab sticks up 16px and its tilt adds a
     few more at the corners, so wrapped rows need more vertical clearance than horizontal
     or the lower row's tab pokes into the folder above — visible on a tablet, where the
     five folders wrap to two or three rows. */
  gap:46px clamp(16px,2.2vw,30px) !important;
  padding:clamp(40px,6vh,70px) 12px clamp(20px,5vh,54px); }
/* The push to the bottom goes on the wrapper Streamlit puts around the row, because that
   wrapper — not the row — is the flex child of the scene. On the row it did nothing, and
   the drawer sat under the hero with a hundred pixels of bare desk beneath it. */
[data-testid="stLayoutWrapper"]:has(.pi-folder) { margin-top:auto; }
[data-testid="stHorizontalBlock"]:has(.pi-folder) > [data-testid="stColumn"] {
  flex:0 0 auto !important; width:auto !important; min-width:0 !important;
  position:relative; padding-top:16px; }
[data-testid="stHorizontalBlock"]:has(.pi-folder) [data-testid="stVerticalBlock"] { gap:0; }

/* A folder: body, sheet, tab, flap. The design's sizes to the pixel. */
.pi-folder { position:relative; width:238px; height:170px; cursor:pointer;
  transform:rotate(var(--rot)); transition:transform .38s cubic-bezier(.2,.9,.3,1.2),
  filter .38s ease, opacity .45s ease; }
.pi-folder--next { width:252px; height:178px; }
.pi-folder--own { width:224px; height:162px; }
.pi-fbody { position:absolute; inset:0; border-radius:0 4px 4px 4px;
  background:linear-gradient(180deg, var(--folder-body), var(--folder-body-deep));
  box-shadow:inset 0 6px 14px rgba(0,0,0,.3); }
.pi-folder--next .pi-fbody { background:linear-gradient(180deg, var(--folder-next-body), var(--folder-next-body-deep)); }
.pi-folder--own .pi-fbody { background:linear-gradient(180deg, var(--folder-own-body), var(--folder-own-body-deep)); }
.pi-peek { position:absolute; left:12px; right:12px; top:-4px; height:140px; z-index:2;
  background:var(--cream); border:1px solid var(--rule-soft); border-radius:2px;
  padding:12px 14px; box-sizing:border-box; box-shadow:0 -4px 14px rgba(0,0,0,.25);
  transform:translateY(26px); transition:transform .38s ease; overflow:hidden; }
.pi-folder--next .pi-peek { top:-10px; height:158px; transform:translateY(28px); }
.pi-folder--own .pi-peek { height:138px; }
.pi-peek-claim { font-family:var(--f-type); font-size:14px; line-height:1.55; color:var(--ink-type); }
.pi-peek-claim--own { font-size:13.5px; color:var(--pencil-warm); }
.pi-peek-src { font-family:var(--f-mono); font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--pencil-warm); margin-top:6px; }
.pi-ftab { position:absolute; left:0; top:-16px; width:112px; height:24px; z-index:1;
  background:var(--folder-tab); border-radius:5px 5px 0 0; }
.pi-folder--next .pi-ftab { width:118px; background:var(--folder-next-tab); }
.pi-folder--own .pi-ftab { width:104px; background:var(--folder-own-tab); }
.pi-flap { position:absolute; inset:0; z-index:3; padding:16px 18px; box-sizing:border-box;
  background:linear-gradient(180deg, var(--folder), var(--folder-deep));
  border-radius:0 4px 4px 4px; box-shadow:0 12px 26px rgba(0,0,0,.5);
  transform-origin:bottom center; transition:transform .38s ease; }
.pi-folder--next .pi-flap { background:linear-gradient(180deg, var(--folder-next), var(--folder-next-deep));
  box-shadow:0 14px 30px rgba(0,0,0,.55), 0 0 0 1px rgba(232,180,90,.35); }
.pi-folder--own .pi-flap { background:linear-gradient(180deg, var(--folder-own), var(--folder-own-deep)); }
.pi-flap-row { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.pi-fno { font-family:var(--f-mono); font-size:11px; letter-spacing:.18em;
  text-transform:uppercase; color:var(--kraft-ink); white-space:nowrap; }
.pi-folder--own .pi-fno, .pi-folder--own .pi-fmeta { color:var(--folder-own-label); }
.pi-fnext { font-family:var(--f-mono); font-size:9.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--bone); background:var(--red); border-radius:2px;
  padding:3px 7px; white-space:nowrap; }
.pi-ftitle { font-family:var(--f-display); font-size:19px; font-weight:700; line-height:1.2;
  color:var(--ink-brown); margin-top:6px; }
.pi-folder--next .pi-ftitle { font-size:20px; }
.pi-folder--own .pi-ftitle { color:var(--folder-own-ink); }
.pi-fmeta { display:flex; gap:10px; margin-top:8px; flex-wrap:wrap; font-family:var(--f-mono);
  font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--kraft-ink); }
.pi-fstamp { position:absolute; right:12px; bottom:12px; font-family:var(--f-mono);
  font-weight:700; font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--red); border:2px solid var(--red); border-radius:3px; padding:3px 8px;
  transform:rotate(8deg); opacity:.85; white-space:nowrap; }
.pi-stud { position:absolute; left:16px; bottom:14px; width:16px; height:16px;
  border-radius:50%; border:2px solid var(--stud-rim);
  background:radial-gradient(circle at 35% 35%, var(--stud), var(--folder-body)); }
.pi-folder--own .pi-stud { border-color:var(--stud-own-rim);
  background:radial-gradient(circle at 35% 35%, var(--stud-own), var(--kraft-blocks)); }
.pi-fnote { position:absolute; right:14px; bottom:12px; font-family:var(--f-hand);
  font-size:16px; color:var(--red-hand); transform:rotate(-3deg); }

/* The click target is the folder itself, as in the design: the real button lies over the
   folder, invisible but present — a screen reader reads "Open case 3 — The paradox" and a
   keyboard tabs to it, and the folder answers the focus the way it answers a pointer. */
[data-testid="stColumn"]:has(.pi-folder) [class*="st-key-case-"] {
  position:absolute; inset:0; z-index:5; margin:0 !important; }
[data-testid="stColumn"]:has(.pi-folder) [class*="st-key-case-"] .stButton,
[data-testid="stColumn"]:has(.pi-folder) [class*="st-key-case-"] .stButton > button {
  width:100%; height:100%; margin:0; }
[data-testid="stColumn"]:has(.pi-folder) [class*="st-key-case-"] .stButton > button {
  opacity:0; cursor:pointer; border:0; background:transparent; }
[data-testid="stColumn"]:has(.pi-folder):has(button:focus-visible) .pi-folder {
  outline:3px solid var(--gold-lit); outline-offset:6px; border-radius:4px; }

/* Reaching for a folder — the design's `folderIn`, value for value: the folder lifts and
   grows, the flap squashes down on its hinge, the sheet slides up. */
[data-testid="stColumn"]:has(.pi-folder):hover .pi-folder,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-folder {
  transform:translateY(-22px) scale(1.05); filter:drop-shadow(0 26px 30px rgba(0,0,0,.55)); }
[data-testid="stColumn"]:has(.pi-folder):hover .pi-flap,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-flap {
  transform:rotateX(0deg) translateY(10px) scaleY(.82); }
[data-testid="stColumn"]:has(.pi-folder):hover .pi-peek,
[data-testid="stColumn"]:has(.pi-folder):focus-within .pi-peek {
  transform:translateY(-52px); }
/* Opening one — the design's `openFolder`: up and out, while the archive falls away. */
[data-testid="stColumn"].is-opening .pi-folder {
  transform:translateY(-140px) scale(1.5) !important; opacity:0; }
/* Scoped to the archive: Streamlit keeps the container node across reruns, so the class
   the click added is still there when the board arrives — and without the scope the board
   rendered at opacity 0, a whole scene invisible. `bring_into_view` strips it as well. */
.stMainBlockContainer.is-leaving:has(.pi-archive) > [data-testid="stVerticalBlock"] {
  opacity:0; transform:scale(1.05); transition:opacity .55s ease, transform .55s ease; }

/* Case Nº 0, opened: the rumour is written on a sheet pulled from the folder. */
.stMainBlockContainer:has(.pi-archive) [data-testid="stForm"] {
  width:min(560px, calc(100% - 24px)); margin:0 auto 10px; background:var(--cream);
  border:1px solid var(--rule-soft); border-radius:2px; padding:16px 18px;
  box-shadow:0 10px 26px rgba(0,0,0,.45); transform:rotate(-.6deg); }
.stMainBlockContainer:has(.pi-archive) [data-testid="stForm"] .stFormSubmitButton > button {
  margin-top:10px; }
.pi-own-note { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--ash); text-align:center; margin:0 0 6px; line-height:1.8; }

/* --- the standing facts ------------------------------------------------------------ */
.pi-foot { position:relative; z-index:1; display:flex; justify-content:space-between;
  gap:8px 22px; flex-wrap:wrap; padding:0 clamp(14px,2.6vw,36px) 18px;
  font-family:var(--f-mono); font-size:10.5px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--ash); line-height:1.7; }
/* Where the docket came from, folded under the desk. */
.stMainBlockContainer:has(.pi-archive) [data-testid="stExpander"] {
  margin:0 clamp(14px,2.6vw,36px) 24px; }
</style>
"""
