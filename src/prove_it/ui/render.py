"""Small renderers: markup fragments and single Streamlit elements.

Split from `app.py` at the same time as the stylesheet, and along the same seam the file
already had. These turn one value into one piece of page — a chip, a panel, a table — and
none of them decides anything. Everything that decides lives in `domain/` where a test can
reach it without a browser.

The three that carry real risk are here together on purpose: `seal_panel`, `custody_line`
and `provenance_panel` all render Genie-supplied strings into markdown with HTML enabled,
so every value they interpolate is escaped.
"""

from __future__ import annotations

import html
import json
import math

import streamlit as st

from prove_it.domain.custody import custody_of, same_conversation
from prove_it.domain.estimate import score_estimate, verdict_gap
from prove_it.domain.exhibits import Exhibit
from prove_it.domain.game import Outcome, Run, Settlement, rank_for
from prove_it.domain.sqldiff import Change, diff_tokens
from prove_it.domain.verdict import ResultTable, Verdict, is_rate_column
from prove_it.genie.models import Turn
from prove_it.session import Investigation
from prove_it.ui.style import VERDICT_TEXT

# -- small renderers ----------------------------------------------------------------


def verdict_chip(verdict: Verdict, *, arrive: bool = False) -> str:
    """`arrive` plays the chip in with the stamp's overshoot — used once, at the reveal,
    where the verdict is the thing that has just been unsealed."""
    label, css = VERDICT_TEXT[verdict]
    extra = " pi-verdict--arrive" if arrive else ""
    return f'<span class="pi-verdict {css}{extra}">{label}</span>'


def bring_into_view(marker: str | None = None) -> None:
    """Scroll the page to the top, or to the first inline frame whose markup contains
    `marker`, after a change of screen.

    Streamlit keeps the scroll position across a rerun, which is right for a widget change
    and wrong for a navigation. A player who clicked a folder halfway down the docket landed
    halfway down the case screen; one who locked a call landed below the seal breaking; and
    one who cross-examined landed a screen *past* the verdict slam, which then played to
    nobody. The scroll container is Streamlit's block container, not the document, so this
    is a zero-height frame reaching up into the parent to move it. The marker search retries
    briefly because the frame it looks for may still be mounting.
    """
    target = json.dumps(marker)
    st.iframe(
        "<script>"
        "(function () {"
        "  var marker = " + target + ";"
        "  var d = window.parent.document;"
        "  var scrollers = ['[data-testid=\"stMainBlockContainer\"]', 'section.stMain']"
        "    .map(function (s) { return d.querySelector(s); }).filter(Boolean);"
        "  if (!marker) {"
        "    scrollers.forEach(function (s) { s.scrollTop = 0; });"
        "    window.parent.scrollTo(0, 0);"
        "    return;"
        "  }"
        "  var tries = 0;"
        "  (function go() {"
        "    var frames = Array.prototype.slice.call(d.querySelectorAll('iframe'));"
        "    var f = frames.filter(function (x) {"
        "      return (x.getAttribute('srcdoc') || '').indexOf(marker) !== -1; })[0];"
        "    if (!f) { if (tries++ < 60) setTimeout(go, 50); return; }"
        "    var s = scrollers.filter(function (x) { return x.scrollHeight > x.clientHeight; })[0];"
        "    if (!s) { f.scrollIntoView({ block: 'start' }); return; }"
        "    var y = f.getBoundingClientRect().top - s.getBoundingClientRect().top + s.scrollTop;"
        "    s.scrollTo({ top: Math.max(0, y - 24), behavior: 'smooth' });"
        "  })();"
        "})();"
        "</script>",
        # One pixel, not none: `st.iframe` rejects a height of zero. The container is
        # hidden in CSS, so the pixel never reaches the page.
        height=1,
    )


CASE_STEPS = 5


