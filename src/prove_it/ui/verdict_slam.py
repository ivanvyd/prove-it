"""The flip, staged: objection, the rewritten query lighting up, a freeze, the stamp,
and the chips.

Two verdicts side by side is a rendering. This is a beat. It borrows the parts of other
people's beats that are known to land and nothing else: Ace Attorney's order (present the
evidence, OBJECTION, the witness breaks), a hitstop scaled to how much flipped (Sakurai's
rule — a light hit is a couple of frames, a finishing blow is a real pause), Balatro's
overshoot easing on the stamp, and a count-up on the chips so the payout is watched
rather than read.

The whole timeline is a pure function of elapsed milliseconds. `apply(t)` sets every
class and number from `t` alone, which is what makes two things true at once: it plays
itself on load with requestAnimationFrame, and the recorder can call `window.__seek(t)`
frame by frame and get the identical picture. A component that animated with timers would
strobe under a rerun and could not be photographed deterministically.

Same inherited discipline as the charts: script-safe JSON because the SQL fragments and
the trick's name reach here from Genie's rows and the docket, and the frame is measured
off the content element rather than the document.
"""

from __future__ import annotations

from prove_it.domain.game import Outcome, Settlement
from prove_it.domain.verdict import Verdict

# Taken from the page's palette rather than restated here. This frame is a separate
# document, so the stylesheet's custom properties do not reach it — importing the values is
# the only route across that boundary, and the hardcoded copy that used to sit here is why
# the flip beat kept drawing itself in the pre-rework paper long after the page was manila.
from prove_it.ui.style import (
    INK,
    MONO,
    PALETTE,
    PAPER,
    PENCIL,
    RULE,
    SERIF,
    VERDICT_TEXT,
    script_json,
)

# The verdict chips, in the page's own verdict colours, so one verdict cannot come out in
# one red inside the frame and a different red in the receipt below it.
COLOURS = {
    "v-holds": (PALETTE["holds"], PALETTE["holds-soft"]),
    "v-busted": (PALETTE["busted"], PALETTE["busted-soft"]),
    "v-half": (PALETTE["accent"], PALETTE["accent-soft"]),
    "v-nodata": (PALETTE["nodata"], PALETTE["nodata-soft"]),
}

HEIGHT = 320
MAX_FRAGMENTS = 4
FRAGMENT_CHARS = 42

# How the page finds this frame in order to scroll to it. Named here, beside the markup it
# has to match, because the alternative was a bare string in app.py pointing at a class in
# this file: renaming `.vs` would read as cosmetic from inside here, the scroll would
# silently find nothing, and the beat the whole case pays for would stop being shown.
SLAM_MARKER = 'class="vs"'


def slam_height() -> int:
    return HEIGHT


def _clean_fragments(added: list[str]) -> list[str]:
    """The additions as chips a reader can take in at a glance.

    They arrive from the token diff, which is right for highlighting inside the SQL
    panel and wrong for a chip: it hands over runs like "department`, `" — a stray
    backtick and a comma around one word. Trim the punctuation the diff split on, drop
    anything that is not a word, and cap the count so the beat stays a beat.
    """
    out: list[str] = []
    for raw in added:
        text = raw.strip().strip("`,;() ").strip()
        if sum(ch.isalpha() for ch in text) < 3:
            continue
        text = text[:FRAGMENT_CHARS]
        if text not in out:
            out.append(text)
    return out[:MAX_FRAGMENTS]


def _chip(verdict: Verdict) -> dict[str, str]:
    label, css = VERDICT_TEXT[verdict]
    ink, soft = COLOURS[css]
    return {"label": label, "ink": ink, "soft": soft}


def _hitstop_ms(first: Verdict, second: Verdict) -> int:
    """How long the world stops before the stamp. Scaled to what flipped."""
    if first is second:
        return 0
    if second is Verdict.BUSTED:
        return 900
    if second is Verdict.HALF_TRUE:
        return 520
    return 300


