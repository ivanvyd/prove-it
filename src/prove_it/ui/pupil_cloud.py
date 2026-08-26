"""The evidence room: every pupil the averages were standing in front of.

The app asserts "scores vary by about 89 inside each group, nearly everyone overlaps" and
asks a child to take it on faith. This draws it. Two buttons — where the averages put
everyone, and where they actually are — and the distance between those pictures is the
whole lesson.

Both groups share one horizontal axis on purpose. An earlier version borrowed a rotating
3D cloud from a reference design; it photographed well and taught nothing, because the
depth jitter rendered as diagonal streaks that look like structure, and two separately
floating clouds cannot show overlap. Overlap is only visible when both groups are measured
against the same line.

Honesty rules, both load-bearing:

The dots are a reconstruction from the three numbers Genie returned — count, mean, spread
— not the pupil rows, which the app never asked for and would need to write a query to
get. The caption says so on screen at full size. An app that teaches children to distrust
a confident summary cannot quietly show them invented individuals.

The reconstruction is normal, which this data genuinely is. If the real distribution were
skewed the drawing would flatter it, and the caption would have to say something else.
"""

from __future__ import annotations

from prove_it.domain.distribution import GroupShape, overlap_fraction
from prove_it.ui.style import (
    GOLD_DEEP,
    GREEN,
    INK,
    MONO,
    NAVY,
    PAPER,
    PENCIL,
    RED,
    RULE,
    SERIF,
    rgba,
    script_json,
)

# In-palette, and deliberately not pink and blue: the groups are usually boys and girls,
# and colouring them that way is both a cliché and a nudge the app has no business making.
# Navy and ochre also stay apart for a colour-blind reader, which pink/blue does not.
GROUP_COLOURS = [NAVY, GOLD_DEEP, GREEN, RED]

BAND = 78
TOP = 34
FOOT = 30


def cloud_height(shapes: list[GroupShape]) -> int:
    return TOP + BAND * max(len(shapes), 2) + FOOT


