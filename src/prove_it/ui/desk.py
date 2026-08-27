"""The desk under the board, and the bar above it.

The design's second scene is a header row, the board, and then the desk: a slate at the
left saying what is on it tonight, the phase's panel in the middle — the wager, the review,
the retrial, the closed case — and the detective's tools at the right. The panels hold the
controls, and controls have to be Streamlit widgets to reach Python, so what this module
owns is everything around them: the markup for the slate, the bar and the props, and the
CSS that dresses the widgets as the design's slips, coins, wax seal and buttons.
"""

from __future__ import annotations

import html

from prove_it.domain.game import CASE_CLOSED_POINTS, OVERTURNED_POINTS, Rank
from prove_it.ui.render import source_link

PHASE_LABELS = {
    "wager": "Read the warrant · wager",
    "revealed": "Seal broken · review",
    "retrial": "Retrial · verdict flipped",
    "retrial-stood": "Retrial · verdict stood",
    "closed": "Case closed",
}


def case_bar(
    *, number: int, title: str, claim: str, points: int, rank: Rank, promoted: bool, source_url: str
) -> str:
    """The row across the top of the board scene, right of the ← THE ARCHIVE button."""
    label = (
        f"Case N&ordm; {number:02d} &middot; {html.escape(title)}" if number else "Case N&ordm; 0"
    )
    plate = (
        f'<span class="pi-hdr-rank is-promoted">{html.escape(rank.title.upper())} &#9733;'
        '<span class="shine" aria-hidden="true"></span></span>'
        if promoted
        else f'<span class="pi-hdr-rank">{html.escape(rank.title.upper())}</span>'
    )
    return (
        '<div class="pi-cbar">'
        f'<span class="pi-cbar-case">{label}</span>'
        f'<span class="pi-cbar-claim">&ldquo;{html.escape(claim)}&rdquo;</span>'
        '<span class="pi-cbar-r">'
        f'<span class="pi-hdr-k">PTS <b>{points}</b></span>{plate}{source_link(source_url)}'
        "</span></div>"
    )


def slate(*, number: int, title: str, phase: str, gain: int) -> str:
    """ON THE DESK TONIGHT: the case, the phase, and what it has paid so far."""
    name = (
        f"Case N&ordm; {number:02d} &mdash; {html.escape(title)}" if number else html.escape(title)
    )
    return (
        '<div class="pi-slate">'
        '<div class="k">On the desk tonight</div>'
        f'<div class="t">{name}</div>'
        f'<div class="k rows">Now: <b>{html.escape(PHASE_LABELS[phase])}</b><br>'
        f"Winnings this case: <b>+{gain}</b></div>"
        '<div class="hand">read the warrant, then wager.</div>'
        "</div>"
    )


def props() -> str:
    """The tools of the trade: a magnifier, an ink pad and a hand stamp, lying at the right
    of the desk. Pure scenery, hidden from assistive technology and from narrow screens."""
    return (
        '<div class="pi-props" aria-hidden="true">'
        '<span class="glow"></span><span class="shadow"></span>'
        '<div class="mag"><span class="lens"></span><span class="rim"></span>'
        '<span class="hl a"></span><span class="hl b"></span>'
        '<span class="collar"></span><span class="handle"></span><span class="cap"></span></div>'
        '<div class="pad"><span class="base"></span><span class="ink"></span></div>'
        '<div class="stamp"><span class="knob"></span><span class="stem"></span>'
        '<span class="foot"></span><span class="rubber"></span></div>'
        '<span class="hand">tools of the trade</span>'
        "</div>"
    )


def wager_head(question: str) -> str:
    return (
        '<div class="pi-wager-head"><span class="pi-wager-title">The wager</span>'
        f'<span class="pi-wager-q">{question}</span></div>'
    )


