"""Scene two: the board. A case, worked on a corkboard in a wooden frame.

This is the design file's `#er-frame` / `#er-board`, item for item: the claim clipping,
Genie's reasoning on index cards, the search warrant carrying the query, the sealed
evidence bag, the result strip that gets pinned up when the seal breaks, the second warrant
that fills the reserved space at the retrial, the chain-of-custody tag, and the red strings
between them — drawn from measured positions, exactly as the design's `_strings()` does.

It renders as one `st.iframe` document because the composition is absolute: every item sits
at a percentage of the board, and the strings are lines between bounding rectangles. Below
1000px of width the design stacks every item into one column (its `_layout()`), and this
document does the same with a media query and reports its own height to the page.

Everything on the board is data. The claim, the reasoning, the query, the ids, the rows,
the verdicts and the follow-up all come from the investigation; this module reads them and
lays them out. It composes no SQL and runs none — the warrant shows the query Genie wrote.
"""

from __future__ import annotations

import html
import re

from prove_it.domain.custody import custody_of, evidence_tag, same_conversation
from prove_it.domain.exhibits import Exhibit
from prove_it.domain.explain import annotate
from prove_it.domain.sqldiff import Change, diff_tokens
from prove_it.domain.verdict import Analysis, ResultTable, Verdict, is_rate_column
from prove_it.genie.models import Turn
from prove_it.session import Investigation, Stage
from prove_it.ui.render import for_display
from prove_it.ui.style import FONT_LINK, FONTS, PALETTE, VERDICT_TEXT, script_json

# Result rows pinned to the board. A window of years can run to thirty rows, and a sheet
# that long would push everything under it off the cork; the rest is on the receipt.
MAX_ROWS = 8

# The board's height on a wide screen, where the design fills the viewport. The retrial
# fills the right-hand third with a second warrant, so it needs the taller board.
HEIGHTS = {"wager": 760, "revealed": 880, "retrial": 920, "closed": 920}

_TOKEN = re.compile(r"\{\{([a-z][\w-]*)(?:@([\d.]+))?\}\}")
# Genie writes keywords in capitals and identifiers in lowercase backticks, which is what
# the warrant's red-keyword typing keys off. A list of keywords would be a list of the
# exact strings `tests/test_no_sql_in_app_code.py` is built to refuse; a shape is not.
_CAPS = re.compile(r"\b[A-Z][A-Z_]{1,}\b")
_N_OF_M = re.compile(r"\b(\d+ of \d+)\b")


def paint(css: str) -> str:
    """Resolve `{{token}}` and `{{token@alpha}}` to the palette's values.

    The board is an iframe and cannot see the page's custom properties, so its colours are
    written in by Python. A placeholder syntax rather than an f-string, because a stylesheet
    is nothing but braces.
    """

    def swap(match: re.Match[str]) -> str:
        value = PALETTE[match.group(1)]
        if match.group(2) is None:
            return value
        red, green, blue = (int(value.lstrip("#")[at : at + 2], 16) for at in (0, 2, 4))
        return f"rgba({red},{green},{blue},{match.group(2)})"

    return _TOKEN.sub(swap, css)


def board_height(phase: str) -> int:
    return HEIGHTS[phase]


def phase_of(inv: Investigation, *, finished: bool) -> str:
    """Which of the design's four phases this investigation is in."""
    if finished:
        return "closed"
    if inv.stage is Stage.REPAIRED:
        return "retrial"
    if inv.stage is Stage.REVEALED:
        return "revealed"
    return "wager"


# -- pieces ------------------------------------------------------------------------------


def _keywords(text: str) -> str:
    """Escaped SQL with its capitalised words typed in red, the way the warrant reads."""
    out: list[str] = []
    cursor = 0
    for match in _CAPS.finditer(text):
        out.append(html.escape(text[cursor : match.start()]))
        out.append(f'<b class="kw">{html.escape(match.group(0))}</b>')
        cursor = match.end()
    out.append(html.escape(text[cursor:]))
    return "".join(out)


def warrant_sql(sql: str) -> str:
    """The query with every part `explain.annotate` can name wrapped so a pointer — or a
    Tab — brings up what it does. Text is preserved exactly; only the wrapping is added."""
    parts = []
    for fragment in annotate(sql):
        if fragment.note is None:
            parts.append(_keywords(fragment.text))
            continue
        described = html.escape(f"{fragment.text.strip()}: {fragment.note}")
        parts.append(
            f'<span class="tok" tabindex="0" role="button" aria-label="{described}" '
            f'data-note="{html.escape(fragment.note)}">{_keywords(fragment.text)}</span>'
        )
    return "".join(parts)


def warrant_diff(before: str | None, after: str | None, exhibits: list[Exhibit]) -> str:
    """The second query with what it added marked, the way the design's second warrant
    highlights `department`. Removals are not drawn: this sheet is the new query, and the
    first warrant is still pinned beside it for anyone who wants the old one."""
    labels = {e.fragment for e in exhibits if e.fragment}
    out = []
    for line in diff_tokens(before, after):
        if line.change is Change.REMOVED:
            continue
        text = _keywords(line.text)
        if line.change is Change.ADDED:
            flagged = any(k in line.text for k in labels)
            out.append(f'<mark class="{"ex" if flagged else ""}">{text}</mark>')
        else:
            out.append(text)
    return "".join(out)


