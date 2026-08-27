"""The antibody kit: the card a closed case mints, and the one thing that leaves the room.

When a case closes the design lifts a collectible card over the board — ANTIBODY Nº 02,
the trick's name, what it does and where it turns up next — with the kit's other slots
under it, and offers to share it: a case card that can be downloaded, with a caption that
can be copied. Both overlays are markup laid over the page; the buttons under them are
Streamlit's, placed by the desk's stylesheet.

The share card is also rendered as an SVG a player can download. It carries the same
words as the card on screen and nothing else — no account, no feed, no tracking pixel; an
image you own, as the design puts it.
"""

from __future__ import annotations

import html
from textwrap import wrap

from prove_it.domain.cases import Case
from prove_it.domain.verdict import Verdict
from prove_it.ui.archive import trap_dots
from prove_it.ui.style import FONTS, PALETTE, VERDICT_TEXT, rgba


def _motif(case: Case | None) -> str:
    """What the band across the card shows. The paradox gets the design's own picture —
    every group leaning one way, the total the other. Every other trick gets its trap."""
    if case is not None and case.key == "paradox":
        ups = "".join('<span class="tri up"></span>' for _ in range(4))
        return (
            f'<div class="motif"><div class="col"><div class="tris">{ups}</div>'
            '<div class="k">Every group</div></div>'
            '<div class="col"><span class="tri down"></span><div class="k">The total</div></div></div>'
        )
    dots = trap_dots(case.trap) if case is not None else "????"
    return f'<div class="motif"><div class="col"><div class="dots">{dots}</div><div class="k">Trap</div></div></div>'


def antibody_card(
    *,
    number: int,
    case: Case | None,
    trick: str,
    lesson: str,
    wild: str,
    verdict: Verdict,
    kit: list[tuple[int, str]],
) -> str:
    """The minted card, over the board. `kit` lists every slot as (number, state), state
    one of "done", "this", "open", "own"."""
    label = f"Antibody N&ordm; {number:02d}" if number else "Antibody N&ordm; 0"
    trap = trap_dots(case.trap) if case is not None else "????"
    slots = []
    for n, state in kit:
        text = {
            "done": f"N&ordm;{n} &#10003;",
            "this": f"N&ordm;{n} &#9733;",
            "open": f"N&ordm;{n}",
            "own": f"N&ordm;{n}<br>yours",
        }[state]
        slots.append(f'<span class="slot {state}">{text}</span>')
    stamp_label, tone = VERDICT_TEXT[verdict]
    return (
        '<div class="pi-overlay pi-overlay--card" role="dialog" aria-label="Antibody card minted">'
        f'<div class="k gold">{label} minted &mdash; click the card</div>'
        '<label class="pi-acard"><input type="checkbox" class="flip" aria-label="Turn the card over">'
        '<div class="front"><div class="inner">'
        f'<div class="head"><span>{label}</span><span class="gold">Trap {trap}</span></div>'
        f'<div class="band">{_motif(case)}</div>'
        f'<div class="body"><div class="trick">{html.escape(trick)}</div>'
        f'<div class="lesson">{html.escape(lesson)}</div></div>'
        f'<div class="wild"><div class="k red">In the wild</div><div>{html.escape(wild)}</div></div>'
        f'<span class="pi-verdict {tone} corner">{html.escape(stamp_label)}</span>'
        "</div></div>"
        '<div class="back"><div class="seal"><div class="t">Prove It</div>'
        '<div class="k">Evidence kit</div></div></div>'
        "</label>"
        f'<div class="pi-kitstrip">{"".join(slots)}</div>'
        "</div>"
    )


def share_caption(*, claim: str, trick: str, verdict: Verdict) -> str:
    label = VERDICT_TEXT[verdict][0]
    return (
        f"I checked a rumour against real data. “{claim}” — {label}. The trick: {trick}. #ProveIt"
    )