def seal_hint(*, picked: bool, staked: bool) -> str:
    if picked and staked:
        return "Your call is on record &mdash; open it"
    if picked:
        return "Now stake it"
    if staked:
        return "Now make the call"
    return "Pick a slip and a stake first"


def under(text: str) -> str:
    """The small mono line under a control: +250 IF THE VERDICT FLIPS, CASE CLOSED +150."""
    return f'<div class="pi-under">{text}</div>'


FLIP_LINE = f"+{OVERTURNED_POINTS} if the verdict flips"
CLOSE_LINE = f"Case closed +{CASE_CLOSED_POINTS}"


DESK_CSS = """
<style>
/* --- the bar above the board ------------------------------------------------------- */
.stMainBlockContainer:has(.pi-cbar) { background:linear-gradient(180deg, var(--board-night) 0%,
  var(--cabinet-deep) 50%, var(--room) 100%); min-height:100vh; }
[data-testid="stHorizontalBlock"]:has(.pi-cbar) { align-items:center; gap:10px 16px !important;
  padding:12px clamp(12px,2.2vw,30px); min-height:58px; flex-wrap:wrap !important; }
[data-testid="stHorizontalBlock"]:has(.pi-cbar) > [data-testid="stColumn"]:first-child {
  flex:0 0 auto !important; width:auto !important; min-width:0 !important; }
[data-testid="stHorizontalBlock"]:has(.pi-cbar) > [data-testid="stColumn"]:last-child {
  flex:1 1 320px !important; width:auto !important; min-width:0 !important; }
[class*="st-key-start-over"] .stButton > button { font-size:11px; letter-spacing:.14em;
  color:var(--mist); border:1px solid rgba(155,163,173,.5); padding:6px 12px; min-height:32px;
  white-space:nowrap; }
[class*="st-key-start-over"] .stButton > button:hover { color:var(--bone); border-color:var(--bone);
  background:transparent; }
.pi-cbar { display:flex; align-items:center; gap:10px 16px; flex-wrap:wrap; min-width:0; }
.pi-cbar-case { font-family:var(--f-mono); font-size:11px; letter-spacing:.18em;
  text-transform:uppercase; color:var(--gold); white-space:nowrap; }
.pi-cbar-claim { flex:1 1 120px; min-width:0; font-family:var(--f-display); font-size:15px;
  font-style:italic; color:var(--mist); white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; }
.pi-cbar-r { display:flex; align-items:center; gap:12px; flex-wrap:wrap; font-family:var(--f-mono); }
.pi-hdr-rank.is-promoted { position:relative; overflow:hidden; border:1.5px solid var(--gold);
  color:var(--chrome); background:var(--gold); font-weight:700; }
.pi-hdr-rank .shine { position:absolute; top:0; bottom:0; left:0; width:60px;
  background:linear-gradient(90deg, transparent, rgba(255,253,246,.75), transparent);
  animation:pi-shine 1.3s ease-out .4s backwards; }
@keyframes pi-shine { 0% { transform:translateX(-130%) skewX(-18deg); }
                      100% { transform:translateX(340%) skewX(-18deg); } }

/* The board's frame: the iframe carries the frame, so its container only sets the gutter. */
.stElementContainer:has(iframe[srcdoc*="er-board"]) { margin:0 clamp(10px,1.9vw,26px); }
.stElementContainer:has(iframe[srcdoc*="er-board"]) iframe { display:block; width:100%; }

/* --- the desk ---------------------------------------------------------------------- */
[class*="st-key-desk"] { position:relative; min-height:330px; margin-top:10px;
  padding:18px 12px 22px; }
[class*="st-key-desk"]::before { content:""; position:absolute; inset:0; pointer-events:none;
  background:
    linear-gradient(180deg, rgba(255,230,180,.28), transparent 6px),
    repeating-linear-gradient(93deg, rgba(0,0,0,.14) 0 2px, transparent 2px 30px,
      rgba(255,240,200,.02) 30px 31px, transparent 31px 100px),
    linear-gradient(180deg, var(--desk-top) 0%, var(--desk-mid) 40%, var(--desk-deep) 100%); }
[class*="st-key-desk"] > [data-testid="stHorizontalBlock"] { position:relative; align-items:center;
  flex-wrap:wrap !important; gap:14px 18px !important; min-height:290px; }
[class*="st-key-desk"] [data-testid="stColumn"]:has(.pi-slate) { flex:0 0 250px !important;
  width:250px !important; min-width:0 !important; align-self:flex-end; }
[class*="st-key-desk"] [data-testid="stColumn"]:has(.pi-props) { flex:0 0 330px !important;
  width:330px !important; min-width:0 !important; align-self:flex-end; }
[class*="st-key-desk"] [data-testid="stColumn"]:not(:has(.pi-slate)):not(:has(.pi-props)) {
  flex:1 1 420px !important; width:auto !important; min-width:0 !important;
  max-width:820px; margin:0 auto; }

/* The slate. */
.pi-slate { background:var(--kraft); border:1px solid var(--kraft-line); border-radius:3px;
  padding:14px 16px; box-shadow:0 10px 24px rgba(0,0,0,.45); transform:rotate(-1.2deg);
  margin-bottom:8px; }
.pi-slate .k { font-family:var(--f-mono); font-size:10px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--kraft-ink-soft); }
.pi-slate .t { font-family:var(--f-display); font-size:18px; font-weight:700;
  color:var(--ink-warm); margin-top:5px; line-height:1.3; }
.pi-slate .rows { letter-spacing:.08em; margin-top:8px; line-height:1.9; }
.pi-slate .rows b { color:var(--ink-warm); }
.pi-slate .hand { font-family:var(--f-hand); font-size:17px; color:var(--red-hand);
  margin-top:6px; transform:rotate(-2deg); display:inline-block; }

/* The tools of the trade. */
.pi-props { position:relative; width:330px; height:220px; margin-left:auto; }
.pi-props > *, .pi-props .mag > *, .pi-props .pad > *, .pi-props .stamp > * { position:absolute; display:block; }
.pi-props .glow { left:-30px; bottom:-10px; width:380px; height:130px; filter:blur(8px);
  background:radial-gradient(ellipse 52% 55% at 50% 45%, rgba(255,222,150,.16), transparent 72%); }
.pi-props .shadow { left:16px; bottom:2px; width:190px; height:36px; border-radius:50%; filter:blur(5px);
  background:radial-gradient(ellipse at 50% 50%, rgba(0,0,0,.5), transparent 70%); }
.pi-props .mag { left:10px; bottom:-18px; width:128px; height:244px; transform:rotate(-46deg);
  transform-origin:64px 64px; }
.pi-props .lens { left:0; top:0; width:128px; height:128px; border-radius:50%; border:11px solid var(--brass);
  background:radial-gradient(circle at 32% 28%, rgba(255,255,255,.34), rgba(226,238,232,.14) 42%,
    rgba(180,200,190,.08) 65%, rgba(120,140,130,.12));
  box-shadow:0 6px 16px rgba(0,0,0,.45), inset 0 3px 10px rgba(255,255,255,.25), inset 0 -4px 12px rgba(30,40,35,.3); }
.pi-props .rim { left:0; top:0; width:128px; height:128px; border-radius:50%; border:11px solid transparent;
  border-top-color:rgba(255,246,214,.65); border-left-color:rgba(255,246,214,.3); transform:rotate(-12deg); }
.pi-props .hl { border-radius:50%; filter:blur(2px); transform:rotate(-22deg);
  background:linear-gradient(120deg, rgba(255,255,255,.55), transparent 75%); }
.pi-props .hl.a { left:30px; top:22px; width:48px; height:17px; }
.pi-props .hl.b { left:72px; top:78px; width:26px; height:9px;
  background:linear-gradient(120deg, rgba(255,255,255,.3), transparent 75%); }
.pi-props .collar { left:50%; top:122px; transform:translateX(-50%); width:28px; height:22px;
  border-radius:4px 4px 6px 6px; box-shadow:0 2px 4px rgba(0,0,0,.35);
  background:linear-gradient(90deg, var(--brass-deep), var(--brass-lit) 45%, var(--brass-mid)); }
.pi-props .handle { left:50%; top:140px; transform:translateX(-50%); width:17px; height:96px; border-radius:8px;
  box-shadow:0 3px 7px rgba(0,0,0,.45);
  background:linear-gradient(90deg, var(--handle), var(--handle-lit) 40%, var(--handle-mid) 70%, var(--handle-deep)); }
.pi-props .cap { left:50%; top:228px; transform:translateX(-50%); width:19px; height:10px; border-radius:5px;
  background:linear-gradient(90deg, var(--brass-deep), var(--handle-cap), var(--brass-deep)); }
.pi-props .pad { right:14px; bottom:12px; width:104px; height:58px; }
.pi-props .pad .base { left:0; bottom:0; width:104px; height:34px; border-radius:6px;
  background:linear-gradient(180deg, var(--fixture), var(--shade-deep) 70%);
  box-shadow:0 5px 12px rgba(0,0,0,.5), inset 0 2px 3px rgba(255,255,255,.12); }
.pi-props .pad .ink { left:8px; bottom:8px; width:88px; height:18px; border-radius:3px;
  background:linear-gradient(180deg, var(--pad-ink), var(--pad-ink-deep)); box-shadow:inset 0 2px 5px rgba(0,0,0,.45); }
.pi-props .stamp { right:44px; bottom:44px; width:56px; height:80px; }
.pi-props .stamp .knob { left:50%; top:0; transform:translateX(-50%); width:24px; height:26px;
  border-radius:50% 50% 8px 8px; box-shadow:0 2px 4px rgba(0,0,0,.4);
  background:linear-gradient(135deg, var(--stamp-knob), var(--handle-lit) 70%); }
.pi-props .stamp .stem { left:50%; top:22px; transform:translateX(-50%); width:11px; height:32px;
  background:linear-gradient(90deg, var(--handle-mid), var(--stamp-knob) 45%, var(--handle-lit)); }
.pi-props .stamp .foot { left:0; top:50px; width:56px; height:26px; border-radius:5px 5px 3px 3px;
  box-shadow:0 4px 9px rgba(0,0,0,.5);
  background:linear-gradient(180deg, var(--stamp-base), var(--stamp-base-mid) 60%, var(--stamp-base-deep)); }
.pi-props .stamp .rubber { left:3px; top:74px; width:50px; height:7px; border-radius:2px;
  background:linear-gradient(180deg, var(--wax), var(--wax-deep)); }
.pi-props .hand { right:18px; bottom:112px; font-family:var(--f-hand); font-size:17px;
  color:rgba(240,235,221,.5); transform:rotate(-4deg); }

/* --- the phase panel --------------------------------------------------------------- */
[class*="st-key-panel-"] { position:relative; background:rgba(20,16,10,.55);
  border:1px solid rgba(201,179,126,.35); border-radius:6px; padding:18px clamp(14px,2vw,22px);
  width:100%; }
[class*="st-key-panel-"] [data-testid="stHorizontalBlock"] { gap:14px 18px !important;
  align-items:center; flex-wrap:wrap !important; }
[class*="st-key-panel-"] [data-testid="stVerticalBlock"] { gap:7px !important; }
.pi-wager-head { display:flex; justify-content:space-between; align-items:baseline; gap:8px 16px;
  flex-wrap:wrap; margin-bottom:8px; }
.pi-wager-title { font-family:var(--f-type); font-size:15px; letter-spacing:.16em;
  text-transform:uppercase; color:var(--gold-pale); }
.pi-wager-q { font-family:var(--f-mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--mist); }
.pi-wager-q b { color:var(--gold-lit); }
/* The slips: paper, a radio dot, typed. The chosen one gets the red ring. */
[class*="st-key-slip-"] .stButton > button { width:100%; position:relative; text-align:left;
  background:var(--cream); color:var(--ink-warm); border:0; border-radius:2px;
  font-family:var(--f-type) !important; font-size:13px; letter-spacing:0; text-transform:none;
  font-weight:400; padding:10px 12px 10px 34px; box-shadow:0 4px 10px rgba(0,0,0,.4);
  transform:rotate(-.6deg); min-height:44px; justify-content:flex-start; }
[class*="st-key-slip-"]:nth-of-type(even) .stButton > button { transform:rotate(.4deg); }
[class*="st-key-slip-"] .stButton > button::before { content:""; position:absolute; left:11px; top:50%;
  margin-top:-6px; width:12px; height:12px; border:2px solid var(--pencil-warm); border-radius:50%; }
[class*="st-key-slip-"] .stButton > button:hover { background:var(--cream); color:var(--ink-warm);
  transform:translateY(-1px) rotate(-.6deg); }
[class*="st-key-slip-"][class*="-on"] .stButton > button {
  box-shadow:0 0 0 2.5px var(--red), 0 4px 10px rgba(0,0,0,.4) !important; }
[class*="st-key-slip-"][class*="-on"] .stButton > button::after { content:""; position:absolute; left:14px;
  top:50%; margin-top:-3px; width:6px; height:6px; border-radius:50%; background:var(--red); }
/* The stake: three coins. */
.pi-stake-label { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--gold); text-align:center; }
.pi-stake-note { font-family:var(--f-mono); font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ash); text-align:center; max-width:260px; line-height:1.7; margin:4px auto 0; }
[class*="st-key-coins"] [data-testid="stHorizontalBlock"] { gap:10px !important; justify-content:center;
  flex-wrap:nowrap !important; }
[class*="st-key-coins"] [data-testid="stColumn"] { flex:0 0 auto !important; width:auto !important;
  min-width:0 !important; }
[class*="st-key-coin-"] .stButton > button { width:68px; height:68px; min-height:68px; border-radius:50%;
  padding:0; border:2.5px solid var(--gold); color:var(--gold-pale);
  background:radial-gradient(circle at 40% 32%, rgba(201,179,126,.28), rgba(201,179,126,.08));
  font-size:9.5px; letter-spacing:.06em; line-height:1.35; white-space:normal; }
[class*="st-key-coin-"] .stButton > button p { margin:0; }
[class*="st-key-coin-"] .stButton > button strong { display:block; font-size:16px; font-weight:700; }
[class*="st-key-coin-HUNCH"] .stButton > button { transform:rotate(-4deg); }
[class*="st-key-coin-FAIRLY"] .stButton > button { transform:rotate(2deg); font-size:9px; letter-spacing:.04em; }
[class*="st-key-coin-CERTAIN"] .stButton > button { transform:rotate(6deg); border-color:var(--certain);
  color:var(--certain-ink); background:radial-gradient(circle at 40% 32%, rgba(212,106,94,.3), rgba(212,106,94,.08)); }
[class*="st-key-coin-"] .stButton > button:hover { color:inherit; background:radial-gradient(circle at 40% 32%,
  rgba(201,179,126,.4), rgba(201,179,126,.14)); }
[class*="st-key-coin-"][class*="-on"] .stButton > button { box-shadow:0 0 0 6px transparent,
  0 0 0 8.5px var(--gold-lit) !important; }
[class*="st-key-coin-CERTAIN"][class*="-on"] .stButton > button { box-shadow:0 0 0 6px transparent,
  0 0 0 8.5px var(--pin-red) !important; }
/* The wax seal. */
[class*="st-key-seal"] .stButton > button { width:104px; height:104px; min-height:104px; border-radius:50%;
  margin:0 auto; display:flex; padding:0; border:0; color:var(--wax-ink);
  font-family:var(--f-type) !important; font-size:12px; letter-spacing:.12em; line-height:1.6;
  white-space:normal; text-align:center;
  background:radial-gradient(circle at 38% 30%, var(--red-lit), var(--wax) 62%, var(--wax-deep));
  box-shadow:0 8px 22px rgba(0,0,0,.55), inset 0 2px 6px rgba(255,200,180,.35), inset 0 -6px 12px rgba(0,0,0,.4);
  transition:opacity .3s ease, transform .18s ease; }
[class*="st-key-seal"] .stButton > button:hover { transform:scale(1.05); color:var(--wax-ink);
  background:radial-gradient(circle at 38% 30%, var(--red-lit), var(--wax) 62%, var(--wax-deep)); }
[class*="st-key-seal"] .stButton > button:active { transform:scale(.94); }
[class*="st-key-seal"] .stButton > button:disabled { opacity:.42; }
[class*="st-key-seal"] .stButton { display:flex; justify-content:center; }
.pi-seal-hint { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--mist); text-align:center; width:170px; line-height:1.7; margin:8px auto 0; }
.pi-under { font-family:var(--f-mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--mist); text-align:center; margin-top:6px; }
/* The estimate ruler, when the case asks for one, sits with the slips. */
[class*="st-key-panel-"] .pi-vlabel { margin:10px 0 4px; font-size:10px; color:var(--gold); }
/* The review: the question, the doubt, and the cross-examination. */
.pi-review-q { font-family:var(--f-display); font-size:19px; font-style:italic; color:var(--bone); margin-top:10px; }
.pi-review-t { font-size:15px; line-height:1.6; color:var(--mist); margin-top:6px; }
.pi-review-t strong { color:var(--bone); }
[class*="st-key-panel-"] .stFormSubmitButton > button { width:100%; border:0; color:var(--wax-ink);
  background:linear-gradient(180deg, var(--red-lit), var(--wax)); box-shadow:0 6px 18px rgba(0,0,0,.5);
  font-weight:500; padding:15px 20px; }
[class*="st-key-panel-"] .stFormSubmitButton > button:hover { transform:translateY(-2px); color:var(--wax-ink);
  background:linear-gradient(180deg, var(--red-lit), var(--wax)); }
[class*="st-key-panel-"] [data-testid="stForm"] { border:0; padding:0; }
/* The retrial and the closed case. */
.pi-retrial-line { font-family:var(--f-display); font-size:19px; font-weight:600; color:var(--bone);
  margin-top:10px; line-height:1.45; }
.pi-retrial-sub { font-size:15px; line-height:1.6; color:var(--mist); margin-top:6px; }
.pi-closed-line { font-family:var(--f-display); font-size:19px; font-weight:600; color:var(--bone); }
.pi-closed-line .v { color:var(--pin-red); }
.pi-closed-line .v-holds { color:var(--green); }

/* --- what lies below the desk ------------------------------------------------------ */
[class*="st-key-below"] { padding:18px clamp(12px,2.2vw,30px) 40px; }
[class*="st-key-below"] [data-testid="stVerticalBlock"] { gap:8px !important; }
[class*="st-key-below"] iframe { display:block; }

/* --- narrow: the design's `_layout()` for the desk ---------------------------------- */
@media (max-width: 999px) {
  [class*="st-key-desk"] { padding:16px 10px 22px; }
  [class*="st-key-desk"] [data-testid="stColumn"]:has(.pi-slate) { flex:1 1 100% !important;
    width:100% !important; align-self:auto; }
  .pi-slate { width:min(420px, 100%); margin:0 auto 14px; transform:none; }
  [class*="st-key-desk"] [data-testid="stColumn"]:has(.pi-props) { display:none; }
  .pi-cbar-claim { white-space:normal; flex-basis:100%; }
}
</style>
"""