def _table(table: ResultTable | None, *, highlight: set[str] | None = None) -> str:
    if table is None or not table.rows:
        return ""
    columns = [c.name for c in table.columns]
    lit = highlight or set()
    head = "".join(f"<div>{html.escape(c)}</div>" for c in columns)
    rows = []
    for row in table.rows[:MAX_ROWS]:
        cells = []
        for i, column in enumerate(columns):
            raw = row[i] if i < len(row) else None
            shown = for_display(raw, column)
            text = "" if shown is None else html.escape(str(shown))
            klass = " hi" if (column in lit or (not lit and is_rate_column(column))) else ""
            cells.append(f'<div class="c{klass}">{text}</div>')
        rows.append(f'<div class="r">{"".join(cells)}</div>')
    if len(table.rows) > MAX_ROWS:
        more = len(table.rows) - MAX_ROWS
        rows.append(
            f'<div class="r more"><div class="c" style="grid-column:1/-1">'
            f"&hellip; {more} more row{'s' if more != 1 else ''} on the receipt</div></div>"
        )
    return (
        f'<div class="tbl" style="--cols:{len(columns)}">'
        f'<div class="r h">{head}</div>{"".join(rows)}</div>'
    )


def _stamp(verdict: Verdict, *, klass: str = "stamp") -> str:
    label, tone = VERDICT_TEXT[verdict]
    return f'<span class="{klass} {tone}">{html.escape(label)}</span>'


def _custody_short(turn) -> tuple[str, str]:
    record = custody_of(turn)
    if record is None:
        return "", ""
    return html.escape(record.short_conversation), html.escape(record.short_message)


def _source_line(inv: Investigation) -> str:
    case = inv.case
    if case is None:
        return "YOUR OWN RUMOUR &middot; TYPED, NOT FILED"
    kind = "REAL DATA" if case.real_data else "SYNTHETIC DATA"
    return f"{kind} &middot; {html.escape(case.source.upper())}"


def thought_cards(turn: Turn | None, table: str | None) -> str:
    """Genie's reasoning, as index cards. The design's third card is WHERE IT LOOKED — the
    table — typed rather than set, and that card is kept last here too.

    Falls back to the turn's one-line description when Genie sent no steps, and to a card
    saying so when it sent neither: the probe says steps come back 14/14 on Free Edition,
    but that is one space on one day, and the column must not become an empty frame.
    Every string here is Genie's, so every one is escaped.
    """
    cards: list[tuple[str, str, bool]] = []
    if turn is not None:
        steps = turn.ordered_thoughts
        if steps:
            # Every step Genie sent, in its order. The design draws three; the recording
            # has three plus the table, and a step dropped to fit a picture is a step the
            # reader was not shown. Four is where a card falls off the board's left column.
            for step in steps[:4]:
                cards.append((step.label, step.content, False))
        elif turn.description:
            cards.append(("What Genie understood", turn.description, False))
    # The table, as the design's typed WHERE IT LOOKED card — but only when Genie did not
    # already say where it looked. The recorded fixture includes a data-sourcing step
    # labelled "Where it looked", and appending the table under the same label put two
    # identical headings on the board, one over the full path and one over the bare name.
    already_sourced = any(label.strip().lower() == "where it looked" for label, _, _ in cards)
    if table and not already_sourced:
        cards.append(("Where it looked", table, True))
    if not cards:
        cards.append(("What Genie said", "Genie did not explain its working for this one.", False))
    tilts = ("-2deg", "1.4deg", "-.8deg", "1deg", "-1.2deg")
    out = []
    for i, (label, body, typed) in enumerate(cards):
        klass = "b typed" if typed else "b"
        out.append(
            f'<div class="card" style="transform:rotate({tilts[i % len(tilts)]})"><span class="pin blue"></span>'
            f'<div class="k">{html.escape(label)}</div>'
            f'<div class="{klass}">{html.escape(body)}</div></div>'
        )
    return "".join(out)


# -- the board -----------------------------------------------------------------------


