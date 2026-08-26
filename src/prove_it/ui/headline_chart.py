"""The chart a headline would print.

Same two numbers the first query returned, drawn from just below the lower one instead of
from zero. The bars come out three times different for a gap of four points, which is how
an honest number becomes a dishonest picture — and the axis label says so, in the open,
because the point is to teach the trick rather than play it.

This sits beside the naive result deliberately. The child has just been told the gap looks
decisive; here is the chart that would have convinced them, with its own thumb on the
scale visible.
"""

from __future__ import annotations

import html

from prove_it.ui.style import GOLD_DEEP, GOLD_SOFT, GREEN, INK, MONO, NAVY, PENCIL, RED, SERIF

BAR_COLOURS = [NAVY, GOLD_DEEP, GREEN, RED]

MIN_HEIGHT = 26
MAX_HEIGHT = 150


def render_headline_chart(groups: list[tuple[str, float]]) -> str:
    """Two bars on a truncated axis, captioned with the trick. Empty unless two groups."""
    if len(groups) != 2:
        return ""

    # Round first, then measure. Genie returns full precision (492.64332917705605), and
    # the bar labels, the table above and the demo_data figures are all one decimal place.
    # Computing the gap from the raw value made the caption say "a gap of 4.6" directly
    # beneath its own labels reading 492.6 and 488.1 — a chart about a misleading picture
    # of numbers should not be the thing on screen whose arithmetic does not add up.
    groups = [(name, round(mean, 1)) for name, mean in groups]

    values = [mean for _, mean in groups]
    low, high = min(values), max(values)
    span = high - low
    if span <= 0:
        return ""

    # Start the axis just under the smaller value — exactly the move being demonstrated.
    floor = low - span * 0.35
    scale = high - floor

    bars, names = [], []
    for i, (name, mean) in enumerate(groups):
        height = MIN_HEIGHT + (mean - floor) / scale * (MAX_HEIGHT - MIN_HEIGHT)
        bars.append(
            f'<div class="hc-col">'
            f'<div class="hc-value">{mean:.1f}</div>'
            f'<div class="hc-bar" style="height:{height:.0f}px;'
            f'background:{BAR_COLOURS[i % len(BAR_COLOURS)]}"></div>'
            f"</div>"
        )
        names.append(f'<div class="hc-name">{html.escape(name)}</div>')

    return f"""
<div class="hc">
  <div class="hc-head">
    <span>The chart a headline would print</span>
    <span class="hc-warn">axis starts at {floor:.0f}, not 0</span>
  </div>
  <div class="hc-plot">{"".join(bars)}</div>
  <div class="hc-names">{"".join(names)}</div>
  <div class="hc-foot">Same two numbers. Cut the bottom off the axis and a gap of
    {span:.1f} looks like a landslide.</div>
</div>

<style>
  html, body {{ margin:0; padding:0; }}
  .hc {{ border:1px solid {GOLD_DEEP}; background:{GOLD_SOFT};
    padding:14px 16px 12px; font-family:{SERIF}; color:{INK}; }}
  .hc-head {{ display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap;
    font-family:{MONO}; font-size:10px; letter-spacing:.14em;
    text-transform:uppercase; color:{PENCIL}; }}
  .hc-warn {{ color:{GOLD_DEEP}; font-weight:600; }}
  /* Bounded, and centred inside that bound. Left to fill a 1080px panel the two bars
     float in the middle of an empty field and stop reading as a chart. */
  .hc-plot {{ display:flex; align-items:flex-end; justify-content:center; gap:44px;
    height:{MAX_HEIGHT + 24}px; padding-top:12px; max-width:340px; margin:0 auto;
    border-bottom:2px solid {GOLD_DEEP}; }}
  .hc-col {{ display:flex; flex-direction:column; align-items:center; gap:7px; }}
  .hc-value {{ font-family:{MONO}; font-size:13px;
    color:{INK}; }}
  .hc-bar {{ width:62px; border-radius:2px 2px 0 0; }}
  /* Below the axis, not on it. Sitting the label on the rule made it look like a
     strikethrough. */
  .hc-names {{ display:flex; justify-content:center; gap:44px; max-width:340px;
    margin:7px auto 0; }}
  .hc-name {{ width:62px; text-align:center;
    font-family:{MONO}; font-size:10px;
    letter-spacing:.12em; text-transform:uppercase; color:{PENCIL}; }}
  .hc-foot {{ font-size:12.5px; line-height:1.5; color:{INK}; margin-top:14px;
    text-align:center; }}
</style>

<script>
// Streamlit is given a fixed height from Python, which cannot know how many lines the
// caption will wrap to on a phone. Same-origin srcdoc lets the frame correct itself; if
// that is ever blocked the Python height stands as the floor.
(function () {{
  var root = document.querySelector('.hc');
  function fit() {{
    try {{
      var f = window.frameElement;
      // The content element, not documentElement — the latter is at least the frame's own
      // height, so using it makes the panel grow without bound on every resize.
      if (f && root) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}
  window.addEventListener('resize', fit);
  fit();
}})();
</script>
"""