def step_rail(current: int, label: str) -> str:
    """Where you are in the case, drawn rather than only named.

    "Step 2 of 5" was 10.5px uppercase mono — the smallest text on the screen. In a game
    the progress signal should be among the largest, and for the age this is built for it
    is most of what keeps a player going: a five-segment rail fills as the case proceeds,
    so the end is visible from the start and each beat is a segment earned.

    The count is announced once, for a screen reader, and the segments themselves are
    decoration — repeating "step, step, step" would be noise.
    """
    segments = "".join(
        f'<span class="pi-rail-seg{" is-done" if n < current else ""}'
        f'{" is-now" if n == current else ""}"></span>'
        for n in range(1, CASE_STEPS + 1)
    )
    announced = f"Step {current} of {CASE_STEPS}: {html.escape(label)}"
    return (
        f'<div class="pi-rail" role="group" aria-label="{announced}">'
        f'<span class="pi-rail-track" aria-hidden="true">{segments}</span>'
        f'<span class="pi-rail-label">{html.escape(label)}</span>'
        f"</div>"
    )


def render_sql(sql: str | None) -> str:
    return f'<div class="pi-sql">{html.escape(sql or "")}</div>'


def seal_panel(
    *, opened: bool, tag: str | None, question: str | None = None, wager: str | None = None
) -> str:
    """The sealed result, as an object rather than an absence.

    Both states render from here so the locked and open poses line up exactly — the demo
    cuts between them, and a cut only reads as an unlock when nothing but the lock moves.

    `tag` is Genie's real attachment id, which is precisely the handle the app is holding
    and refusing to spend until the child has committed. Printing it makes the seal a
    picture of a fact instead of a decorative padlock.
    """
    lock = "🔓" if opened else "🔒"
    label = "Seal broken" if opened else "Result sealed"
    tag_line = (
        f'<div class="pi-tag">Evidence tag&nbsp; <b>{html.escape(tag)}</b></div>' if tag else ""
    )
    # The same blocked-out digits in both states, struck through once the seal is open.
    # Keeping the element identical is what lets the demo cut between the two stills; the
    # strike is what stops an opened seal reading as though it were still hiding the
    # number that is now sitting directly beneath it.
    # Decoration, and hidden from assistive technology on purpose: a screen reader reading
    # "black-square black-square" tells a listener nothing, and the label beside it already
    # says the result is sealed.
    blocks = '<div class="blocks" aria-hidden="true">▚▚▚.▚</div>'
    prompt = (
        f'<div class="q">{question}</div>'
        if question
        else ('<div class="q">The result is below.</div>' if opened else "")
    )
    # The wager, printed on the seal once it is open: the same object the player was
    # staring at, now carrying what they put on it. It is what makes the reveal read as
    # a bet being settled rather than a number arriving.
    wager_line = f'<div class="wager">{html.escape(wager)}</div>' if wager else ""
    return (
        f'<div class="pi-seal{" pi-seal--open" if opened else ""}">'
        f'<div class="k">{lock} {label}</div>'
        f"{blocks}{prompt}{wager_line}{tag_line}</div>"
    )


def custody_line(turn: Turn | None, *, continues: bool = False) -> str:
    """One query's provenance, in Genie's own identifiers.

    `continues` marks the follow-up as having stayed inside the first query's
    conversation. That is the multi-turn claim made checkable: it is the difference
    between Genie remembering what was asked and a template being run twice.

    Renders nothing when Genie wrote no query. This line attributes *a query*, and a
    refused follow-up has none — it reached Stage.REPAIRED with `has_query` false, and
    stamping "written by Genie" under it would put a false provenance claim on screen.
    A wrong authorship statement is worse here than an absent one, because the whole
    point of the line is that it can be checked.
    """
    record = custody_of(turn)
    if record is None or turn is None or not turn.has_query:
        return ""
    conversation = html.escape(record.short_conversation)
    message = html.escape(record.short_message)
    marker = '<span class="same">same conversation as query v1</span><br>' if continues else ""
    return (
        f'<div class="pi-custody">{marker}'
        f"written by Genie · conversation {conversation}… · message {message}…</div>"
    )