def render_cloud(shapes: list[GroupShape], *, seed: int = 20260831) -> str:
    """Inline HTML+JS for the evidence room. Empty string when there is nothing to draw."""
    if len(shapes) < 2:
        return ""

    overlap = overlap_fraction(shapes)
    payload = script_json(
        {
            "groups": [
                {
                    "name": s.name,
                    "n": s.count,
                    # Rounded to the one decimal place this panel prints, so the caption's
                    # "two averages, N apart" agrees with the two labels above it and with
                    # the verdict line beside it. Computed from the raw means it said 4.6
                    # while the sentence directly below said 4.5 — caught by looking at a
                    # rendered frame, which is the only place the two appear together.
                    "mean": round(s.mean, 1),
                    "sd": s.spread,
                    "colour": GROUP_COLOURS[i % len(GROUP_COLOURS)],
                }
                for i, s in enumerate(shapes)
            ],
            "seed": seed,
            "band": BAND,
            "top": TOP,
            # The one true CSS height. Deliberately not read back off the canvas element:
            # assigning `canvas.height` writes through to the `height` *attribute*, so on a
            # 2x display each resize would read back the previous backing-store size and
            # double it. That ratcheted the panel to 28,000px.
            "height": cloud_height(shapes),
            "overlap": (
                f"About {overlap * 100:.0f}% of the two groups sit on top of each other."
                if overlap is not None
                else "Every pupil, placed by their own score."
            ),
        }
    )

    return f"""
<div class="pc">
  <div class="pc-bar">
    <div class="pc-title">The evidence room
      <span class="pc-n">{sum(s.count for s in shapes):,} pupils</span></div>
    <div class="pc-toggle">
      <button type="button" data-mode="avg" class="on">Where the averages put them</button>
      <button type="button" data-mode="all">Where they actually are</button>
    </div>
  </div>
  <canvas class="pc-canvas" height="{cloud_height(shapes)}"></canvas>
  <div class="pc-foot">
    <div class="pc-read"></div>
    <div class="pc-note">Each dot is one pupil, placed from the three numbers Genie returned
      for its group: how many, the average, and the spread. It is a drawing of that shape,
      not the individual rows — this app never asked for those.</div>
  </div>
</div>

<style>
  html, body {{ margin:0; padding:0; }}
  .pc {{ border:1px solid {RULE}; background:{PAPER}; font-family:{SERIF}; color:{INK}; }}
  .pc-bar {{ display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 13px; border-bottom:1px solid {RULE}; flex-wrap:wrap; }}
  /* On a phone the two toggle labels will not sit side by side with the title, so stop
     fighting it: stack once, predictably, rather than wrapping into three rows. */
  @media (max-width: 620px) {{
    .pc-bar {{ flex-direction:column; align-items:flex-start; }}
    .pc-toggle {{ display:flex; width:100%; }}
    .pc-toggle button {{ flex:1; text-align:center; }}
  }}
  .pc-title {{ font-family:{MONO}; font-size:10px;
    letter-spacing:.14em; text-transform:uppercase; color:{PENCIL}; }}
  .pc-n {{ color:{INK}; margin-left:8px; }}
  .pc-toggle button {{ font-family:{MONO}; font-size:11px;
    padding:7px 12px; border:1px solid {RULE}; background:transparent;
    color:{PENCIL}; cursor:pointer; }}
  .pc-toggle button + button {{ border-left:0; }}
  .pc-toggle button.on {{ background:{INK}; color:{PAPER};
    border-color:{INK}; }}
  .pc-canvas {{ display:block; width:100%; }}
  .pc-foot {{ padding:12px 13px; border-top:1px solid {RULE}; }}
  .pc-read {{ font-family:{SERIF}; font-weight:600;
    font-size:16px; line-height:1.4; color:{INK}; min-height:1.4em; }}
  .pc-note {{ font-size:12px; line-height:1.5; color:{PENCIL}; margin-top:6px;
    max-width:70ch; }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.pc');
  var canvas = root.querySelector('.pc-canvas');
  var read = root.querySelector('.pc-read');
  var ctx = canvas.getContext('2d');
  var still = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Deterministic: the same rows must always draw the same picture, or nobody can point
  // at it twice.
  var s = D.seed >>> 0;
  function rnd() {{ s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }}
  function gauss() {{
    var u = Math.max(rnd(), 1e-9), v = rnd();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }}

  // Past a few thousand dots the picture stops changing and a classroom tablet starts
  // dropping frames. The real count stays in the caption, where it is honest.
  var total = D.groups.reduce(function (a, g) {{ return a + g.n; }}, 0);
  var take = Math.min(1, 5200 / total);

  var pts = [];
  D.groups.forEach(function (g, gi) {{
    var n = Math.max(80, Math.round(g.n * take));
    for (var i = 0; i < n; i++) {{
      pts.push({{ g: gi, score: g.mean + gauss() * g.sd, jitter: rnd() }});
    }}
  }});

  // Frame on roughly three standard deviations either side of the middle, not on the
  // sampled extremes. A handful of outliers four deviations out would otherwise stretch
  // the axis and squeeze the actual crowd into the middle third of the panel, which
  // makes two heavily overlapping groups look further apart than they are.
  var means = D.groups.map(function (g) {{ return g.mean; }});
  var widest = Math.max.apply(null, D.groups.map(function (g) {{ return g.sd; }}));
  var centre = (Math.min.apply(null, means) + Math.max.apply(null, means)) / 2;
  var reach = (Math.max.apply(null, means) - Math.min.apply(null, means)) / 2 + widest * 2.9;
  var lo = centre - reach, hi = centre + reach;

  var mix = 0, target = 0;

  function xOf(v, W) {{ return 26 + (v - lo) / (hi - lo) * (W - 52); }}

  function draw() {{
    var W = canvas.clientWidth;
    var H = D.height;
    ctx.clearRect(0, 0, W, H);

    // One shared axis. Both groups measured against the same line is the entire reason
    // the overlap is visible at all.
    ctx.strokeStyle = '{rgba("pencil", 0.28)}';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(26, H - 20); ctx.lineTo(W - 26, H - 20); ctx.stroke();
    ctx.fillStyle = '{rgba("pencil", 0.85)}';
    ctx.font = '10px ' + {MONO!r};
    ctx.textAlign = 'left'; ctx.fillText(Math.round(lo), 26, H - 7);
    ctx.textAlign = 'right'; ctx.fillText(Math.round(hi), W - 26, H - 7);
    ctx.textAlign = 'center'; ctx.fillText('maths score', W / 2, H - 7);

    for (var gi = 0; gi < D.groups.length; gi++) {{
      var g = D.groups[gi];
      var bandTop = D.top + gi * D.band;
      ctx.fillStyle = g.colour;
      ctx.globalAlpha = 0.22;
      for (var i = 0; i < pts.length; i++) {{
        var p = pts[i];
        if (p.g !== gi) continue;
        var v = g.mean + (p.score - g.mean) * mix;
        ctx.fillRect(xOf(v, W), bandTop + 8 + p.jitter * (D.band - 30), 1.7, 1.7);
      }}
      ctx.globalAlpha = 1;

      var mx = xOf(g.mean, W);
      ctx.strokeStyle = g.colour; ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(mx, bandTop - 4); ctx.lineTo(mx, bandTop + D.band - 16); ctx.stroke();
      ctx.fillStyle = g.colour;
      ctx.font = '600 11px ' + {MONO!r};
      ctx.textAlign = 'center';
      ctx.fillText(g.name + ' · ' + g.mean.toFixed(1), mx, bandTop - 9);
    }}
  }}

  function caption() {{
    read.textContent = target === 0
      ? 'Two averages, ' + Math.abs(D.groups[0].mean - D.groups[1].mean).toFixed(1)
        + ' apart. This is everything the first query could see.'
      : D.overlap;
  }}

  function tick() {{
    if (Math.abs(mix - target) < 0.004) {{ mix = target; draw(); return; }}
    mix += (target - mix) * 0.10;
    draw();
    requestAnimationFrame(tick);
  }}

  root.querySelectorAll('.pc-toggle button').forEach(function (btn) {{
    btn.addEventListener('click', function () {{
      root.querySelectorAll('.pc-toggle button').forEach(function (b) {{
        b.classList.toggle('on', b === btn);
      }});
      target = btn.getAttribute('data-mode') === 'all' ? 1 : 0;
      caption();
      if (still) {{ mix = target; draw(); }} else {{ requestAnimationFrame(tick); }}
    }});
  }});

  // Streamlit is told a height in Python, which cannot know the viewport. Below about
  // 620px the toolbar wraps and the note runs to three lines, and the panel was clipped
  // by 100px on a phone. Same-origin srcdoc means the frame can measure itself and fix
  // its own height; the Python figure stays as the floor if that is ever blocked.
  function fit() {{
    try {{
      var f = window.frameElement;
      // Measure the CONTENT, never documentElement. documentElement.scrollHeight is at
      // least the frame's own height, so feeding it back in ratchets: the panel grew to
      // fourteen thousand pixels on the first try.
      if (f) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}

  function resize() {{
    var r = window.devicePixelRatio || 1;
    var H = D.height;
    // These two assignments reflect into the width/height *attributes*, which is why the
    // CSS height above comes from D and is never read back out of the element.
    canvas.width = canvas.clientWidth * r;
    canvas.height = H * r;
    canvas.style.height = H + 'px';
    ctx.setTransform(r, 0, 0, r, 0, 0);
    draw();
    fit();
  }}

  window.addEventListener('resize', resize);

  // Drive the spread from outside, one step at a time.
  //
  // The toggle animates on requestAnimationFrame, which is right for a person and wrong
  // for a frame-by-frame screen recorder: the whole transition finishes in about a
  // second of wall-clock time while the recorder has captured four frames, so the
  // finished video shows a jump rather than a crowd spreading out. A recorder can step
  // this instead and get the real animation at the video's own frame rate.
  //
  // It also makes the transition reachable from a test, which an rAF loop is not.
  window.__setMix = function (value) {{
    mix = Math.max(0, Math.min(1, value));
    target = mix;
    // Move the toggle with the picture. Without this a stepped recording showed the
    // dots fully spread while the button still claimed "where the averages put them",
    // which reads as the control being broken rather than as the demo driving it.
    var want = mix > 0.5 ? 'all' : 'avg';
    root.querySelectorAll('.pc-toggle button').forEach(function (b) {{
      b.classList.toggle('on', b.getAttribute('data-mode') === want);
    }});
    caption();
    draw();
  }};

  caption();
  resize();
}})();
</script>
"""
