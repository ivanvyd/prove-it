"""The wait, made into a beat.

Genie takes 15-30s a turn on a warm warehouse, longer cold. The old app put a spinner
there and the video cut it out. This turns the wait into the thing you watch: a case clock
counting up, and a board of the phases Genie actually moves through — FETCHING METADATA,
ASKING AI, EXECUTING QUERY, SEALED — each light coming on when its real status arrives.

The clock is owned by the iframe and derived from a start epoch passed in as a prop, NOT
driven from Python. That is the one design decision the whole component rests on: Streamlit
re-runs the script on every poll and remounts the component, so anything Python drives
would restart from zero each tick and strobe. Given `startedAtMs`, the iframe re-derives
the true elapsed time on every remount and the clock runs smooth across all of them.

`phase` is the highest-numbered status seen so far, so a remount that arrives mid-wait
lights every board light up to there rather than replaying them.
"""

from __future__ import annotations

# Taken from the page's palette rather than restated here: this frame is a separate
# document, so the stylesheet's custom properties never reach it. The room is painted in
# the masthead's own chrome, because that is what it is — instrumentation about the
# session, not content.
from prove_it.ui.style import ASH, BONE, CHROME, GOLD_BAR, MONO, SERIF, SLATE, rgba, script_json

# The order the board lights up in, mapped from Genie's MessageStatus. Several raw statuses
# fold onto one light: PENDING_WAREHOUSE and FETCHING_METADATA are both "getting ready".
PHASE_ORDER = ["READY", "THINKING", "QUERYING", "SEALED"]
_STATUS_TO_PHASE = {
    "SUBMITTED": "READY",
    "PENDING_WAREHOUSE": "READY",
    "FETCHING_METADATA": "READY",
    "FILTERING_CONTEXT": "READY",
    "ASKING_AI": "THINKING",
    "EXECUTING_QUERY": "QUERYING",
    "COMPLETED": "SEALED",
}
PHASE_LABELS = {
    "READY": "Fetching metadata",
    "THINKING": "Asking the model",
    "QUERYING": "Writing the query",
    "SEALED": "Sealed",
}

HEIGHT = 150


def room_height() -> int:
    return HEIGHT


def phase_for(status: str) -> str:
    """Which board light a raw status lights. A status the board has no light for maps
    to READY, the first one, rather than inventing a new light."""
    return _STATUS_TO_PHASE.get(status.upper(), "READY")


def render_room(*, phase: str, started_at_ms: float, done: bool) -> str:
    """Inline HTML for the interrogation room at one poll.

    `started_at_ms` is a wall-clock epoch (ms). The iframe keeps the clock running from it
    across remounts; `done` freezes the clock on the SEALED frame.
    """
    reached = PHASE_ORDER.index(phase) if phase in PHASE_ORDER else 0
    payload = script_json(
        {
            "order": PHASE_ORDER,
            "labels": PHASE_LABELS,
            "reached": reached,
            "startedAt": started_at_ms,
            "done": done,
        }
    )

    lights = "".join(
        f'<div class="ir-light" data-i="{i}"><span class="ir-dot"></span>'
        f'<span class="ir-name">{PHASE_LABELS[p]}</span></div>'
        for i, p in enumerate(PHASE_ORDER)
    )

    return f"""
<div class="ir">
  <div class="ir-head">
    <span class="ir-title">Genie is at the table</span>
    <span class="ir-clock">0.0s</span>
  </div>
  <div class="ir-board">{lights}</div>
</div>

<style>
  html, body {{ margin:0; padding:0; }}
  .ir {{ font-family:{SERIF}; color:{BONE};
    background:{CHROME}; border:1px solid {SLATE}; padding:16px 18px; }}
  .ir-head {{ display:flex; justify-content:space-between; align-items:baseline; }}
  .ir-title {{ font-family:{MONO}; font-size:11px; letter-spacing:.16em;
    text-transform:uppercase; color:{ASH}; }}
  .ir-clock {{ font-family:{MONO}; font-size:30px; font-weight:700;
    color:{BONE}; letter-spacing:.02em; font-variant-numeric:tabular-nums; }}
  .ir-board {{ display:flex; gap:20px; margin-top:14px; flex-wrap:wrap; }}
  .ir-light {{ display:flex; align-items:center; gap:8px; opacity:.35; transition:opacity .3s; }}
  .ir-light.is-on {{ opacity:1; }}
  .ir-dot {{ width:11px; height:11px; border-radius:50%; background:{ASH}; flex:none;
    transition:background .3s, box-shadow .3s; }}
  .ir-light.is-on .ir-dot {{ background:{GOLD_BAR};
    box-shadow:0 0 0 4px {rgba("gold-bar", 0.18)}; }}
  .ir-light.is-live .ir-dot {{ animation:ir-pulse 1s ease-in-out infinite; }}
  .ir-name {{ font-family:{MONO}; font-size:11px; letter-spacing:.08em;
    text-transform:uppercase; color:{ASH}; }}
  @keyframes ir-pulse {{ 0%,100% {{ box-shadow:0 0 0 4px {rgba("gold-bar", 0.10)}; }}
    50% {{ box-shadow:0 0 0 7px {rgba("gold-bar", 0.28)}; }} }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.ir');
  var clock = root.querySelector('.ir-clock');
  var lights = Array.prototype.slice.call(root.querySelectorAll('.ir-light'));

  lights.forEach(function (el, i) {{
    el.classList.toggle('is-on', i <= D.reached);
    el.classList.toggle('is-live', i === D.reached && !D.done);
  }});

  function fmt(ms) {{ return (ms / 1000).toFixed(1) + 's'; }}
  function paint() {{ clock.textContent = fmt(Math.max(0, Date.now() - D.startedAt)); }}
  function tick() {{ paint(); if (!D.done) requestAnimationFrame(tick); }}
  // Paint once synchronously from the epoch BEFORE the first animation frame, so a
  // remount mid-wait never shows the static "0.0s" for a frame — it resumes at the true
  // elapsed time immediately. The clock is re-derived from startedAt every remount, so it
  // never restarts at zero when Streamlit re-runs the script. Frozen on the sealed frame.
  paint();
  if (!D.done) requestAnimationFrame(tick);

  try {{
    var f = window.frameElement;
    if (f) {{
      f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
      // The first frame of a wait brings itself into view. The room renders under the
      // folder that was opened, and when that folder sits low in the viewport the room
      // lands below the fold, the one place a "something is happening" signal is no use.
      // Later phases remount the frame and must not scroll: the player may have moved.
      if (D.reached === 0) f.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});
    }}
  }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
}})();
</script>
"""
