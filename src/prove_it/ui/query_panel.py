"""Genie's query, annotated, with the explanation attached to the part it explains.

The product's central demand is that a child reads a query before betting on it. Printing
the SQL and hoping is not the same as making it readable: `STDDEV(maths_score)` means
nothing to a ten-year-old, and the case where it appears is the one whose entire lesson
lives inside that function. So each part the app can name is a target — point at it, or
tab to it, and the strip underneath says what that part does.

A frame rather than page markup, for two reasons that are both about what a browser will
actually run. Streamlit does not execute script in `st.markdown`, so a copy button and a
live explanation strip are impossible there; and a frame is the only place this app can put
JavaScript at all. The cost is the usual one — a separate document cannot read the page's
CSS custom properties — so the palette and the type stacks arrive by import, as they do in
every other frame here.

Accessibility is not a layer on top of this; it decides the shape. A hover-only affordance
would be unusable by keyboard and invisible to a screen reader, so every annotated part is
focusable, the strip is a live region that announces on focus, and the whole thing works
with a pointer, a keyboard, or a screen reader alone.
"""

from __future__ import annotations

import html

from prove_it.domain.explain import annotate
from prove_it.ui.style import (
    GOLD_DEEP,
    GOLD_SOFT,
    INK,
    MONO,
    PAPER,
    PENCIL,
    RULE,
    SERIF,
    rgba,
    script_json,
)

# Room for the query, the strip, and the header. The frame measures itself and corrects
# this, but a floor that is close keeps the first paint from jumping.
BASE_HEIGHT = 132
PER_LINE = 26
CHARS_PER_LINE = 62