def render_board(
    inv: Investigation,
    *,
    number: int,
    phase: str,
    exhibits: list[Exhibit] | None = None,
) -> str:
    """The whole corkboard for one investigation, in the given phase."""
    first, second = inv.first, inv.second
    sealed = phase == "wager"
    revealed = phase != "wager"
    retrial = phase in ("retrial", "closed")
    pre_retrial = phase in ("wager", "revealed")
    first_analysis: Analysis | None = inv.first_analysis
    second_analysis: Analysis | None = inv.second_analysis
    tag = evidence_tag(first)
    conv1, msg1 = _custody_short(first)
    conv2, msg2 = _custody_short(second)
    continued = same_conversation(first, second)
    exhibits = exhibits or []
    added_aliases = {e.alias for e in exhibits if e.alias}
    case_label = f"CASE N&ordm; {number:02d}" if number else "CASE N&ordm; 0"

    # The warrant.
    sql = first.sql if first is not None and first.has_query else None
    warrant_body = (
        f'<div class="sql">{warrant_sql(sql)}</div>'
        if sql
        else '<div class="sql none">Genie wrote no query for this claim: it could not turn '
        "it into a question this data can answer.</div>"
    )
    overturned = (
        '<span class="big-stamp" aria-label="Overturned">Overturned</span>'
        if retrial and inv.lesson_landed
        else ""
    )

    # The bag.
    if sealed:
        band = '<div class="band">Sealed &middot; do not open</div>'
        inside = (
            '<div class="blocks" aria-hidden="true">▚▚.▚%</div>'
            '<div class="bag-k">Result rows inside</div>'
        )
    else:
        band = '<div class="band torn-l">Sea&mdash;</div><div class="band torn-r">&mdash;led</div>'
        inside = (
            '<div class="blocks struck" aria-hidden="true">▚▚.▚%</div>'
            '<div class="hand red">emptied onto the board &darr;</div>'
        )
    tag_card = (
        f'<div class="tagcard">TAG <b>{html.escape(tag)}</b> &mdash; GENIE&rsquo;S ATTACHMENT '
        f"HANDLE.<br>HELD, NOT SPENT, UNTIL YOU STAKE.</div>"
        if tag
        else ""
    )

    # The result strip, pinned once the seal is broken.
    strip = ""
    if revealed and first_analysis is not None:
        rows = inv.first_result
        count = len(rows.rows) if rows else 0
        aside = inv.case.aside if inv.case and inv.case.aside else ""
        strip = (
            '<div id="er-strip"><span class="pin red mid"></span>'
            '<div class="strip-head">'
            f'<span class="k">Result &middot; query v1 &middot; {count} row{"s" if count != 1 else ""}</span>'
            f"{_stamp(first_analysis.verdict, klass='stamp arrive')}</div>"
            f"{_table(rows)}"
            f'<div class="line">{html.escape(first_analysis.reason)}</div>'
            + (f'<div class="hand red small">{html.escape(aside)}</div>' if aside else "")
            + "</div>"
        )

    # The same-conversation tag and the second warrant.
    conv_tag = ""
    retrial_sheet = ""
    holder = (
        '<div id="er-holder"><div>Reserved<br>for the retrial<br>'
        "<span>Cross-examine to fill</span></div></div>"
        if pre_retrial
        else ""
    )
    if retrial and second_analysis is not None:
        if continued:
            conv_tag = (
                '<div id="er-conv"><div class="k">Same conversation &mdash; continued, not '
                're-asked</div><div class="hand">one agent, holding the thread</div></div>'
            )
        asked = inv.transcript[-1] if inv.transcript else ""
        second_sql = (
            warrant_diff(sql, second.sql, exhibits)
            if second is not None and second.has_query
            else '<span class="none">Genie wrote no second query.</span>'
        )
        punch = _N_OF_M.sub(r'<span class="circle">\1</span>', html.escape(second_analysis.reason))
        conv_line = (
            f"SAME CONV <b>{conv2}&hellip;</b> &middot; MSG {msg2}&hellip;"
            if continued
            else f"CONV {conv2}&hellip; &middot; MSG {msg2}&hellip;"
        )
        retrial_sheet = (
            '<div id="er-retrial"><span class="pin red left"></span>'
            '<div class="w-head"><span class="w-title">Warrant N&ordm; 2</span>'
            f"{_stamp(second_analysis.verdict)}</div>"
            f'<div class="k asked">You asked: &ldquo;{html.escape(asked)}&rdquo;</div>'
            f'<div class="sql two">{second_sql}</div>'
            f"{_table(inv.second_result, highlight=added_aliases)}"
            f'<div class="line">{punch}</div>'
            f'<div class="foot">{conv_line}</div>'
            "</div>"
        )

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{FONT_LINK}
<style>{paint(BOARD_CSS)}</style></head>
<body>
<div id="er-frame"><div id="er-board">
  <div class="tooth" aria-hidden="true"></div>
  <div id="er-fixtures" aria-hidden="true">
    <span class="post a"></span><span class="lamp a"></span><span class="bulb a"></span>
    <span class="post b"></span><span class="lamp b"></span><span class="bulb b"></span>
  </div>
  <div id="er-cone-a" aria-hidden="true"></div><div id="er-cone-b" aria-hidden="true"></div>
  <svg id="er-strings" aria-hidden="true">
    <line id="er-line-1"></line><line id="er-line-2"></line><line id="er-line-3"></line>
    <line id="er-line-4"></line><line id="er-line-5"></line><line id="er-line-6"></line>
  </svg>

  <div id="er-claim"><span class="pin red top"></span><div class="clip">
    <div class="k rule">The daily rumour &middot; heard everywhere</div>
    <div class="claim">&ldquo;{html.escape(inv.claim)}&rdquo;</div>
    <div class="k src">{_source_line(inv)}</div>
    <div class="hand red right">check the query first!</div>
  </div></div>

  <div id="er-reason">{thought_cards(first, inv.case.table if inv.case else None)}</div>

  <div id="er-warrant"><span class="pin red left"></span><span class="pin red right"></span>
    <div class="w-head"><span class="w-title">Search warrant</span><span class="k red">Exhibit Q-1</span></div>
    <div class="k lead">The query Genie wrote &mdash; read it before any answer</div>
    {warrant_body}
    <div class="note" aria-live="polite"><span class="idle">Point at a part of the query &mdash; or press Tab &mdash; to find out what it does.</span></div>
    <div class="foot">Written by Genie &middot; CONV <b>{conv1}&hellip;</b> &middot; MSG {msg1}&hellip;
      <button class="copy" type="button" aria-label="Copy this query to the clipboard">Copy the query</button><br>
      Checkable in the Genie space&rsquo;s own history &mdash; not our record</div>
    {overturned}
  </div>

  <div id="er-bag"><span class="pin red top"></span><div class="bag">
    <div class="flapline"></div>{band}
    <div class="bag-body"><div class="k">Evidence &middot; {case_label}</div>{inside}</div>
    {tag_card}
  </div></div>

  {strip}{conv_tag}{holder}{retrial_sheet}

  <div id="er-tag"><span class="pin tack"></span>
    <div class="k">Chain of custody &mdash; every ID is Genie&rsquo;s own</div></div>