def call_line(inv: Investigation) -> str:
    """The player's call, standing. Shown at the naive reveal, where a "trick" call looks
    lost and a "holds up" call looks won — and neither is settled yet."""
    call, stake = inv.call, inv.stake
    if call is None or stake is None:
        return ""
    standing = " The cross-examination decides." if inv.can_repair else ""
    return (
        f'<div class="pi-call">Your call: <b>{html.escape(call.value)}</b> · '
        f"staked {html.escape(stake.label.lower())} (×{stake.multiplier}).{standing}</div>"
    )


def estimate_line(inv: Investigation) -> str:
    """The player's mark laid over the real gap, drawn to scale.

    A number beside a number is a comparison a reader has to do themselves. The whole
    reason this mechanic works — Kim, Reinecke & Hullman, CHI 2017 — is that the distance
    between the belief and the data is *shown*, so the surprise belongs to the person who
    guessed rather than to the person who wrote the caption.

    Both marks sit on the same ruler the player was given, which is what makes the two
    positions mean anything. Escaped throughout: nothing here comes from Genie, but the
    labels come from the case file and this function has no business trusting its inputs
    more than its neighbours do.
    """
    if inv.guess is None or inv.case is None or inv.case.estimate is None:
        return ""
    actual = verdict_gap(inv.first_analysis.delta if inv.first_analysis else None)
    if actual is None:
        return ""

    spec = inv.case.estimate
    result = score_estimate(inv.guess, actual, spec)
    you, truth = spec.fraction_of(inv.guess) * 100, spec.fraction_of(actual) * 100
    tone = "hit" if result.landed else "miss"
    unit = html.escape(spec.unit)
    verdict_word = html.escape(result.label)
    reward = f" <b>+{result.points}</b>" if result.points else ""
    return (
        f'<div class="pi-est pi-est--{tone}">'
        f'<div class="pi-est-rule">'
        f'<span class="pi-est-truth" style="left:{truth:.2f}%"></span>'
        f'<span class="pi-est-you" style="left:{you:.2f}%"></span>'
        f"</div>"
        f'<div class="pi-est-read">You said <b>{inv.guess:.1f}{unit}</b> · '
        f"it is <b>{actual:.1f}{unit}</b> — {verdict_word}{reward}</div>"
        f"</div>"
    )


def payout_line(inv: Investigation, settlement: Settlement) -> str:
    """The payout chit: every award named and totalled, the way the design's torn slip
    shows its working rather than handing over one opaque number."""
    if inv.stake is None:
        return ""
    if settlement.outcome is Outcome.VOID:
        return (
            '<div class="pi-payout pi-payout--void">'
            "The data could not rule on that — nothing scored, nothing lost.</div>"
        )
    tone = "win" if settlement.outcome is Outcome.RIGHT else "loss"
    lines = " · ".join(f"{html.escape(a.label)} {a.points:+d}" for a in settlement.awards)
    return f'<div class="pi-payout pi-payout--{tone}">{lines} <b>= {settlement.points:+d}</b></div>'


def hud(run: Run, total_cases: int) -> str:
    """The run, read off the masthead: docket progress, chips, streak, and the rank plate.

    Ordered the way the design's chrome bar reads it — progress first, then the score, then
    the title you currently hold.
    """
    streak = (
        f'<span class="pi-hud-streak is-on">STREAK {run.streak}</span>' if run.streak >= 3 else ""
    )
    rank = rank_for(run.points)
    return (
        f'<span class="pi-hud">'
        f'<span class="pi-hud-docket">DOCKET <b>{run.cases_called}/{total_cases}</b></span>'
        f'<span>PTS <span class="pi-hud-chips">{run.points}</span></span>'
        f"{streak}"
        f'<span class="pi-hud-rank">{html.escape(rank.title.upper())}</span>'
        f"</span>"
    )