def panel_height(sql: str | None) -> int:
    """A first guess at the height, refined by the frame once it can measure itself."""
    if not sql:
        return BASE_HEIGHT
    lines = sum(max(1, (len(part) // CHARS_PER_LINE) + 1) for part in sql.splitlines() or [""])
    return BASE_HEIGHT + PER_LINE * min(lines, 14)


def render_query_panel(sql: str | None, *, label: str = "The query Genie wrote") -> str:
    """Inline HTML for one annotated query. Empty string when there is no query.

    A refused turn has no SQL, and an empty panel captioned "the query Genie wrote" would
    be claiming one exists.
    """
    fragments = annotate(sql)
    if not fragments:
        return ""

    # The query is written into the markup, not built by the script. It used to be the other
    # way round — an empty <pre> filled in by JavaScript — which meant the one screen whose
    # whole job is "read the query before you bet" showed an empty box anywhere script did
    # not run, with no error to explain it. It also made the test asserting the query is on
    # screen unable to fail, because it matched the SQL inside the un-executed script.
    #
    # The script now only attaches behaviour to spans that already exist.
    parts = []
    for fragment in fragments:
        text = html.escape(fragment.text)
        if fragment.note is None:
            parts.append(text)
            continue
        described = html.escape(f"{fragment.text.strip()}: {fragment.note}")
        parts.append(
            f'<span class="qp-tok" tabindex="0" role="button" aria-label="{described}" '
            f'data-note="{html.escape(fragment.note)}">{text}</span>'
        )
    body = "".join(parts)

    explainable = sum(1 for fragment in fragments if fragment.note)
    described_panel = html.escape(
        f"{label}. {explainable} parts of this query can be explained; tab through them."
    )
    payload = script_json({"sql": sql or ""})

    return f"""
<div class="qp">
  <div class="qp-head">
    <span class="qp-label">{html.escape(label)}</span>
    <button class="qp-copy" type="button" aria-label="Copy this query to the clipboard">
      <span class="qp-copy-text">Copy</span>
    </button>
  </div>
  <pre class="qp-sql" tabindex="0" aria-label="{described_panel}">{body}</pre>
  <p class="qp-note" aria-live="polite">
    <span class="qp-note-idle">Point at a coloured part of the query — or press Tab — to
      find out what it does.</span>
  </p>
</div>

<style>
  html, body {{ margin:0; padding:0; background:transparent; }}
  .qp {{ font-family:{SERIF}; color:{INK}; background:{PAPER};
    border:1px solid {RULE}; border-radius:2px; box-shadow:0 2px 12px {rgba("ink", 0.07)}; }}
  .qp-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px;
    padding:10px 14px 8px 16px; border-bottom:1px solid {RULE}; }}
  .qp-label {{ font-family:{MONO}; font-size:10.5px; letter-spacing:.18em;
    text-transform:uppercase; color:{PENCIL}; font-weight:600; }}

  /* 44x44 of hit area for the copy control, per the target-size guidance, without the
     button drawing at that size. */
  .qp-copy {{ font-family:{MONO}; font-size:10.5px; letter-spacing:.12em;
    text-transform:uppercase; color:{INK}; background:transparent;
    border:1.5px solid {INK}; border-radius:3px; padding:7px 14px; min-height:34px;
    cursor:pointer; position:relative; transition:background .14s ease, color .14s ease; }}
  .qp-copy::after {{ content:""; position:absolute; inset:-6px -4px; }}
  .qp-copy:hover, .qp-copy:focus-visible {{ background:{INK}; color:{PAPER}; }}
  .qp-copy:focus-visible {{ outline:3px solid {GOLD_DEEP}; outline-offset:2px; }}
  .qp-copy.is-done {{ background:{GOLD_SOFT}; border-color:{GOLD_DEEP}; color:{INK}; }}

  .qp-sql {{ font-family:{MONO}; font-size:13px; line-height:1.95; color:{INK};
    margin:0; padding:18px 20px 16px 34px; white-space:pre-wrap; overflow-wrap:anywhere;
    position:relative; }}
  .qp-sql::before {{ content:""; position:absolute; left:20px; top:12px; bottom:12px;
    width:1px; background:{rgba("busted", 0.28)}; }}
  .qp-sql:focus-visible {{ outline:3px solid {GOLD_DEEP}; outline-offset:-3px; }}

  /* An explainable part. The underline is the affordance at rest — dotted, in the app's
     own gold, so it reads as "there is something here" without shouting over the SQL. */
  .qp-tok {{ position:relative; cursor:help; border-radius:2px;
    padding:1px 2px; margin:0 -1px;
    background-image:linear-gradient(to top, {rgba("nodata", 0.5)} 1.5px, transparent 1.5px);
    background-repeat:repeat-x; background-position:0 100%;
    transition:background-color .22s ease, color .22s ease; }}
  /* The sweep: a wash of gold crossing the fragment left to right, once, on arrival. */
  .qp-tok.is-live {{ background-color:{GOLD_SOFT}; color:{INK};
    animation:qp-sweep .42s cubic-bezier(.2,.8,.2,1); }}
  .qp-tok:focus-visible {{ outline:3px solid {GOLD_DEEP}; outline-offset:2px;
    background-color:{GOLD_SOFT}; }}
  @keyframes qp-sweep {{
    from {{ background-image:linear-gradient(90deg,
      {rgba("nodata", 0.55)} 0%, {rgba("nodata", 0.55)} 8%, transparent 8%); }}
    to   {{ background-image:linear-gradient(90deg,
      {rgba("nodata", 0.55)} 0%, {rgba("nodata", 0.55)} 100%, transparent 100%); }}
  }}

  .qp-note {{ margin:0; padding:12px 16px 14px; border-top:1px dashed {RULE};
    background:{rgba("nodata-soft", 0.35)}; font-size:14px; line-height:1.55; color:{INK};
    min-height:2.9em; }}
  .qp-note-idle {{ color:{PENCIL}; font-size:13px; }}
  .qp-note.is-live {{ animation:qp-rise .26s ease-out; }}
  @keyframes qp-rise {{ from {{ opacity:0; transform:translateY(3px); }}
                        to {{ opacity:1; transform:none; }} }}

  @media (prefers-reduced-motion: reduce) {{
    .qp-tok, .qp-tok.is-live, .qp-note.is-live, .qp-copy {{ animation:none; transition:none; }}
  }}
</style>

<script>
(function () {{
  var D = {payload};
  var root = document.querySelector('.qp');
  var pre = root.querySelector('.qp-sql');
  var note = root.querySelector('.qp-note');
  var idle = note.innerHTML;

  // The spans already exist, with their text, their notes and their ARIA. This only makes
  // them interactive, so everything except the highlight survives script being blocked.
  Array.prototype.forEach.call(pre.querySelectorAll('.qp-tok'), function (tok) {{
    var noteText = tok.getAttribute('data-note') || '';
    function show() {{
      note.textContent = noteText;
      note.classList.remove('is-live');
      void note.offsetWidth;
      note.classList.add('is-live');
      Array.prototype.forEach.call(pre.querySelectorAll('.qp-tok.is-live'), function (o) {{
        o.classList.remove('is-live');
      }});
      tok.classList.add('is-live');
    }}
    function clear() {{
      tok.classList.remove('is-live');
      if (!pre.querySelector('.qp-tok.is-live')) note.innerHTML = idle;
    }}
    tok.addEventListener('mouseenter', show);
    tok.addEventListener('mouseleave', clear);
    tok.addEventListener('focus', show);
    tok.addEventListener('blur', clear);
    // Enter and Space are what a keyboard user presses on something announced as a
    // button; without this the announcement would be a promise the frame does not keep.
    tok.addEventListener('keydown', function (e) {{
      if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); show(); }}
    }});
  }});

  var copy = root.querySelector('.qp-copy');
  var copyText = root.querySelector('.qp-copy-text');
  copy.addEventListener('click', function () {{
    function done(ok) {{
      copyText.textContent = ok ? 'Copied' : 'Press Ctrl+C';
      copy.classList.add('is-done');
      setTimeout(function () {{
        copyText.textContent = 'Copy';
        copy.classList.remove('is-done');
      }}, 1800);
    }}
    // The clipboard API needs a permission the parent page has not delegated to this
    // frame, so the old selection trick is the one that actually works here. It is tried
    // second only because the modern call is silent when it does work.
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(D.sql).then(function () {{ done(true); }}, fallback);
    }} else {{ fallback(); }}
    function fallback() {{
      try {{
        var box = document.createElement('textarea');
        box.value = D.sql;
        box.setAttribute('readonly', '');
        box.style.position = 'fixed';
        box.style.opacity = '0';
        document.body.appendChild(box);
        box.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(box);
        done(ok);
      }} catch (err) {{ done(false); }}
    }}
  }});

  function fit() {{
    try {{
      var f = window.frameElement;
      // The content element, never documentElement: the latter is at least the frame's own
      // height, so feeding it back ratchets the panel taller on every resize.
      if (f) f.style.height = Math.ceil(root.getBoundingClientRect().height + 2) + 'px';
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}
  window.addEventListener('resize', fit);
  fit();
  setTimeout(fit, 60);
}})();
</script>
"""
