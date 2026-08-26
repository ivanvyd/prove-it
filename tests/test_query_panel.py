"""The annotated query panel, checked on the markup a browser is actually served.

This file exists because of a test that could not fail. `test_app_flow`'s check that "the
query is on screen" string-matched the frame's whole `srcdoc`, and the panel used to build
its contents from JavaScript — so the SQL matched inside an un-executed `<script>` whether
or not a browser would ever paint it. The assertions here look only at the markup outside
the script, which is what a reader gets when script does not run.
"""

from __future__ import annotations

import html
import re

from prove_it.ui.query_panel import panel_height, render_query_panel

SPREAD = (
    "SELECT `gender`, COUNT(*) AS students, AVG(`maths_score`) AS avg_score, "
    "STDDEV(`maths_score`) AS spread FROM `workspace`.`prove_it`.`student_scores` "
    "WHERE `gender` IS NOT NULL GROUP BY `gender`"
)


def markup_only(rendered: str) -> str:
    """Everything before the script block: what a script-blocked browser gets."""
    return rendered.split("<script>")[0]


def pre_text(rendered: str) -> str:
    """The query as it would be read off the page, tags stripped."""
    inner = re.search(r"<pre[^>]*>(.*?)</pre>", rendered, re.S)
    assert inner, "the panel rendered no <pre>"
    return html.unescape(re.sub(r"<[^>]+>", "", inner.group(1)))


def test_a_refused_turn_renders_no_panel() -> None:
    """A turn with no query must not get a box captioned "the query Genie wrote"."""
    for empty in (None, "", "   "):
        assert render_query_panel(empty) == ""


def test_the_query_is_in_the_markup_not_only_in_the_script() -> None:
    """The screen whose whole job is "read the query before you bet" must not depend on JS.

    The panel used to ship an empty `<pre>` filled in by script. Anywhere that script did
    not run — a stricter frame CSP, a filtering proxy, a managed classroom browser — the
    player got a blank box and no error explaining it.
    """
    body = markup_only(render_query_panel(SPREAD))
    assert "student_scores" in body
    assert "STDDEV" in body
    assert "The query Genie wrote" in body, "the label is server-rendered too"


def test_the_rendered_query_is_genie_s_own_text_character_for_character() -> None:
    """Annotating must not paraphrase, reorder or drop any of the query."""
    assert pre_text(render_query_panel(SPREAD)) == SPREAD


def test_the_explainable_parts_are_reachable_without_script() -> None:
    """Focusability and the accessible name are attributes, not behaviour added later."""
    body = markup_only(render_query_panel(SPREAD))
    assert body.count('class="qp-tok"') >= 3
    assert body.count('tabindex="0"') >= 3
    assert 'role="button"' in body
    assert "aria-label=" in body
    assert 'aria-live="polite"' in body


def test_the_copy_control_is_named_for_a_screen_reader() -> None:
    body = markup_only(render_query_panel(SPREAD))
    assert 'aria-label="Copy this query to the clipboard"' in body


def test_genie_s_sql_cannot_smuggle_markup_into_the_panel() -> None:
    """Column names arrive from Genie's rows, which this app does not control."""
    hostile = render_query_panel("SELECT `<img src=x onerror=alert(1)>` FROM `t`")
    assert "<img src=x" not in hostile
    assert "&lt;img" in hostile


def test_the_height_floor_grows_with_the_query() -> None:
    """The frame corrects itself once it can measure, but the first paint should not jump."""
    assert panel_height(None) == panel_height("")
    assert panel_height(SPREAD) > panel_height("SELECT 1")