def source_link(url: str) -> str:
    """The masthead's link to the source, or nothing when no source is configured.

    The app's central claim — that it never writes a line of SQL — is only checkable by
    reading the code, so this link is part of the argument rather than a courtesy. It opens
    in a new tab because losing an in-progress case to a navigation would cost the player
    their stake, and `rel` is set because `target="_blank"` otherwise hands the opened page
    a handle back to this one.
    """
    # Escaping the value is not the same as trusting the scheme. `html.escape` stops a URL
    # breaking out of the attribute and does nothing about `javascript:`, which renders as a
    # live control on every screen of the app — so the scheme is checked here rather than
    # left to the escaping to imply. Anything that is not plain http(s) is treated exactly
    # like an empty setting: no link, rather than a link nobody vetted. A URL with no scheme
    # is refused too, because it would resolve against the app's own origin rather than
    # reaching a repository.
    #
    # Split by hand rather than with the standard library's URL parser, whose module name
    # `tests/test_product_rules.py` rejects anywhere in the app. That guard is deliberately
    # blunt and worth more kept that way than the two lines it costs here: it is what checks
    # this app never fetches anything, which is most of what makes its claims verifiable.
    scheme, _, _ = url.strip().partition(":")
    if scheme.lower() not in {"http", "https"}:
        return ""
    return (
        f'<a class="pi-mast-src" href="{html.escape(url, quote=True)}" target="_blank" '
        # Named on the anchor rather than by its text, because the narrow-viewport rule
        # hides that text — and `display:none` takes it out of the accessibility tree as
        # well as off the screen, which would leave the link announced as just its URL.
        f'rel="noopener noreferrer" aria-label="Read the source on GitHub">'
        # Drawn inline rather than fetched: the product makes no external requests, and an
        # icon font or a remote mark would be one on every render.
        #
        # A source-code mark rather than the GitHub octocat. The octocat is a single 700-
        # character bezier path, which is not something to reproduce from memory — the first
        # attempt rendered a crescent — and it is a trademark besides. Three straight strokes
        # say "the code" just as plainly and can be read for correctness straight off the
        # page: two chevrons and the slash between them.
        f'<svg viewBox="0 0 20 16" width="16" height="14" aria-hidden="true" focusable="false" '
        f'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">'
        f'<polyline points="6,4 2,8 6,12"/>'
        f'<polyline points="14,4 18,8 14,12"/>'
        f'<line x1="11.5" y1="2.5" x2="8.5" y2="13.5"/>'
        f"</svg>"
        f"<span>SOURCE</span></a>"
    )


def provenance_panel(inv: Investigation) -> str:
    """Judge-facing chrome: the full identifiers, and what they do and do not prove.

    Deliberately not placed anywhere near the child's decision. A ten-year-old has no use
    for a 32-character handle, and the one screen this must never crowd is the sealed one.
    """
    rows = []
    for label, turn in (("v1", inv.first), ("v2", inv.second)):
        # Same rule as `custody_line`: the table's first column is "Query", so a turn that
        # produced none does not get a row claiming otherwise.
        if turn is None or not turn.has_query:
            continue
        record = custody_of(turn)
        if record is None:
            continue
        rows.append(
            f"<tr><td>{label}</td><td>{html.escape(record.conversation_id)}</td>"
            f"<td>{html.escape(record.message_id)}</td></tr>"
        )
    if not rows:
        return ""

    # Continuity is only claimed when there are two *queries* to be continuous between.
    # A refused follow-up shares the conversation id but contributed no query, so the
    # table would list one row under a note about "both queries".
    both_wrote_queries = len(rows) == 2
    continued = both_wrote_queries and same_conversation(inv.first, inv.second)
    note = (
        "Both queries carry the same conversation id. The follow-up continued the "
        "exchange Genie was already in rather than starting a new one — that is what "
        "makes this a conversation and not a template run twice."
        if continued
        else "These ids can be looked up in the Genie space's own message history."
    )
    return (
        '<div class="pi-prov"><table>'
        "<tr><th>Query</th><th>Conversation</th><th>Message</th></tr>"
        f"{''.join(rows)}</table>"
        f'<div class="note">{note}</div></div>'
    )