</div></div>
<script>
(function () {{
  var D = {script_json({"phase": phase, "sql": sql or "", "height": HEIGHTS[phase]})};
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function el(id) {{ return document.getElementById(id); }}
  function narrow() {{ return window.innerWidth < 1000; }}
  function strings() {{
    var b = el('er-board'); if (!b) return;
    var br = b.getBoundingClientRect(); if (!br.width) return;
    function P(id, fx, fy) {{
      var e = el(id); if (!e) return null;
      var r = e.getBoundingClientRect();
      return [r.left - br.left + r.width * fx, r.top - br.top + r.height * fy];
    }}
    var ph = D.phase, later = ph === 'retrial' || ph === 'closed', nw = narrow();
    var specs = nw ? [
      ['er-line-1', P('er-claim', .5, .98), P('er-reason', .5, .01), true],
      ['er-line-2', P('er-reason', .5, .99), P('er-warrant', .5, .01), true],
      ['er-line-3', P('er-warrant', .5, .99), P('er-bag', .5, .01), true],
      ['er-line-4', P('er-bag', .5, .99), P('er-strip', .5, .01), ph !== 'wager'],
      ['er-line-5', P('er-strip', .5, .99), P('er-conv', .5, .02), later],
      ['er-line-6', P('er-conv', .5, .98), P('er-retrial', .5, .01), later]
    ] : [
      ['er-line-1', P('er-claim', .5, .01), P('er-warrant', .07, .015), true],
      ['er-line-2', P('er-warrant', .95, .015), P('er-bag', .5, .012), true],
      ['er-line-3', P('er-warrant', .5, 1), P('er-tag', .03, .3), true],
      ['er-line-4', P('er-bag', .5, .98), P('er-strip', .5, .005), ph !== 'wager'],
      ['er-line-5', P('er-warrant', .95, .06), P('er-conv', .5, .08), later],
      ['er-line-6', P('er-conv', .92, .55), P('er-retrial', .07, .02), later]
    ];
    for (var i = 0; i < specs.length; i++) {{
      var s = specs[i], ln = el(s[0]); if (!ln) continue;
      if (!s[3] || !s[1] || !s[2]) {{ ln.style.display = 'none'; continue; }}
      ln.setAttribute('x1', s[1][0]); ln.setAttribute('y1', s[1][1]);
      ln.setAttribute('x2', s[2][0]); ln.setAttribute('y2', s[2][1]);
      if (ln.style.display === 'none' || !ln.style.display) {{
        ln.style.display = 'block';
        if (!reduce) {{
          ln.setAttribute('stroke-dasharray', '600');
          ln.style.animation = 'none'; void ln.getBoundingClientRect();
          ln.style.animation = 'er-draw .6s ease-out forwards';
        }}
      }}
    }}
  }}
  function fit() {{
    try {{
      var f = window.frameElement; if (!f) return;
      var want = narrow() ? document.documentElement.scrollHeight
                          : Math.max(D.height, document.documentElement.scrollHeight);
      f.style.height = Math.ceil(want) + 'px';
      // The board crops what scrollHeight cannot see: every item sits absolutely inside
      // overflow:hidden cork, so a tall reason column pokes past the bottom without
      // growing the document. Items are placed by a percentage of the board, so for an
      // item of height h at top t% the board clears it at H = h / (1 - t) — solve that
      // for each pinned item directly and take the tallest demand. Solving beats growing
      // in a loop: the strings overlay spans the full board and a loop chasing "nothing
      // touches the bottom" chased it forever.
      if (!narrow()) {{
        var b = el('er-board'), bh = b ? b.offsetHeight : 0;
        var chrome = f.getBoundingClientRect().height - bh;  // the frame around the cork
        var boardNeed = bh ? Math.max(bh, want - chrome) : 0;
        var ids = ['er-claim', 'er-reason', 'er-warrant', 'er-bag', 'er-strip',
                   'er-conv', 'er-retrial', 'er-tag'];
        for (var i = 0; i < ids.length && bh; i++) {{
          var it = el(ids[i]); if (!it) continue;
          var h = it.getBoundingClientRect().height;  // rect, so a card's tilt counts
          if (!h) continue;
          var frac = it.offsetTop / bh;
          if (frac >= 0.98) continue;
          boardNeed = Math.max(boardNeed, (h + 26) / (1 - frac));
        }}
        if (bh) f.style.height = Math.ceil(boardNeed + chrome) + 'px';
      }}
    }} catch (err) {{ /* cross-origin: keep the height Python asked for */ }}
  }}
  function settle() {{ fit(); strings(); }}
  window.addEventListener('resize', settle);
  settle(); setTimeout(settle, 120); setTimeout(settle, 900);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(settle);
  setTimeout(function () {{ var c = el('er-cone-a'); if (c) c.style.opacity = '1'; }}, 250);
  setTimeout(function () {{ var c = el('er-cone-b'); if (c) c.style.opacity = '1'; }}, 650);

  // The warrant explains itself: point at a part, or Tab to it, and the note says what
  // that part does. The note is one live region so a screen reader hears it once.
  var note = document.querySelector('#er-warrant .note'), idle = note ? note.innerHTML : '';
  var toks = document.querySelectorAll('#er-warrant .tok');
  function show(t) {{ if (!note) return; note.innerHTML = ''; note.textContent = t.getAttribute('data-note'); note.classList.add('live'); }}
  function hide() {{ if (!note) return; note.innerHTML = idle; note.classList.remove('live'); }}
  for (var j = 0; j < toks.length; j++) {{
    toks[j].addEventListener('mouseenter', function (e) {{ show(e.currentTarget); }});
    toks[j].addEventListener('focus', function (e) {{ show(e.currentTarget); }});
    toks[j].addEventListener('mouseleave', hide);
    toks[j].addEventListener('blur', hide);
  }}
  var copy = document.querySelector('#er-warrant .copy');
  if (copy) copy.addEventListener('click', function () {{
    function done(ok) {{ copy.textContent = ok ? 'Copied' : 'Copy failed'; setTimeout(function () {{ copy.textContent = 'Copy the query'; }}, 1800); }}
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(D.sql).then(function () {{ done(true); }}, function () {{ done(false); }});
    }} else {{ done(false); }}
  }});
}})();
</script>
</body></html>"""
    return doc


BOARD_CSS = """
html, body { margin:0; padding:0; background:transparent; height:100%; font-family: FONT_BODY; color:{{ink-warm}}; }
* { box-sizing:border-box; }
@keyframes er-sway { 0%,100% { transform:rotate(-1.1deg); } 50% { transform:rotate(1.3deg); } }
@keyframes er-stamp { 0% { opacity:0; transform:rotate(-8deg) scale(2.1); } 55% { opacity:1; transform:rotate(-8deg) scale(.93); } 100% { opacity:1; transform:rotate(-8deg) scale(1); } }
@keyframes er-stamp-big { 0% { opacity:0; transform:translate(-50%,-50%) rotate(-12deg) scale(2.6); } 55% { opacity:1; transform:translate(-50%,-50%) rotate(-12deg) scale(.95); } 100% { opacity:1; transform:translate(-50%,-50%) rotate(-12deg) scale(1); } }
@keyframes er-pin { 0% { opacity:0; transform:rotate(-2deg) translateY(-30px) scale(1.06); } 100% { opacity:1; transform:rotate(-2deg) translateY(0) scale(1); } }
@keyframes er-pin2 { 0% { opacity:0; transform:rotate(1.2deg) translateY(-30px) scale(1.06); } 100% { opacity:1; transform:rotate(1.2deg) translateY(0) scale(1); } }
@keyframes er-draw { from { stroke-dashoffset:600; } to { stroke-dashoffset:0; } }
@keyframes er-pop { 0% { opacity:0; transform:rotate(2deg) scale(.6); } 70% { transform:rotate(2deg) scale(1.08); } 100% { opacity:1; transform:rotate(2deg) scale(1); } }
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } .stamp, .big-stamp { opacity:1 !important; } }

