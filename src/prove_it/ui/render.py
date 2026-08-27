"""Small renderers: markup fragments and single Streamlit elements.

These turn one value into one piece of page — a chip, a ledger, a table — and none of
them decides anything. Everything that decides lives in `domain/` where a test can reach
it without a browser.

The two that carry real risk are here together on purpose: `provenance_panel` and
`source_link` render strings the app does not control into markdown with HTML enabled, so
every value they interpolate is escaped.
"""

from __future__ import annotations

import html
import json
import math

import streamlit as st

from prove_it.domain.custody import custody_of, same_conversation
from prove_it.domain.estimate import score_estimate, verdict_gap
from prove_it.domain.exhibits import Exhibit
from prove_it.domain.verdict import ResultTable, Verdict, is_rate_column
from prove_it.session import Investigation
from prove_it.ui.style import VERDICT_TEXT


def verdict_chip(verdict: Verdict, *, arrive: bool = False) -> str:
    """`arrive` plays the chip in with the stamp's overshoot — used where the verdict is
    the thing that has just been unsealed."""
    label, css = VERDICT_TEXT[verdict]
    extra = " pi-verdict--arrive" if arrive else ""
    return f'<span class="pi-verdict {css}{extra}">{label}</span>'


def bring_into_view() -> None:
    """Scroll the page to the top after a change of scene.

    Streamlit keeps the scroll position across a rerun, which is right for a widget change
    and wrong for a navigation: a player who clicked a folder halfway down the archive
    landed halfway down the board. The scroll container is Streamlit's block container, not
    the document, so this is a one-pixel frame reaching up into the parent to move it.
    """
    st.iframe(
        "<script>(function () {"
        "  var d = window.parent.document;"
        "  ['[data-testid=\"stMainBlockContainer\"]', 'section.stMain']"
        "    .map(function (s) { return d.querySelector(s); })"
        "    .filter(Boolean).forEach(function (s) { s.scrollTop = 0; });"
        "  window.parent.scrollTo(0, 0);"
        # The archive's leaving-animation classes. Streamlit keeps the container node
        # across reruns, so what a click added is still there when the next scene lands.
        "  d.querySelectorAll('.is-leaving, .is-opening').forEach(function (e) {"
        "    e.classList.remove('is-leaving', 'is-opening'); });"
        "})();</script>",
        # One pixel, not none: `st.iframe` rejects a height of zero. The container is
        # hidden in CSS, so the pixel never reaches the page.
        height=1,
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
    unit = html.escape(spec.unit)
    verdict_word = html.escape(result.label)
    reward = f" <b>+{result.points}</b>" if result.points else ""
    return (
        '<div class="pi-est">'
        '<div class="pi-est-rule">'
        f'<span class="pi-est-truth" style="left:{truth:.2f}%"></span>'
        f'<span class="pi-est-you" style="left:{you:.2f}%"></span>'
        "</div>"
        f'<div class="pi-est-read">You said <b>{inv.guess:.1f}{unit}</b> · '
        f"it is <b>{actual:.1f}{unit}</b> — {verdict_word}{reward}</div>"
        "</div>"
    )


def source_link(url: str) -> str:
    """The link to the source, or nothing when no source is configured.

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
    # blunt and worth more kept that way than the two lines it costs here.
    scheme, _, _ = url.strip().partition(":")
    if scheme.lower() not in {"http", "https"}:
        return ""
    return (
        f'<a class="pi-mast-src" href="{html.escape(url, quote=True)}" target="_blank" '
        f'rel="noopener noreferrer" aria-label="Read the source on GitHub">'
        # The GitHub mark, inline rather than fetched. The path is the design file's own,
        # copied rather than retyped: an earlier attempt to reproduce it from memory
        # rendered a crescent, which is what a 700-character bezier does to a guess.
        f'<svg width="19" height="19" viewBox="0 0 16 16" fill="currentColor" '
        f'aria-hidden="true" focusable="false"><path d="{OCTOCAT}"/></svg></a>'
    )


OCTOCAT = (
    "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-"
    "1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 "
    "1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
    "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36"
    ".09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-"
    "1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 "
    "0 0 0 16 8c0-4.42-3.58-8-8-8z"
)


def provenance_panel(inv: Investigation) -> str:
    """Judge-facing chrome: the full identifiers, and what they do and do not prove.

    Deliberately not placed anywhere near the child's decision. A ten-year-old has no use
    for a 32-character handle, and the one screen this must never crowd is the sealed one.
    """
    rows = []
    for label, turn in (("v1", inv.first), ("v2", inv.second)):
        # The table's first column is "Query", so a turn that produced none does not get
        # a row claiming otherwise.
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


__all__ = [
    "bring_into_view",
    "estimate_line",
    "for_display",
    "provenance_panel",
    "render_exhibits",
    "render_table",
    "source_link",
    "verdict_chip",
]

_ = json  # `json` stays imported for `script_json` callers that used to live here.
