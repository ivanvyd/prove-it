"""The picture of a reversal: every subgroup, then the total that disagrees with them.

The subgroup verdict says women were admitted at a higher rate in four of six departments
while the pooled rate favours men. That sentence is true and almost impossible to feel.
Drawn, it takes about a second: six pairs of dots where the women's dot is higher in most
of them, and then one more pair, set apart, where it is not.

Two decisions carry it.

The pooled pair is drawn in the SAME units on the SAME axis as the subgroups, separated by
a rule rather than by a different chart. A reader has to be able to see that the last pair
is made of the six before it, and a second panel with its own scale hides exactly that.

Dot size follows how many people were in each cell, because the reversal is caused by the
sizes. Department A admitted 82% of women and there were 108 of them; department F admitted
7% of women and there were 341. Without the sizes the picture shows a paradox; with them it
shows the reason.

Every lesson this file learned the hard way is inherited from `pupil_cloud.py`, and each
one is load-bearing: script-safe JSON because labels come from Genie's rows, measuring the
content element rather than the document because the alternative ratchets the frame to
fourteen thousand pixels, never reading a size back off the canvas because assigning
`canvas.height` writes through to the attribute, and rounding every displayed number before
it is compared or quoted.
"""

from __future__ import annotations

import html

from prove_it.domain.verdict import Subgroup
from prove_it.ui.style import (
    GOLD_DEEP,
    INK,
    MONO,
    NAVY,
    PAPER,
    PENCIL,
    RULE,
    SERIF,
    rgba,
    script_json,
)

# The same two ink colours the evidence room uses, and deliberately not pink and blue: the
# groups here are usually men and women, and colouring them that way is a cliche and a
# nudge the app has no business making. Navy and ochre also stay apart for a colour-blind
# reader.
LEFT_COLOUR = NAVY
RIGHT_COLOUR = GOLD_DEEP

ROW = 46
TOP = 58
# Just enough to clear the last row's dots and the gridlines under them. It was 92, which
# left a fifth of the panel as empty paper below the total.
FOOT = 30


def chart_height(groups: list[Subgroup]) -> int:
    # One row per subgroup, plus the pooled row and the rule above it.
    return TOP + ROW * (len(groups) + 1) + FOOT