def render_diff(
    before: str | None, after: str | None, exhibits: list[Exhibit] | None = None
) -> str:
    """Render the two queries as one diff.

    Highlights inline at token level rather than by line. Real Genie emits a query as one
    long line, so a line-based diff marked the whole statement as replaced and the two new
    columns — the entire point of this screen — never showed up as additions.
    """
    labels = {e.fragment: e.label for e in (exhibits or []) if e.fragment}
    rows = []
    for segment in diff_tokens(before, after):
        text = html.escape(segment.text)
        if segment.change is Change.ADDED:
            # Carry the exhibit letter into the highlight so the badge in the SQL, the
            # badge in the narration below and the column in the table are visibly the
            # same thing rather than three separate claims.
            label = next((v for k, v in labels.items() if k and k in segment.text), None)
            # Escaped for consistency with `render_exhibits` below, which escapes the same
            # field. `Exhibit.label` is currently always one letter from a fixed alphabet,
            # so nothing is reachable today — but this file's own docstring promises every
            # interpolated value is escaped, and an unescaped one makes that a lie the next
            # reader has to re-derive.
            badge = f'<b class="pi-ex">{html.escape(label)}</b>' if label else ""
            rows.append(f'<mark class="add">{badge}{text}</mark>')
        elif segment.change is Change.REMOVED:
            rows.append(f'<span class="del">{text}</span>')
        else:
            rows.append(f"<span>{text}</span>")
    return f'<div class="pi-sql">{"".join(rows)}</div>'


def render_exhibits(exhibits: list[Exhibit]) -> str:
    """The added columns, named, with what each one revealed.

    Staggered by CSS `animation-delay` rather than by reruns or `time.sleep`: the page is
    already rendered, so the choreography costs nothing, replays identically on every load,
    and a frozen screenshot still shows every line.
    """
    rows = []
    for i, exhibit in enumerate(exhibits):
        rows.append(
            f'<div class="pi-exhibit" style="animation-delay:{0.35 + i * 0.55:.2f}s">'
            f'<b class="pi-ex">{html.escape(exhibit.label)}</b>'
            f"<div><code>{html.escape(exhibit.alias)}</code> "
            f"{html.escape(exhibit.narration)}</div></div>"
        )
    return f'<div class="pi-exhibits">{"".join(rows)}</div>'


def render_thoughts(turn: Turn) -> None:
    steps = turn.ordered_thoughts
    if not steps:
        # The probe may show `thoughts` is empty on Free Edition. Falling back to the
        # one-line description keeps the panel honest instead of empty.
        if turn.description:
            st.markdown(
                f'<div class="pi-step"><div class="t">What it understood</div>'
                f'<div class="b">{html.escape(turn.description)}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Genie did not explain its working for this one.")
        return
    for step in steps:
        st.markdown(
            f'<div class="pi-step"><div class="t">{html.escape(step.label)}</div>'
            f'<div class="b">{html.escape(step.content)}</div></div>',
            unsafe_allow_html=True,
        )


def for_display(cell: object, column: str = "") -> object:
    """Round a returned number to something a reader can hold.

    Genie returns full float precision — 492.64332917705605 — and fifteen decimals is
    noise, especially next to prose that says "about 89". Integers and non-numbers pass
    through untouched, so counts stay counts.

    A rate is the exception, and it took a screenshot to notice. One decimal place turns
    Berkeley's 0.4451 and 0.3035 into 0.4 and 0.3, and department D's 0.331 against 0.349
    into 0.3 against 0.3 — so two of the four departments that reverse stop reversing on
    screen, in the one table the whole case rests on. Rates render as percentages, which is
    also how the verdict beside them is already worded.

    The 0..1 guard is what keeps `combined_expenditure_share_gdp` alone: it matches the
    rate test by name, but its values are percentages already (3.53, 5.43) and multiplying
    them by a hundred would invent a number.
    """
    if cell is None:
        return None
    text = str(cell).strip()
    try:
        value = float(text)
    except ValueError:
        return cell
    if not math.isfinite(value) or "." not in text:
        return cell
    if is_rate_column(column) and 0.0 <= value <= 1.0:
        return f"{value * 100:.1f}%"
    return f"{value:.1f}"


def render_table(table: ResultTable | None) -> None:
    if table is None or not table.rows:
        return
    st.dataframe(
        {
            col.name: [
                for_display(row[i], col.name) if i < len(row) else None for row in table.rows
            ]
            for i, col in enumerate(table.columns)
        },
        hide_index=True,
        width="stretch",
    )
