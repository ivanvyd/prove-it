"""The verdict slam: the flip as a beat, and the rules that keep it honest.

The theatre must never outrun the arithmetic. Every visual decision here — whether the
world freezes, how hard it shakes, whether a trick's name appears — is derived from the
two verdicts and the settlement, never chosen by the case.
"""

from __future__ import annotations

import json

from prove_it.domain.game import Award, Outcome, Settlement
from prove_it.domain.verdict import Verdict
from prove_it.ui.verdict_slam import render_slam


def payload_of(html: str) -> dict:
    return json.loads(html[html.index("var D = ") + 8 : html.index(";\n  var root")])


def slam(**overrides) -> str:
    base = dict(
        first=Verdict.HOLDS,
        second=Verdict.BUSTED,
        trick="Simpson's paradox",
        follow_up="break that down by department",
        added=["`department`,", "GROUP BY `department`, `gender`"],
        settlement=Settlement(Outcome.RIGHT, (Award("Called it x certain", 300),), 1),
        stake_label="Certain",
        points_before=0,
        points_after=3,
    )
    base.update(overrides)
    return render_slam(**base)


def test_a_bust_freezes_longest_and_shakes_hardest() -> None:
    d = payload_of(slam())
    assert d["flipped"] is True
    assert d["hitstop"] == 900
    assert d["shake"] == "large"


def test_half_true_freezes_less_and_shakes_less() -> None:
    d = payload_of(slam(second=Verdict.HALF_TRUE))
    assert 0 < d["hitstop"] < 900
    assert d["shake"] == "medium"


def test_a_verdict_that_did_not_flip_gets_no_freeze_and_no_shake() -> None:
    """The surviving case still gets its objection and its stamp; it earns no drama."""
    d = payload_of(
        slam(
            second=Verdict.HOLDS,
            settlement=Settlement(Outcome.WRONG, (Award("Missed x certain", -300),), 0),
        )
    )
    assert d["flipped"] is False
    assert d["hitstop"] == 0
    assert d["shake"] == "none"


def test_the_chips_count_from_before_to_after() -> None:
    d = payload_of(slam(points_before=4, points_after=7))
    assert (d["chipsBefore"], d["chipsAfter"]) == (4, 7)
    assert d["payout"]["tone"] == "win"
    assert "certain" in d["payout"]["text"]


def test_a_wrong_call_is_said_plainly() -> None:
    d = payload_of(
        slam(settlement=Settlement(Outcome.WRONG, (Award("Missed x certain", -300),), 0))
    )
    assert d["payout"]["tone"] == "loss"
    assert "Not this time" in d["payout"]["text"]


def test_no_call_means_no_payout_row() -> None:
    d = payload_of(slam(settlement=None, stake_label=None))
    assert d["payout"] is None


def test_the_trick_is_named_only_when_there_is_one() -> None:
    assert payload_of(slam())["trick"] == "Simpson's paradox"
    assert payload_of(slam(trick=None))["trick"] == ""


def test_diff_debris_does_not_become_a_chip() -> None:
    """The token diff hands over runs like "department`, `" — right for highlighting
    inside the SQL, wrong on a chip. Seen on a live screen as its own fragment."""
    d = payload_of(
        slam(
            added=[
                "`department`,",
                "department`, `",
                "`, `",
                "ORDER BY `department`",
                "`department`,",
            ]
        )
    )
    assert d["fragments"] == ["department", "ORDER BY `department"]


def test_fragments_are_capped_and_trimmed() -> None:
    d = payload_of(slam(added=[f"col_{i} " + "x" * 100 for i in range(9)] + ["   "]))
    assert len(d["fragments"]) == 4
    assert all(len(f) <= 42 for f in d["fragments"])


def test_the_payload_cannot_close_the_script_block() -> None:
    """Fragments and the trick come from Genie's rows and the docket."""
    html = slam(added=["</script><script>alert(1)</script>"], trick="<b>x</b>")
    payload = html[html.index("var D = ") + 8 : html.index(";\n  var root")]
    assert "</script>" not in payload
    assert "<" not in payload
    assert html.count("<script>") == 1


def test_the_timeline_is_seekable_and_pure() -> None:
    """The recorder steps the flip frame by frame; the picture at t must depend on t alone."""
    html = slam()
    assert "window.__seek = function" in html
    assert "window.__total" in html
    assert "function apply(t)" in html
    assert "setTimeout" not in html and "setInterval" not in html
    # The first seek must stop the autoplay loop, or the loop overwrites the frame the
    # recorder asked for a few milliseconds later — which it did, on the first try.
    assert "seeking = true" in html
    assert "if (seeking) return" in html


def test_reduced_motion_jumps_to_the_end() -> None:
    assert "prefers-reduced-motion" in slam()


def test_the_scroll_marker_matches_the_markup_it_looks_for() -> None:
    """`app.py` scrolls to the flip by searching frames for this marker.

    Nothing else ties the two together: renaming the root class reads as cosmetic from
    inside this file, and the scroll would then search for something that no longer exists,
    exhaust its retries and silently do nothing — on the beat the whole case pays for.
    """
    from prove_it.ui.verdict_slam import SLAM_MARKER

    markup = render_slam(
        first=Verdict.HOLDS,
        second=Verdict.BUSTED,
        trick="The hidden spread",
        follow_up="show the spread too",
        added=["STDDEV(`maths_score`) AS spread"],
        settlement=None,
        stake_label=None,
        points_before=0,
        points_after=500,
    )
    assert SLAM_MARKER in markup