def share_card(
    *,
    number: int,
    claim: str,
    trick: str,
    reason: str,
    verdict: Verdict,
    real_data: bool,
    queries: int,
    flipped: bool,
    conversation: str,
) -> str:
    stamp_label, tone = VERDICT_TEXT[verdict]
    checked = "Checked against real data" if real_data else "Checked against synthetic data"
    flip_line = "Verdict flipped on one follow-up" if flipped else "Verdict stood on the follow-up"
    case = f"Case N&ordm; {number:02d}" if number else "Case N&ordm; 0"
    return (
        '<div class="pi-overlay pi-overlay--share" role="dialog" aria-label="The case card">'
        '<div class="k gold wide">The case card &mdash; the only thing that leaves the room</div>'
        '<div class="pi-scard">'
        f'<div class="head"><span>Prove It &middot; {case}</span><span class="gold">{checked}</span></div>'
        '<div class="body">'
        f'<span class="pi-verdict {tone} corner big">{html.escape(stamp_label)}</span>'
        '<div class="k">The rumour</div>'
        f'<div class="claim">&ldquo;{html.escape(claim)}&rdquo;</div>'
        '<div class="k gap">The trick</div>'
        f'<div class="trick"><b>{html.escape(trick)}</b> &mdash; {html.escape(reason)}</div>'
        '<div class="foot">'
        f"<span>{queries} quer{'ies' if queries != 1 else 'y'} &middot; {'both' if queries == 2 else 'all'} by Genie &middot; 0 by the app</span>"
        f"<span>{flip_line}</span>"
        f"<span>Conv {html.escape(conversation)}&hellip;</span>"
        "</div></div></div>"
        '<div class="k ash">No accounts, no feed &mdash; the card is an image you own.</div>'
        "</div>"
    )