/* The frame and the cork. */
#er-frame { height:100%; min-height:640px; background:linear-gradient(180deg, {{frame}}, {{frame-deep}});
  border-radius:6px; padding:clamp(9px,1.1vw,15px); box-shadow:0 18px 60px {{black@0.6}}; }
#er-board { position:relative; width:100%; height:100%; border-radius:2px; overflow:hidden;
  background:linear-gradient(160deg, {{cork}}, {{cork-mid}} 55%, {{cork-deep}});
  box-shadow:inset 0 0 80px {{cork-shadow@0.55}}; }
.tooth { position:absolute; inset:0; background-image:radial-gradient({{tooth@0.22}} 1.2px, transparent 1.3px),
  radial-gradient({{tooth-light@0.1}} 1px, transparent 1.1px); background-size:26px 26px, 34px 34px;
  background-position:0 0, 12px 9px; }
/* Two lamps clipped to the top of the frame, and the cones they throw. */
#er-fixtures span { position:absolute; display:block; }
#er-fixtures .post { top:-6px; width:3px; height:34px; background:{{cord}}; }
#er-fixtures .post.a { left:24.5%; } #er-fixtures .post.b { left:75.5%; }
#er-fixtures .lamp { top:26px; width:55px; height:26px; border-radius:8px 8px 44px 44px; z-index:6;
  background:linear-gradient(180deg, {{fixture}}, {{fixture-deep}}); }
#er-fixtures .lamp.a { left:calc(24.5% - 25px); } #er-fixtures .lamp.b { left:calc(75.5% - 25px); }
#er-fixtures .bulb { top:44px; width:21px; height:16px; border-radius:50%; z-index:6;
  background:radial-gradient(circle at 50% 40%, {{bulb}}, {{bulb-warm}} 60%, {{bulb-warm@0.2}} 85%, transparent);
  box-shadow:0 0 26px 9px {{bulb-warm@0.4}}; }
