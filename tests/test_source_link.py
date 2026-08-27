"""The masthead's link to the source.

Worth its own file because the link is not decoration. The app's central claim is that it
never writes a line of SQL, and the only way anyone can check that is to read the code —
so a link that points at the wrong repository, or silently disappears, takes the evidence
for the claim with it.
"""

from __future__ import annotations

import re

import pytest

from prove_it.config import Settings
from prove_it.domain.game import RANKS
from prove_it.ui.render import source_link


def test_renders_the_configured_url() -> None:
    markup = source_link("https://github.com/example/thing")
    assert 'href="https://github.com/example/thing"' in markup


def test_no_url_renders_nothing() -> None:
    """A fork that clears the setting gets no link, not a link to someone else's repo.

    Whitespace counts as empty: a `PROVE_IT_SOURCE_URL=" "` in a deployment config is
    someone switching it off, and an anchor wrapping a blank href is a dead control.
    """
    assert source_link("") == ""
    assert source_link("   ") == ""


def test_the_default_points_at_this_project() -> None:
    assert Settings.source_url == "https://github.com/ivanvyd/prove-it"


def test_opens_out_of_the_app_without_handing_over_the_page() -> None:
    """`target="_blank"` alone gives the opened page a handle back to this one.

    It matters more here than on most pages: losing an in-progress case to a navigation
    would cost the player the stake they have already committed.
    """
    markup = source_link("https://github.com/example/thing")
    assert 'target="_blank"' in markup
    assert "noopener" in markup


def test_the_link_is_named_for_a_screen_reader() -> None:
    """The visible word is hidden below 720px, and `display:none` takes it out of the
    accessibility tree too — so the name has to live on the anchor itself."""
    markup = source_link("https://github.com/example/thing")
    assert 'aria-label="Read the source on GitHub"' in markup


def test_a_hostile_url_cannot_break_out_of_the_attribute() -> None:
    markup = source_link('https://x.test/"><script>alert(1)</script>')
    assert "<script>" not in markup
    assert "&quot;" in markup or "&#x27;" in markup


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(document.cookie)",
        "JavaScript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "github.com/example/thing",
    ],
)
def test_only_http_urls_become_a_link(url: str) -> None:
    """Escaping the value and vetting the scheme are two different jobs.

    `html.escape` stops a URL breaking out of the attribute and has nothing to say about
    `javascript:`, which would render as a live control on every screen of the app. The
    earlier version of this file tested only the breakout and passed while the scheme went
    unchecked. A scheme-less string is refused too: it would resolve against the app's own
    origin rather than reaching the repository.
    """
    assert source_link(url) == ""


def test_no_rank_title_is_long_enough_to_clip_the_masthead() -> None:
    """The masthead is one 56px row that clips rather than wraps, and the rank plate is the
    widest thing on it — so the length of these four strings is what decides whether the bar
    fits.

    It has now overflowed three times: once taking the rank plate off screen at 375px, once
    at 768px when the source link was added, and once at 320px. Each was fixed by shedding or
    tightening something at a breakpoint, which is a fix that holds only while the titles stay
    this length. A browser is what actually measures the bar, and the suite has none — this
    guards the input that drives it instead. `FIELD INVESTIGATOR` is 18 characters and
    measured 155px in the fallback mono; the breakpoints were tuned against exactly that.
    """
    longest = max(RANKS, key=lambda r: len(r.title))
    assert len(longest.title) <= 18, (
        f"{longest.title!r} is longer than the masthead was measured against; re-check the "
        f"bar at 320, 375, 768 and 861px before raising this bound"
    )


def test_the_mark_is_drawn_not_fetched() -> None:
    """The product makes no external requests. An icon font or a remote SVG would be one
    on every render, and Free Edition's allowlist would block it besides."""
    markup = source_link("https://github.com/example/thing")
    assert "<svg" in markup
    assert not re.search(r"<(img|use)\b|https?://(?!github\.com/example)", markup)