def share_svg(
    *,
    number: int,
    claim: str,
    trick: str,
    reason: str,
    verdict: Verdict,
    real_data: bool,
    queries: int,
    flipped: bool,
    conversation: str,
) -> bytes:
    """The case card as a file: the same words, drawn as SVG so it stays sharp at any size
    and carries nothing but text."""
    p = PALETTE
    serif, mono = FONTS["display"], FONTS["mono"]
    stamp_label, _ = VERDICT_TEXT[verdict]
    tone = {
        Verdict.BUSTED: p["red"],
        Verdict.HOLDS: p["green"],
        Verdict.HALF_TRUE: p["navy"],
        Verdict.CANT_TELL: p["gold-deep"],
    }[verdict]
    claim_lines = wrap(f"“{claim}”", 34)[:4]
    trick_lines = wrap(f"{trick} — {reason}", 62)[:4]
    checked = "CHECKED AGAINST REAL DATA" if real_data else "CHECKED AGAINST SYNTHETIC DATA"
    flip_line = "VERDICT FLIPPED ON ONE FOLLOW-UP" if flipped else "VERDICT STOOD ON THE FOLLOW-UP"
    case = f"CASE Nº {number:02d}" if number else "CASE Nº 0"
    y = 150
    claim_svg = "".join(
        f'<text x="40" y="{y + i * 32}" font-family="{serif}" font-size="24" font-weight="700" '
        f'font-style="italic" fill="{p["ink-warm"]}">{html.escape(line)}</text>'
        for i, line in enumerate(claim_lines)
    )
    y2 = y + len(claim_lines) * 32 + 34
    trick_svg = "".join(
        f'<text x="40" y="{y2 + 26 + i * 24}" font-family="{serif}" font-size="16" '
        f'fill="{p["ink-warm"]}">{html.escape(line)}</text>'
        for i, line in enumerate(trick_lines)
    )
    y3 = y2 + 26 + len(trick_lines) * 24 + 28
    height = y3 + 70
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="680" height="{height}" viewBox="0 0 680 {height}">
<rect width="680" height="{height}" rx="4" fill="{p["cream"]}"/>
<rect width="680" height="52" fill="{p["chrome"]}"/>
<text x="24" y="32" font-family="{mono}" font-size="11" letter-spacing="2" fill="{p["bone"]}">PROVE IT · {case}</text>
<text x="656" y="32" font-family="{mono}" font-size="11" letter-spacing="1.5" fill="{p["gold"]}" text-anchor="end">{checked}</text>
<g transform="rotate(7 590 96)"><rect x="530" y="80" width="120" height="34" rx="4" fill="none" stroke="{tone}" stroke-width="3"/>
<text x="590" y="103" font-family="{mono}" font-size="14" font-weight="700" letter-spacing="2" fill="{tone}" text-anchor="middle">{html.escape(stamp_label.upper())}</text></g>
<text x="40" y="110" font-family="{mono}" font-size="11" letter-spacing="2" fill="{p["pencil-warm"]}">THE RUMOUR</text>
{claim_svg}
<text x="40" y="{y2}" font-family="{mono}" font-size="11" letter-spacing="2" fill="{p["pencil-warm"]}">THE TRICK</text>
{trick_svg}
<line x1="40" y1="{y3}" x2="640" y2="{y3}" stroke="{p["ink-warm"]}" stroke-width="2"/>
<text x="40" y="{y3 + 26}" font-family="{mono}" font-size="10.5" letter-spacing="1" fill="{p["kraft-ink"]}">{queries} QUERIES · ALL BY GENIE · 0 BY THE APP</text>
<text x="640" y="{y3 + 26}" font-family="{mono}" font-size="10.5" letter-spacing="1" fill="{p["kraft-ink"]}" text-anchor="end">{flip_line}</text>
<text x="40" y="{y3 + 48}" font-family="{mono}" font-size="10.5" letter-spacing="1" fill="{p["kraft-ink"]}">CONV {html.escape(conversation)}…</text>
</svg>""".encode()


def copy_frame(text: str, label: str = "Copy caption") -> str:
    """A button that copies `text` to the clipboard, as an inline frame.

    A frame because the clipboard needs script and Streamlit runs none in markdown. The
    frame is transparent and holds nothing but the button, dressed as the design's
    outlined control, so it sits in the row with the other two."""
    p = PALETTE
    payload = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:transparent;}}
button {{ font-family:{FONTS["mono"]};font-size:12px;letter-spacing:.12em;text-transform:uppercase;
  color:{p["bone"]};background:transparent;border:1.5px solid {rgba("bone", 0.6)};border-radius:3px;
  padding:12px 18px;cursor:pointer;white-space:nowrap;min-height:44px;}}
button:hover{{background:{rgba("bone", 0.1)};}}
button:focus-visible{{outline:2px solid {p["gold-lit"]};outline-offset:3px;}}
</style></head><body><button type="button" id="c">{html.escape(label)}</button>
<script>(function(){{var b=document.getElementById('c'),t='{payload}';
function done(ok){{b.textContent=ok?'Copied':'Copy failed';setTimeout(function(){{b.textContent='{html.escape(label)}';}},1800);}}
b.addEventListener('click',function(){{if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).then(function(){{done(true);}},function(){{done(false);}});}}else{{done(false);}}}});
}})();</script></body></html>"""