#er-fixtures .bulb.a { left:calc(24.5% - 8px); } #er-fixtures .bulb.b { left:calc(75.5% - 8px); }
#er-cone-a, #er-cone-b { position:absolute; top:44px; height:88%; opacity:0; transition:opacity 1.1s ease;
  pointer-events:none; z-index:5; }
#er-cone-a { left:2.5%; width:44%; background:radial-gradient(ellipse 52% 62% at 50% 0%, {{cone@0.34}}, {{cone@0.1}} 52%, transparent 74%); }
#er-cone-b { left:53.5%; width:46%; background:radial-gradient(ellipse 52% 62% at 50% 0%, {{cone@0.3}}, {{cone@0.09}} 52%, transparent 74%); }
#er-strings { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; z-index:3;
  filter:drop-shadow(0 2px 1px {{black@0.4}}); }
#er-strings line { stroke:{{string}}; stroke-width:2.2; display:none; }

/* Pins. */
.pin { position:absolute; width:14px; height:14px; border-radius:50%; z-index:6;
  background:radial-gradient(circle at 35% 30%, {{pin-red}}, {{pin-red-deep}}); box-shadow:0 3px 5px {{black@0.5}}; }
.pin.top { left:50%; top:-5px; transform:translateX(-50%); }
.pin.mid { left:50%; top:-5px; transform:translateX(-50%); width:13px; height:13px; }
.pin.left { left:14px; top:-5px; } .pin.right { right:14px; top:-5px; }
.pin.blue { left:12px; top:-5px; width:11px; height:11px; background:radial-gradient(circle at 35% 30%, {{pin-blue}}, {{pin-blue-deep}}); box-shadow:0 2px 4px {{black@0.5}}; }
.pin.tack { left:-4px; top:8px; width:9px; height:9px; background:{{cream}}; border:2px solid {{kraft-blocks}}; box-shadow:none; }

/* Type. */
.k { font-family: FONT_MONO; font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:{{pencil-warm}}; }
.k.red { color:{{red-sql}}; letter-spacing:.12em; }
.hand { font-family: FONT_HAND; font-size:17px; }
.hand.red { color:{{red-hand}}; }
.hand.right { text-align:right; transform:rotate(-3deg); margin-top:8px; font-size:20px; }
.hand.small { font-size:16px; transform:rotate(-1deg); margin-top:3px; }
.stamp { display:inline-block; font-family: FONT_MONO; font-weight:700; font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; border:2px solid currentColor; border-radius:3px; padding:2px 7px; white-space:nowrap;
  transform:rotate(-8deg); }
.stamp.arrive { opacity:0; animation:er-stamp .45s cubic-bezier(.2,1.4,.4,1) .9s forwards; }
.v-holds { color:{{green}}; } .v-busted { color:{{red}}; } .v-half { color:{{navy}}; } .v-nodata { color:{{gold-deep}}; }
.big-stamp { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%) rotate(-12deg);
  font-family: FONT_MONO; font-weight:700; font-size:clamp(22px,2.2vw,30px); letter-spacing:.16em; text-transform:uppercase;
  color:{{red}}; border:5px double {{red}}; border-radius:6px; padding:8px 22px; background:{{cream@0.65}};
  opacity:0; animation:er-stamp-big .55s cubic-bezier(.2,1.4,.4,1) 1s forwards; z-index:5; white-space:nowrap; }

/* The claim clipping. */
#er-claim { position:absolute; left:2.2%; top:6.5%; width:21.5%; transform:rotate(-1.8deg); z-index:4; }
.clip { background:{{clipping}}; padding:16px 18px 18px; box-shadow:0 8px 20px {{black@0.4}};
  clip-path:polygon(0 0, 100% 0, 100% 96%, 96% 100%, 88% 97%, 74% 100%, 60% 97%, 42% 100%, 26% 97%, 12% 100%, 0 96%); }
.clip .rule { font-size:10.5px; letter-spacing:.18em; border-bottom:1px solid {{rule-clip}}; padding-bottom:6px; }
.clip .claim { font-family: FONT_BODY; font-size:clamp(17px,1.5vw,20px); font-weight:700; font-style:italic; line-height:1.3; color:{{ink-warm}}; margin-top:10px; }
.clip .src { margin-top:10px; line-height:1.7; }

/* Genie's reasoning. */
#er-reason { position:absolute; left:3%; top:44%; width:20%; z-index:4; }
.card { position:relative; background:{{paper}}; border:1px solid {{rule-soft}}; padding:10px 13px; box-shadow:0 6px 14px {{black@0.35}}; }
.card + .card { margin-top:10px; }
.card .k { letter-spacing:.14em; color:{{navy}}; font-weight:600; }
.card .b { font-size:14px; line-height:1.5; color:{{ink-brown}}; margin-top:4px; }
.card .b.typed { font-family: FONT_TYPE; font-size:12.5px; line-height:1.6; overflow-wrap:anywhere; }

/* The search warrant. */
#er-warrant { position:absolute; left:27.5%; top:4.5%; width:25.5%; background:{{cream}}; padding:18px 20px 16px;
  transform:rotate(.8deg); box-shadow:0 10px 26px {{black@0.45}}; z-index:4; }