def render_slam(
    *,
    first: Verdict,
    second: Verdict,
    trick: str | None,
    follow_up: str,
    added: list[str],
    settlement: Settlement | None,
    stake_label: str | None,
    points_before: int,
    points_after: int,
) -> str:
    """Inline HTML for the flip. Always renders — a case that did not flip still gets
    its objection and its stamp; it just gets no freeze and no shake, because the
    theatre must never outrun the arithmetic."""
    fragments = _clean_fragments(added)
    flipped = first is not second

    payout = None
    if settlement is not None and stake_label is not None:
        match settlement.outcome:
            case Outcome.RIGHT:
                payout = {
                    "text": f"Called it — {stake_label.lower()}, and right",
                    "tone": "win",
                }
            case Outcome.WRONG:
                payout = {
                    "text": f"Not this time — {stake_label.lower()}, and wrong",
                    "tone": "loss",
                }
            case Outcome.VOID:
                payout = {"text": "The data could not rule — nothing scored", "tone": "void"}

    payload = script_json(
        {
            "first": _chip(first),
            "second": _chip(second),
            "flipped": flipped,
            "trick": trick or "",
            "followUp": follow_up,
            "fragments": fragments,
            "hitstop": _hitstop_ms(first, second),
            "shake": "large"
            if second is Verdict.BUSTED and flipped
            else ("medium" if flipped else "none"),
            "payout": payout,
            "chipsBefore": points_before,
            "chipsAfter": points_after,
        }
    )

    return f"""
<div class="vs">
  <div class="vs-row vs-first">
    <span class="vs-k">The first verdict</span>
    <span class="vs-chip vs-chip1"></span>
  </div>
  <div class="vs-obj">
    <span class="vs-obj-word">Objection</span>
    <span class="vs-obj-q"></span>
  </div>
  <div class="vs-frags"></div>
  <div class="vs-row vs-second">
    <span class="vs-k">After cross-examination</span>
    <span class="vs-chip vs-chip2"></span>
    <span class="vs-trick"></span>
  </div>
  <div class="vs-pay">
    <span class="vs-chips"><span class="vs-num">0</span> pts</span>
    <span class="vs-pay-text"></span>
  </div>
</div>

<style>
  /* The browser's default `body {{ margin: 8px }}` is 16px of height this frame was never
     given: `st.iframe(height=...)` is told the CONTENT height, and the margin pushes
     the document past it, so the bottom is quietly cut on every frame at every width.
     Measured as a consistent 14px shortfall across all six visuals before this reset. */
  html, body {{ margin:0; padding:0; }}
  .vs {{ font-family:{SERIF}; color:{INK};
    background:{PAPER}; border:1px solid {RULE}; padding:16px 18px; }}
  .vs-row {{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; min-height:38px; }}
  .vs-k {{ font-family:{MONO}; font-size:10px; letter-spacing:.14em;
    text-transform:uppercase; color:{PENCIL}; min-width:190px; }}
  .vs-chip {{ display:inline-block; font-weight:700; font-size:13px; letter-spacing:.08em;
    text-transform:uppercase; padding:6px 12px; border:1.5px solid currentColor; }}
  .vs-chip2 {{ opacity:0; transform:scale(1.9) rotate(-7deg); }}
  .vs-chip2.is-on {{ opacity:1; transform:scale(1) rotate(-3deg);
    transition:transform .22s cubic-bezier(.34,1.56,.64,1), opacity .08s linear; }}
  .vs-obj {{ display:flex; align-items:center; gap:12px; margin:10px 0 8px; padding:8px 12px;
    background:{INK}; color:{PAPER}; transform:translateX(-18px); opacity:0; }}
  .vs-obj.is-on {{ transform:none; opacity:1; transition:transform .18s ease-out, opacity .12s; }}
  .vs-obj-word {{ font-weight:800; font-size:14px; letter-spacing:.18em;
    text-transform:uppercase; }}
  .vs-obj-q {{ font-style:italic; font-size:14px; opacity:.92; }}
  .vs-frags {{ display:flex; gap:8px; flex-wrap:wrap; min-height:26px; margin:0 0 10px 204px; }}
  .vs-frag {{ font-family:{MONO}; font-size:12px; padding:2px 7px;
    border:1px dashed {RULE}; color:{PENCIL}; opacity:.35; }}
  .vs-frag.is-on {{ background:{PALETTE["holds-soft"]}; color:{PALETTE["holds"]};
    border-color:{PALETTE["holds"]}; border-style:solid;
    opacity:1; transition:all .15s; }}
  .vs-trick {{ font-weight:700; font-size:15px; opacity:0; transform:translateY(4px); }}
  .vs-trick.is-on {{ opacity:1; transform:none; transition:all .25s ease-out; }}
  .vs-pay {{ display:flex; align-items:baseline; gap:14px; margin-top:12px; padding-top:10px;
    border-top:1px solid {RULE}; opacity:0; }}
  .vs-pay.is-on {{ opacity:1; transition:opacity .2s; }}
  .vs-chips {{ font-family:{MONO}; font-size:12px; letter-spacing:.12em;
    text-transform:uppercase; color:{PENCIL}; }}
  .vs-num {{ font-size:26px; font-weight:700; color:{INK}; letter-spacing:0;
    font-variant-numeric:tabular-nums; }}
  .vs-pay-text {{ font-weight:600; font-size:15px; }}
  .vs-pay--win .vs-pay-text {{ color:{PALETTE["holds"]}; }}
  .vs-pay--loss .vs-pay-text {{ color:{PALETTE["busted"]}; }}
  .vs-pay--void .vs-pay-text {{ color:{PALETTE["nodata"]}; }}
  /* Three shake tiers, by how much flipped. Reserved for the stamp: a shake on every
     action stops meaning anything. */
  /* At 375 the frame is 329px wide, and the two fixed widths above — a 190px label column
     and the 204px indent that lines the fragments up under it — leave about 125px for a
     chip naming a whole added column and its alias. Measured: content ran to 394px inside
     a 329px frame, so the chip naming what the fairer query ADDED was cut off, on the one
     beat the whole product exists for. `scrolling=False` means it could not be reached.
     Below 560px the label stops reserving a column and the fragments lose the indent. */
  @media (max-width: 560px) {{
    .vs-row {{ align-items:flex-start; gap:8px; }}
    .vs-k {{ min-width:0; width:100%; }}
    .vs-frags {{ margin-left:0; }}
    .vs-frag {{ max-width:100%; overflow-wrap:anywhere; }}
    .vs-obj {{ flex-direction:column; align-items:flex-start; gap:6px; }}
  }}
  .vs.shake-medium {{ animation:vs-shake-m .3s linear; }}
  .vs.shake-large {{ animation:vs-shake-l .5s linear; }}
  @keyframes vs-shake-m {{
    0%,100% {{ transform:none; }}
    25% {{ transform:translate(-4px,2px); }}
    50% {{ transform:translate(4px,-2px); }}
    75% {{ transform:translate(-2px,-3px); }} }}
  @keyframes vs-shake-l {{
    0%,100% {{ transform:none; }}
    20% {{ transform:translate(-7px,3px) rotate(-.4deg); }}
    40% {{ transform:translate(7px,-3px) rotate(.4deg); }}
    60% {{ transform:translate(-5px,-4px); }}
    80% {{ transform:translate(4px,3px); }} }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.vs');
  var $ = function (s) {{ return root.querySelector(s); }};

  var chip1 = $('.vs-chip1'), chip2 = $('.vs-chip2');
  function paint(el, chip) {{
    el.textContent = chip.label; el.style.color = chip.ink; el.style.background = chip.soft;
  }}
  paint(chip1, D.first);
  paint(chip2, D.second);
  $('.vs-obj-q').textContent = D.followUp;
  $('.vs-trick').textContent = D.trick;
  var frags = $('.vs-frags');
  D.fragments.forEach(function (f) {{
    var el = document.createElement('span');
    el.className = 'vs-frag'; el.textContent = f;
    frags.appendChild(el);
  }});
  var fragEls = Array.prototype.slice.call(frags.children);
  var pay = $('.vs-pay');
  if (D.payout) {{
    $('.vs-pay-text').textContent = D.payout.text;
    pay.classList.add('vs-pay--' + D.payout.tone);
  }}

  // The timeline, in ms. Every moment is an absolute time so apply(t) is a pure function.
  var T = {{}};
  T.objection = 500;
  T.fragStart = 950; T.fragStep = 340;
  T.freeze = T.fragStart + fragEls.length * T.fragStep + 250;
  T.stamp = T.freeze + D.hitstop;
  T.trick = T.stamp + 420;
  T.pay = T.stamp + 720; T.payDur = 760;
  T.total = T.pay + T.payDur + 700;
  window.__total = T.total;

  var shaken = false;
  function ease(u) {{ return 1 - Math.pow(1 - u, 3); }}
  function apply(t) {{
    $('.vs-obj').classList.toggle('is-on', t >= T.objection);
    fragEls.forEach(function (el, i) {{
      el.classList.toggle('is-on', t >= T.fragStart + i * T.fragStep);
    }});
    var stamped = t >= T.stamp;
    chip2.classList.toggle('is-on', stamped);
    if (stamped && !shaken && D.shake !== 'none') {{
      shaken = true; root.classList.add('shake-' + D.shake);
    }}
    if (!stamped) {{ shaken = false; root.classList.remove('shake-medium', 'shake-large'); }}
    $('.vs-trick').classList.toggle('is-on', t >= T.trick && !!D.trick);
    var showPay = t >= T.pay && !!D.payout;
    pay.classList.toggle('is-on', showPay);
    var u = Math.max(0, Math.min(1, (t - T.pay) / T.payDur));
    var n = D.chipsBefore;
    if (showPay) n = Math.round(D.chipsBefore + (D.chipsAfter - D.chipsBefore) * ease(u));
    $('.vs-num').textContent = String(n);
  }}

  // Seekable for the recorder: one call, one exact frame. Autoplay for everyone else,
  // and straight to the end for anyone who asked for less motion.
  // The first seek takes the wheel: the autoplay loop stops applying its own clock, or
  // a frame the recorder asked for is overwritten a few milliseconds later by the frame
  // the loop was about to draw anyway - which is exactly what happened on the first try.
  var seeking = false;
  window.__seek = function (t) {{
    seeking = true;
    apply(Math.max(0, Math.min(T.total, t)));
    fit();
  }};

  function fit() {{
    try {{
      var f = window.frameElement;
      if (f) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) {{ apply(T.total); fit(); return; }}
  var start = null;
  function tick(now) {{
    if (seeking) return;
    if (start === null) start = now;
    var t = now - start;
    apply(t);
    if (t < T.total) requestAnimationFrame(tick); else fit();
  }}
  apply(0); fit();
  requestAnimationFrame(tick);
}})();
</script>
"""