KIT_CSS = """
<style>
/* An overlay lies over the whole room. */
.pi-overlay { position:fixed; inset:0; z-index:60; display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:16px; padding:22px 12px 120px; overflow-y:auto;
  background:radial-gradient(ellipse 60% 60% at 50% 44%, rgba(14,17,22,.62), rgba(8,10,13,.92));
  animation:pi-scrim .5s ease-out; }
.pi-overlay--share { background:rgba(8,10,13,.93); z-index:70; gap:18px; }
@keyframes pi-scrim { from { opacity:0; } to { opacity:1; } }
@keyframes pi-mint { 0% { opacity:0; transform:translateY(46px) rotate(4deg) scale(.94); }
                     100% { opacity:1; transform:translateY(0) rotate(0deg) scale(1); } }
.pi-overlay .k { font-family:var(--f-mono); font-size:11.5px; letter-spacing:.24em;
  text-transform:uppercase; text-align:center; line-height:1.8; }
.pi-overlay .k.gold { color:var(--gold); }
.pi-overlay .k.ash { color:var(--ash); font-size:10.5px; letter-spacing:.08em; max-width:92vw; }
.pi-overlay .k.wide { font-size:12px; }
/* The buttons under an overlay are Streamlit's, lifted to sit on it. */
[class*="st-key-kit-actions"], [class*="st-key-share-actions"] { position:fixed; left:50%;
  bottom:6vh; transform:translateX(-50%); z-index:71; width:auto; }
[class*="st-key-kit-actions"] [data-testid="stHorizontalBlock"],
[class*="st-key-share-actions"] [data-testid="stHorizontalBlock"] { gap:12px !important;
  justify-content:center; flex-wrap:wrap !important; }
[class*="st-key-kit-actions"] [data-testid="stColumn"],
[class*="st-key-share-actions"] [data-testid="stColumn"] { flex:0 0 auto !important;
  width:auto !important; min-width:0 !important; }
[class*="st-key-kit-actions"] .stButton > button, [class*="st-key-share-actions"] .stButton > button,
[class*="st-key-share-actions"] .stDownloadButton > button { white-space:nowrap; }
[class*="st-key-share-actions"] .stDownloadButton > button {
  font-family:var(--f-mono) !important; text-transform:uppercase; letter-spacing:.12em; font-size:12px;
  border-radius:3px; padding:12px 18px; border:0; font-weight:700; color:var(--chrome);
  background:linear-gradient(180deg, var(--gold-fill), var(--gold)); }
[class*="st-key-share-back"] .stButton > button { border:0; color:var(--mist); }
[class*="st-key-share-back"] .stButton > button:hover { color:var(--bone); background:transparent; }

/* The antibody card: front and back, turned over by its own checkbox. */
.pi-acard { position:relative; display:block; width:min(330px, 88vw); height:452px; cursor:pointer;
  animation:pi-mint .7s cubic-bezier(.2,1.1,.35,1) .2s backwards; flex-shrink:0; }
.pi-acard .flip { position:absolute; opacity:0; width:1px; height:1px; }
.pi-acard .front, .pi-acard .back { position:absolute; inset:0; border:1.5px solid var(--chrome);
  border-radius:8px; box-shadow:0 24px 60px rgba(0,0,0,.6); }
.pi-acard .front { background:var(--paper); padding:10px; display:flex; flex-direction:column; }
.pi-acard .back { display:none; align-items:center; justify-content:center;
  background:repeating-linear-gradient(45deg, var(--manila) 0 14px, var(--manila-tab) 14px 28px); }
.pi-acard .flip:checked ~ .front { display:none; }
.pi-acard .flip:checked ~ .back { display:flex; }
.pi-acard .flip:focus-visible ~ .front, .pi-acard .flip:focus-visible ~ .back {
  outline:3px solid var(--gold-lit); outline-offset:4px; }
.pi-acard .inner { position:relative; border:1px solid var(--rule); border-radius:5px; flex:1; display:flex;
  flex-direction:column; overflow:hidden; }
.pi-acard .head { background:var(--chrome); color:var(--bone); padding:11px 15px; display:flex;
  justify-content:space-between; align-items:center; gap:8px; font-family:var(--f-mono); font-size:10.5px;
  letter-spacing:.2em; text-transform:uppercase; white-space:nowrap; }
.pi-acard .head .gold { color:var(--gold); letter-spacing:.14em; }
.pi-acard .band { height:112px; background:var(--manila); display:flex; align-items:center;
  justify-content:center; flex-shrink:0; }
.pi-acard .motif { display:flex; gap:18px; align-items:center; }
.pi-acard .motif .col { display:flex; flex-direction:column; align-items:center; }
.pi-acard .tris { display:flex; gap:7px; }
.pi-acard .tri { width:0; height:0; display:block; }
.pi-acard .tri.up { border-left:8px solid transparent; border-right:8px solid transparent;
  border-bottom:14px solid var(--green); }
.pi-acard .tri.down { border-left:24px solid transparent; border-right:24px solid transparent;
  border-top:38px solid var(--red); }
.pi-acard .dots { font-family:var(--f-mono); font-size:34px; letter-spacing:.08em; color:var(--red); }
.pi-acard .motif .k { font-size:9.5px; letter-spacing:.1em; color:var(--chit-ink); margin-top:6px; }
.pi-acard .body { padding:14px 18px; flex:1; color:var(--ink); min-height:0; }
.pi-acard .trick { font-family:var(--f-display); font-size:23px; font-weight:700; }
.pi-acard .lesson { font-size:13.5px; line-height:1.5; color:var(--slate); margin-top:8px; }
.pi-acard .wild { border-top:1px dashed var(--rule); padding:10px 18px 12px; font-size:12.5px;
  line-height:1.45; color:var(--pencil-strip); }
.pi-acard .wild .k { font-size:9.5px; letter-spacing:.16em; color:var(--red); font-weight:700;
  text-align:left; margin-bottom:3px; }
.pi-acard .corner { position:absolute; right:12px; top:52px; }
.pi-acard .seal { width:150px; height:150px; border:3px double var(--chrome); border-radius:50%;
  background:var(--sheet); display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:4px; color:var(--chrome); }
.pi-acard .seal .t { font-family:var(--f-display); font-weight:700; font-size:22px; }
.pi-acard .seal .k { font-size:9.5px; letter-spacing:.2em; color:var(--chit-ink); }
/* The kit's slots under the card. */
.pi-kitstrip { display:flex; gap:10px; align-items:center; flex-wrap:wrap; justify-content:center; }
.pi-kitstrip .slot { width:46px; height:62px; border-radius:4px; display:flex; align-items:center;
  justify-content:center; font-family:var(--f-mono); font-size:9px; text-align:center; line-height:1.5;
  border:1px dashed rgba(240,235,221,.4); color:var(--ash); }
.pi-kitstrip .slot.done { background:var(--paper); border:1px solid var(--gold); color:var(--slate); }
.pi-kitstrip .slot.this { background:var(--paper); border:1.5px solid var(--pin-red); color:var(--red);
  box-shadow:0 0 14px rgba(232,106,94,.5); }
.pi-kitstrip .slot.own { border:1.5px dashed rgba(232,106,94,.6); color:var(--pin-red); }

/* The share card. */
.pi-scard { width:min(680px, 94vw); background:var(--cream); border-radius:4px; overflow:hidden;
  box-shadow:0 30px 80px rgba(0,0,0,.7); animation:pi-mint .6s cubic-bezier(.2,1.1,.35,1) .15s backwards;
  flex-shrink:0; }
.pi-scard .head { background:var(--chrome); color:var(--bone); padding:14px 22px; display:flex;
  justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; font-family:var(--f-mono);
  font-size:11px; letter-spacing:.2em; text-transform:uppercase; white-space:nowrap; }
.pi-scard .head .gold { color:var(--gold); letter-spacing:.14em; }
.pi-scard .body { padding:24px 26px; position:relative; }
.pi-scard .k { font-family:var(--f-mono); font-size:11px; letter-spacing:.18em; text-transform:uppercase;
  color:var(--pencil-warm); text-align:left; }
.pi-scard .k.gap { margin-top:16px; }
.pi-scard .claim { font-family:var(--f-display); font-size:clamp(18px,3vw,23px); font-weight:700;
  font-style:italic; line-height:1.3; color:var(--ink-warm); margin-top:6px; max-width:24ch; }
.pi-scard .trick { font-family:var(--f-display); font-size:16.5px; line-height:1.5; color:var(--ink-warm);
  margin-top:4px; }
.pi-scard .foot { display:flex; justify-content:space-between; gap:8px 14px; border-top:2px solid var(--ink-warm);
  margin-top:18px; padding-top:12px; font-family:var(--f-mono); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--kraft-ink); flex-wrap:wrap; line-height:1.8; }
.pi-scard .foot span { white-space:nowrap; }
.pi-scard .corner { position:absolute; top:18px; right:22px; }
.pi-verdict.big { font-size:15px; letter-spacing:.14em; border:3px double currentColor; padding:6px 13px;
  transform:rotate(7deg); }
</style>
"""
