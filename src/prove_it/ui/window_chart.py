"""The whole series, with the window someone chose drawn on top of it.

The verdict says the fall was real and was not the trend. That is two claims at once, and
prose makes a reader hold both in their head. The picture makes them one glance: a line
running the full width, a shaded band where the chosen years sit, and the line clearly
ending higher than it started.

The band is the point. A chart of the full series alone would quietly win the argument by
leaving the window out — which is the same trick in the other direction. Showing both says
what actually happened: the years quoted are real, they are on this line, and they are a
sixth of it.

Same inherited discipline as the other two canvases, each rule bought with a defect:
script-safe JSON because labels come from Genie's rows, measuring the content element
rather than the document because the alternative ratchets the frame without bound, never
reading a size back off the canvas because assigning `canvas.height` writes through to the
attribute, and no CSS custom properties in canvas calls because a context cannot resolve
them and paints black instead.
"""

from __future__ import annotations

from prove_it.ui.style import INK, MONO, NAVY, PAPER, PENCIL, RED, RULE, SERIF, rgba, script_json

LINE_COLOUR = NAVY
BAND_COLOUR = rgba("busted", 0.13)
BAND_EDGE = RED

HEIGHT = 300


def chart_height() -> int:
    return HEIGHT


def render_window(
    points: list[tuple[float, float]],
    window: tuple[float, float] | None = None,
) -> str:
    """Inline HTML for the series panel. Empty string unless there is a trend to show.

    `window` is the pair of years the naive query was asked about. Without one the series
    is drawn plain — which is the honest thing for a claim that never named a window.
    """
    if len(points) < 3:
        # Two points are a window, not a series. There is no "whole run" to contrast with.
        return ""

    ordered = sorted(points)
    first_year, first_value = ordered[0]
    last_year, last_value = ordered[-1]
    low_year, low_value = min(ordered, key=lambda p: p[1])
    direction = "higher" if last_value >= first_value else "lower"

    payload = script_json(
        {
            "points": [[y, round(v, 2)] for y, v in ordered],
            "window": list(window) if window else None,
            "line": LINE_COLOUR,
            "band": BAND_COLOUR,
            "bandEdge": BAND_EDGE,
            "height": HEIGHT,
        }
    )

    band_note = (
        f"The shaded years are the ones the claim picked out. They are real — the low "
        f"point was {low_value:.2f} in {low_year:.0f} — and they are a fraction of the run."
        if window
        else "Every year in the data."
    )

    return f"""
<div class="wc">
  <div class="wc-bar">
    <div class="wc-title">The whole run, {first_year:.0f} to {last_year:.0f}</div>
  </div>
  <canvas class="wc-canvas" height="{HEIGHT}"></canvas>
  <div class="wc-foot">
    <div class="wc-read">It ends {direction} than it started: {first_value:.2f} in
      {first_year:.0f}, {last_value:.2f} in {last_year:.0f}.</div>
    <div class="wc-note">{band_note}</div>
  </div>
</div>

<style>
  html, body {{ margin:0; padding:0; }}
  .wc {{ border:1px solid {RULE}; background:{PAPER}; font-family:{SERIF}; color:{INK}; }}
  .wc-bar {{ padding:10px 13px; border-bottom:1px solid {RULE}; }}
  .wc-title {{ font-family:{MONO}; font-size:10px;
    letter-spacing:.14em; text-transform:uppercase; color:{PENCIL}; }}
  .wc-canvas {{ display:block; width:100%; }}
  .wc-foot {{ padding:12px 13px; border-top:1px solid {RULE}; }}
  .wc-read {{ font-family:{SERIF}; font-weight:600;
    font-size:16px; line-height:1.4; color:{INK}; }}
  .wc-note {{ font-size:12px; line-height:1.5; color:{PENCIL}; margin-top:6px;
    max-width:70ch; }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.wc');
  var canvas = root.querySelector('.wc-canvas');
  var ctx = canvas.getContext('2d');

  var years = D.points.map(function (p) {{ return p[0]; }});
  var values = D.points.map(function (p) {{ return p[1]; }});
  var minYear = Math.min.apply(null, years), maxYear = Math.max.apply(null, years);
  // Only the maximum is needed: the axis floor is fixed at zero below, so the minimum
  // never enters the scale.
  var maxValue = Math.max.apply(null, values);

  // The axis starts at zero, on purpose and in contrast with the headline chart earlier
  // in the same session. That one cuts the bottom off to make four points look decisive
  // and admits it; this one is arguing about a trend, and a truncated axis here would be
  // the app playing the trick it just taught.
  var floor = 0, ceiling = maxValue * 1.15 || 1;

  function draw() {{
    var W = canvas.clientWidth;
    var H = D.height;
    var left = 46, right = W - 18, top = 22, bottom = H - 34;
    ctx.clearRect(0, 0, W, H);

    var x = function (year) {{
      if (maxYear === minYear) return (left + right) / 2;
      return left + (year - minYear) / (maxYear - minYear) * (right - left);
    }};
    var y = function (v) {{
      return bottom - (v - floor) / (ceiling - floor) * (bottom - top);
    }};

    if (D.window) {{
      var a = x(Math.min(D.window[0], D.window[1]));
      var b = x(Math.max(D.window[0], D.window[1]));
      ctx.fillStyle = D.band;
      ctx.fillRect(a, top, Math.max(2, b - a), bottom - top);
      ctx.strokeStyle = D.bandEdge;
      ctx.setLineDash([3, 3]);
      ctx.lineWidth = 1;
      [a, b].forEach(function (edge) {{
        ctx.beginPath(); ctx.moveTo(edge, top); ctx.lineTo(edge, bottom); ctx.stroke();
      }});
      ctx.setLineDash([]);
    }}

    ctx.strokeStyle = '{rgba("pencil", 0.35)}';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(left, bottom); ctx.lineTo(right, bottom); ctx.stroke();

    ctx.fillStyle = '{rgba("pencil", 0.85)}';
    ctx.font = '10px ' + {MONO!r};
    ctx.textAlign = 'center';
    ctx.fillText(String(Math.round(minYear)), left, bottom + 17);
    ctx.fillText(String(Math.round(maxYear)), right, bottom + 17);
    ctx.textAlign = 'right';
    ctx.fillText(ceiling.toFixed(1), left - 8, top + 4);
    ctx.fillText('0', left - 8, bottom + 3);

    ctx.strokeStyle = D.line;
    ctx.lineWidth = 2;
    ctx.beginPath();
    D.points.forEach(function (p, i) {{
      var px = x(p[0]), py = y(p[1]);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }});
    ctx.stroke();

    ctx.fillStyle = D.line;
    D.points.forEach(function (p) {{
      ctx.beginPath();
      ctx.arc(x(p[0]), y(p[1]), 2.2, 0, Math.PI * 2);
      ctx.fill();
    }});
  }}

  function fit() {{
    try {{
      var f = window.frameElement;
      if (f) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}

  function resize() {{
    var r = window.devicePixelRatio || 1;
    var H = D.height;
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
