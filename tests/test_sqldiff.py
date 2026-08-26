"""The v1/v2 diff is the screenshot the project is built around, so it gets tests."""

import html
import re

from prove_it.domain.sqldiff import Change, added_count, diff_sql, diff_tokens
from prove_it.genie.fake import DEMO_FIRST, DEMO_SECOND
from prove_it.ui.render import render_sql


def test_rendered_sql_is_byte_identical_to_what_genie_wrote() -> None:
    """R2. The app displays Genie's query verbatim — no truncation, no reformatting.

    Substring assertions elsewhere would survive a change that silently normalised
    whitespace or trimmed long queries, which would quietly break the guarantee the whole
    product rests on.
    """
    for sql in (DEMO_FIRST.sql, DEMO_SECOND.sql):
        rendered = render_sql(sql)
        inner = re.sub(r"^<div class=\"pi-sql\">|</div>$", "", rendered)
        assert html.unescape(inner) == sql


REAL_V1 = (
    "SELECT `gender`, AVG(`maths_score`) AS avg_maths_score FROM "
    "`workspace`.`prove_it`.`student_scores` WHERE `gender` IS NOT NULL AND "
    "`maths_score` IS NOT NULL GROUP BY `gender`"
)
REAL_V2 = (
    "SELECT `gender`, COUNT(*) AS students, AVG(`maths_score`) AS avg_maths_score, "
    "STDDEV(`maths_score`) AS spread FROM `workspace`.`prove_it`.`student_scores` "
    "WHERE `gender` IS NOT NULL AND `maths_score` IS NOT NULL GROUP BY `gender`"
)


def test_single_line_genie_sql_still_highlights_only_the_new_columns() -> None:
    """The defect that mattered most, caught only by replaying a real recording.

    Genie emits a query as one long line. A line-level diff called the whole statement
    removed-and-re-added, so the two new columns — the entire point of the screen — never
    appeared as additions.
    """
    added = "".join(s.text for s in diff_tokens(REAL_V1, REAL_V2) if s.change is Change.ADDED)

    assert "COUNT(*) AS students" in added
    assert "STDDEV" in added and "spread" in added
    # The parts that did not change must not be marked as new.
    assert "avg_maths_score" not in added.replace("AS avg_maths_score,", "")
    assert "student_scores" not in added


def test_a_token_diff_reassembles_into_exactly_what_genie_wrote() -> None:
    """R2 again: highlighting must not alter the query."""
    rebuilt = "".join(
        s.text for s in diff_tokens(REAL_V1, REAL_V2) if s.change is not Change.REMOVED
    )
    assert rebuilt == REAL_V2


def test_the_rendered_diff_marks_additions_inline() -> None:
    from prove_it.ui.render import render_diff

    rendered = render_diff(REAL_V1, REAL_V2)
    assert '<mark class="add">' in rendered
    assert "student_scoresGROUP" not in rendered


def test_rendering_a_query_with_html_in_it_escapes_rather_than_injects() -> None:
    hostile = "SELECT '<img src=x onerror=alert(1)>' AS x"
    rendered = render_sql(hostile)
    assert "<img" not in rendered
    assert "&lt;img" in rendered


def texts(lines, change):
    return [line.text.strip() for line in lines if line.change is change]


def test_the_repair_shows_up_as_two_added_lines() -> None:
    lines = diff_sql(DEMO_FIRST.sql, DEMO_SECOND.sql)
    added = texts(lines, Change.ADDED)

    assert added_count(lines) == 2
    assert any("COUNT(*)" in line for line in added)
    assert any("STDDEV" in line for line in added)


def test_unchanged_lines_are_kept_so_the_query_still_reads_as_a_query() -> None:
    lines = diff_sql(DEMO_FIRST.sql, DEMO_SECOND.sql)
    same = texts(lines, Change.SAME)

    assert "SELECT gender," in same
    assert "GROUP BY gender" in same


def test_a_changed_line_shows_as_removed_then_added() -> None:
    lines = diff_sql("SELECT a\nFROM t", "SELECT b\nFROM t")
    assert texts(lines, Change.REMOVED) == ["SELECT a"]
    assert texts(lines, Change.ADDED) == ["SELECT b"]


def test_missing_sql_on_either_side_is_survivable() -> None:
    """Genie can return no query at all; the diff must not be the thing that crashes."""
    assert diff_sql(None, None) == []
    assert added_count(diff_sql(None, "SELECT 1")) == 1
    assert texts(diff_sql("SELECT 1", None), Change.REMOVED) == ["SELECT 1"]


def test_indentation_is_preserved_because_the_child_is_reading_it() -> None:
    lines = diff_sql("SELECT a,\n       b\nFROM t", "SELECT a,\n       b,\n       c\nFROM t")
    added = [line.text for line in lines if line.change is Change.ADDED]
    assert added == ["       c"]