.w-head { display:flex; justify-content:space-between; align-items:baseline; gap:8px; border-bottom:2px solid {{ink-warm}};
  padding-bottom:8px; flex-wrap:wrap; }
.w-title { font-family: FONT_TYPE; font-size:16px; letter-spacing:.12em; text-transform:uppercase; color:{{ink-warm}}; white-space:nowrap; }
.k.lead { letter-spacing:.12em; margin-top:8px; line-height:1.7; }
.k.asked { letter-spacing:.1em; margin-top:7px; line-height:1.7; }
.sql { font-family: FONT_TYPE; font-size:clamp(12px,1vw,14px); line-height:1.85; color:{{ink-warm}}; margin-top:10px;
  white-space:pre-wrap; overflow-wrap:anywhere; }
.sql .kw { color:{{red-sql}}; font-weight:400; }
.sql.two { font-size:12px; line-height:1.8; margin-top:8px; }
.sql mark { background:{{green-mark}}; color:{{green-deep}}; padding:0 2px; }
.sql .none, .sql.none { color:{{pencil-warm}}; font-style:italic; }
/* An explainable part: a dotted underline at rest, lit when pointed at. */
.tok { cursor:help; border-bottom:1px dotted {{gold-deep}}; border-radius:2px; transition:background .15s ease; }
.tok:hover, .tok:focus-visible { background:{{green-mark}}; outline:none; }
.tok:focus-visible { box-shadow:0 0 0 2px {{gold-deep}}; }
.note { border-top:1px dashed {{rule-dash}}; margin-top:10px; padding-top:8px; font-family: FONT_MONO; font-size:10px;
  letter-spacing:.06em; line-height:1.7; color:{{pencil-warm}}; text-transform:uppercase; min-height:2.6em; }
.note.live { color:{{ink-warm}}; text-transform:none; font-family: FONT_BODY; font-size:13px; letter-spacing:0; }
.foot { border-top:1px dashed {{rule-dash}}; margin-top:8px; padding-top:8px; font-family: FONT_MONO; font-size:10px;
  letter-spacing:.06em; line-height:1.8; color:{{pencil-warm}}; text-transform:uppercase; overflow-wrap:anywhere; }
.foot b { color:{{red-sql}}; }
.copy { font:inherit; letter-spacing:inherit; text-transform:inherit; color:{{red-sql}}; background:none; border:0;
  border-bottom:1px solid {{red-sql}}; padding:0; margin-left:8px; cursor:pointer; min-height:24px; }
.copy:focus-visible { outline:2px solid {{gold-deep}}; outline-offset:2px; }

/* The evidence bag. */
#er-bag { position:absolute; left:59.5%; top:8%; width:14.5%; z-index:4; transform-origin:top center; animation:er-sway 7s ease-in-out infinite; }
.bag { position:relative; background:linear-gradient(175deg, {{kraft}}, {{kraft-mid}} 60%, {{kraft-deep}}); border:1px solid {{kraft-line}};
  border-radius:3px; padding:38px 14px 18px; box-shadow:0 10px 24px {{black@0.45}}; }
.flapline { position:absolute; left:0; right:0; top:0; height:26px; background:linear-gradient(180deg, {{kraft-band}}, {{kraft-band-deep}}); border-bottom:1px dashed {{kraft-dash}}; }
.band { position:absolute; left:-10px; right:-10px; top:44px; height:32px; background:{{red@0.92}}; transform:rotate(-3deg);
  display:flex; align-items:center; justify-content:center; box-shadow:0 3px 8px {{black@0.35}}; z-index:2;
  font-family: FONT_MONO; font-weight:700; font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:{{wax-ink}}; white-space:nowrap; }
.band.torn-l { right:auto; width:54%; transform:rotate(-9deg); background:{{red@0.88}}; font-size:10.5px; letter-spacing:.18em; box-shadow:none; }
.band.torn-r { left:auto; width:50%; top:40px; transform:rotate(7deg); background:{{red@0.88}}; font-size:10.5px; letter-spacing:.18em; box-shadow:none; }
.bag-body { text-align:center; margin-top:26px; }
.bag-body .k { font-size:10.5px; letter-spacing:.16em; color:{{kraft-ink}}; }
.bag-k { font-family: FONT_MONO; font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:{{kraft-ink}}; margin-top:8px; }
.blocks { font-family: FONT_MONO; font-size:22px; letter-spacing:.1em; color:{{kraft-blocks}}; margin-top:8px; user-select:none; }
.blocks.struck { font-size:16px; text-decoration:line-through; text-decoration-thickness:2px; }
.bag .hand { margin-top:6px; transform:rotate(-2deg); }
.tagcard { display:inline-block; background:{{paper}}; border:1px solid {{tag-line}}; border-radius:2px; padding:6px 10px; margin-top:12px;
  transform:rotate(-1deg); max-width:100%; font-family: FONT_MONO; font-size:9.5px; letter-spacing:.06em; color:{{slate}}; line-height:1.6;
  overflow-wrap:anywhere; text-align:left; }
.tagcard b { letter-spacing:.12em; }