def render_reversal(groups: list[Subgroup], pooled: tuple[float, float]) -> str:
    """Inline HTML for the reversal panel. Empty string when there is nothing to draw."""
    if len(groups) < 2:
        return ""

    against = sum(1 for g in groups if g.favours_right)
    left_name, right_name = groups[0].left, groups[0].right
    pooled_left, pooled_right = round(pooled[0], 1), round(pooled[1], 1)
    pooled_leader = left_name if pooled_left > pooled_right else right_name

    # Escaped copies for the HTML body, kept separate from the raw names above because the
    # two destinations need opposite things. These names are `str(row[...])` straight off
    # Genie's result rows (`domain/verdict.py`, `subgroup_rates`) — data this app does not
    # control — and the frame below is same-origin with scripts enabled, so an unescaped
    # group label there is script execution rather than a cosmetic bug.
    #
    # The JSON payload must NOT get the escaped form: it is read back by `JSON.parse` and
    # painted with `fillText` onto a canvas, which has no markup to be injected into and
    # would render `&amp;lt;` literally. `script_json` is that path's defence.
    left_html, right_html = html.escape(left_name), html.escape(right_name)
    leader_html = html.escape(pooled_leader)

    payload = script_json(
        {
            "rows": [
                {
                    "name": g.name,
                    "left": round(g.left_rate, 1),
                    "right": round(g.right_rate, 1),
                    "leftSize": g.left_size,
                    "rightSize": g.right_size,
                }
                for g in groups
            ],
            "pooled": {"left": pooled_left, "right": pooled_right},
            "leftName": left_name,
            "rightName": right_name,
            "leftColour": LEFT_COLOUR,
            "rightColour": RIGHT_COLOUR,
            "row": ROW,
            "top": TOP,
            "height": chart_height(groups),
        }
    )

    return f"""
<div class="rv">
  <div class="rv-bar">
    <div class="rv-title">Every group, and then the total</div>
    <div class="rv-key">
      <span><i style="background:{LEFT_COLOUR}"></i>{left_html}</span>
      <span><i style="background:{RIGHT_COLOUR}"></i>{right_html}</span>
    </div>
  </div>
  <canvas class="rv-canvas" height="{chart_height(groups)}"></canvas>
  <div class="rv-foot">
    <!-- No verb that has to agree with the label. Group names come from Genie's rows and
         can be singular, plural or a proper noun; this line read "men still comes out
         ahead" on a live screen, which is the same defect the verdict sentences already
         had and which I reintroduced here. -->
    <div class="rv-read">{right_html} did better in {against} of the {len(groups)} groups —
      and the total still favours {leader_html}.</div>
    <div class="rv-note">Each dot is one group's rate; the bigger the dot, the more people
      it is measured over. The total is the same six groups added up, which is why it can
      disagree with all of them: it is weighted by who was in which.</div>
  </div>
</div>

<style>
  /* The root sets the font as well as the ground. A frame is its own document, so an
     element that names no family gets the browser's default — which put `.rv-note`, the
     honesty caption under the slopegraph, in Times New Roman on a page with no Times
     anywhere else. Set here so every child inherits and only deliberate exceptions differ. */
  html, body {{ margin:0; padding:0; }}
  .rv {{ border:1px solid {RULE}; background:{PAPER}; font-family:{SERIF}; color:{INK}; }}
  .rv-bar {{ display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 13px; border-bottom:1px solid {RULE}; flex-wrap:wrap; }}
  .rv-title {{ font-family:{MONO}; font-size:10px;
    letter-spacing:.14em; text-transform:uppercase; color:{PENCIL}; }}
  .rv-key {{ display:flex; gap:14px; font-family:{MONO};
    font-size:11px; color:{PENCIL}; }}
  .rv-key i {{ display:inline-block; width:9px; height:9px; border-radius:50%;
    margin-right:5px; }}
  .rv-canvas {{ display:block; width:100%; }}
  .rv-foot {{ padding:12px 13px; border-top:1px solid {RULE}; }}
  .rv-read {{ font-family:{SERIF}; font-weight:600;
    font-size:16px; line-height:1.4; color:{INK}; }}
  .rv-note {{ font-size:12px; line-height:1.5; color:{PENCIL}; margin-top:6px;
    max-width:70ch; }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.rv');
  var canvas = root.querySelector('.rv-canvas');
  var ctx = canvas.getContext('2d');

  // The largest cell in the table sets the biggest dot, so the sizes are comparable
  // across the panel rather than per row.
  var biggest = 1;
  D.rows.forEach(function (r) {{
    biggest = Math.max(biggest, r.leftSize, r.rightSize);
  }});

  function radius(size) {{
    if (!biggest || !size) return 4;
    // Area in proportion to the count, floored so a tiny group is still visible.
    return Math.max(3.5, Math.min(13, Math.sqrt(size / biggest) * 13));
  }}

  function draw() {{
    var W = canvas.clientWidth;
    var H = D.height;
    ctx.clearRect(0, 0, W, H);

    var left = 92, right = W - 58;
    var span = right - left;
    var x = function (pct) {{ return left + (pct / 100) * span; }};

    // Gridlines stop just under the total's row rather than running to the bottom of the
    // canvas, which left them trailing through empty paper.
    var lastRow = D.top + D.rows.length * D.row;
    ctx.font = '11px ' + {MONO!r};
    ctx.fillStyle = '{rgba("pencil", 0.85)}';
    ctx.textAlign = 'center';
    for (var pct = 0; pct <= 100; pct += 25) {{
      ctx.strokeStyle = '{rgba("pencil", 0.14)}';
      ctx.beginPath();
      ctx.moveTo(x(pct), D.top - 18); ctx.lineTo(x(pct), lastRow + 20); ctx.stroke();
      ctx.fillText(pct + '%', x(pct), D.top - 26);
    }}

    function row(item, index, isPooled) {{
      var y = D.top + index * D.row;
      ctx.strokeStyle = '{rgba("pencil", 0.30)}';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x(item.left), y); ctx.lineTo(x(item.right), y); ctx.stroke();

      [[item.left, D.leftColour, item.leftSize],
       [item.right, D.rightColour, item.rightSize]].forEach(function (pair) {{
        ctx.fillStyle = pair[1];
        ctx.beginPath();
        ctx.arc(x(pair[0]), y, isPooled ? 8 : radius(pair[2]), 0, Math.PI * 2);
        ctx.fill();
      }});

      // Interpolated from the palette, not var(--ink): a canvas context cannot resolve a
      // CSS custom property and silently paints black when handed one.
      ctx.fillStyle = isPooled ? '{INK}' : '{rgba("pencil", 0.95)}';
      ctx.font = (isPooled ? '600 12px ' : '11px ') + {MONO!r};
      ctx.textAlign = 'right';
      ctx.fillText(item.name, left - 14, y + 4);
    }}

    D.rows.forEach(function (r, i) {{ row(r, i, false); }});

    // The rule is what says the last pair is made of the ones above it rather than being
    // a seventh group.
    var ruleY = D.top + D.rows.length * D.row - D.row / 2 + 6;
    ctx.strokeStyle = '{rgba("pencil", 0.45)}';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(28, ruleY); ctx.lineTo(W - 28, ruleY); ctx.stroke();
    ctx.setLineDash([]);

    row({{ name: 'ALL', left: D.pooled.left, right: D.pooled.right }},
        D.rows.length, true);
  }}

  function fit() {{
    try {{
      var f = window.frameElement;
      // The content element, never documentElement: the latter is at least the frame's
      // own height, so feeding it back grows without bound.
      if (f) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}

  function resize() {{
    var r = window.devicePixelRatio || 1;
    var H = D.height;
    // These assignments reflect into the width/height ATTRIBUTES, which is why the CSS
    // height comes from D and is never read back off the element.
    canvas.width = canvas.clientWidth * r;
    canvas.height = H * r;
    canvas.style.height = H + 'px';
    ctx.setTransform(r, 0, 0, r, 0, 0);
    draw();
    fit();
  }}

  window.addEventListener('resize', resize);
  resize();
}})();
</script>
"""