/* The result strip. */
#er-strip { position:absolute; left:56.5%; top:48%; width:20.5%; background:{{paper}}; border:1px solid {{rule-soft}}; padding:14px 16px;
  transform:rotate(-2deg); box-shadow:0 10px 26px {{black@0.45}}; z-index:4; animation:er-pin .5s ease-out .25s backwards; }
.strip-head { display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; }
.strip-head .k { letter-spacing:.14em; color:{{pencil-strip}}; }
.tbl { border:1px solid {{rule-soft}}; margin-top:10px; font-family: FONT_MONO; font-size:11.5px; color:{{ink-warm}}; }
.tbl .r { display:grid; grid-template-columns:1.1fr repeat(calc(var(--cols) - 1), 1fr); border-bottom:1px solid {{row-line}}; }
.tbl .r:last-child { border-bottom:0; }
.tbl .r.h { background:{{table-head}}; border-bottom:1px solid {{rule-soft}}; color:{{pencil-strip}}; font-size:10px; letter-spacing:.06em; text-transform:uppercase; }
.tbl .r > div { padding:6px 8px; overflow-wrap:anywhere; }
.tbl .c.hi { font-weight:700; }
#er-retrial .tbl .c.hi { color:{{green-deep}}; }
.tbl .r.more .c { color:{{pencil-warm}}; font-size:10px; letter-spacing:.06em; text-transform:uppercase; }
.line { font-family: FONT_BODY; font-size:14px; font-weight:600; line-height:1.4; margin-top:9px; color:{{ink-warm}}; }
.circle { border:2.5px solid {{red}}; border-radius:50%; padding:1px 6px; display:inline-block; transform:rotate(-2deg); }

/* The same-conversation tag. */
#er-conv { position:absolute; left:60.5%; top:39.5%; z-index:5; background:{{paper}}; border:2px solid {{string}}; border-radius:20px;
  padding:8px 16px; transform:rotate(2deg); box-shadow:0 6px 16px {{black@0.45}}; animation:er-pop .45s cubic-bezier(.2,1.3,.4,1) 1.3s backwards;
  max-width:min(320px, 92%); text-align:center; }
#er-conv .k { font-size:10.5px; color:{{red}}; font-weight:700; }
#er-conv .hand { font-size:16px; color:{{hand-ink}}; }

/* The reserved space, and the second warrant that fills it. */
/* The reserved slot's ink is the design's, at .9 rather than .6: at .6 it measured 2.7:1 on
   the cork, and a placeholder a reader cannot read is not a placeholder. */
#er-holder { position:absolute; left:78%; top:6%; width:19%; height:60%; border:2px dashed {{ink-warm@0.4}}; border-radius:3px; z-index:4;
  display:flex; align-items:center; justify-content:center; font-family: FONT_MONO; font-size:10.5px; letter-spacing:.16em;
  text-transform:uppercase; color:{{ink-warm@0.9}}; text-align:center; line-height:2; }
#er-holder span { font-size:10px; letter-spacing:.08em; }
#er-retrial { position:absolute; left:76.5%; top:4.5%; width:21%; background:{{cream}}; padding:16px 18px 14px; transform:rotate(1.2deg);
  box-shadow:0 10px 26px {{black@0.45}}; z-index:4; animation:er-pin2 .5s ease-out .2s backwards; }
#er-retrial .w-title { font-size:15px; letter-spacing:.1em; }
#er-retrial .tbl { background:{{paper}}; font-size:11px; }
#er-retrial .line { font-size:14px; line-height:1.5; }

/* The chain-of-custody tag. */
#er-tag { position:absolute; left:29%; top:84%; width:13%; background:{{tag}}; border:1px solid {{tag-line}}; padding:8px 12px;
  transform:rotate(-2.5deg); box-shadow:0 5px 12px {{black@0.4}}; z-index:4; border-radius:2px; }
#er-tag .k { color:{{kraft-ink-soft}}; letter-spacing:.1em; line-height:1.7; }

/* Below 1000px the design stacks every item into one column — its `_layout()`, as CSS. */
@media (max-width: 999px) {
  #er-frame { height:auto; min-height:0; }
  #er-board { height:auto; padding:4px 10px 20px; overflow:visible; }
  #er-fixtures, #er-cone-a, #er-cone-b, #er-holder { display:none; }
  #er-claim, #er-warrant, #er-reason, #er-bag, #er-strip, #er-conv, #er-retrial, #er-tag {
    position:relative; left:auto; top:auto; right:auto; bottom:auto; width:min(540px,100%); margin:18px auto 0; }
  #er-claim { width:min(480px,100%); transform:rotate(-1deg); }
  #er-warrant { transform:rotate(.5deg); }
  #er-reason { transform:none; }
  #er-bag { width:min(320px,88%); }
  #er-strip { transform:rotate(-1deg); }
  #er-conv { width:fit-content; max-width:min(320px,100%); transform:rotate(1.5deg); }
  #er-retrial { transform:rotate(.8deg); }
  #er-tag { width:fit-content; max-width:min(340px,100%); transform:rotate(-1.5deg); }
}
"""
BOARD_CSS = (
    BOARD_CSS.replace("FONT_BODY", FONTS["body"])
    .replace("FONT_MONO", FONTS["mono"])
    .replace("FONT_TYPE", FONTS["type"])
    .replace("FONT_HAND", FONTS["hand"])
)
