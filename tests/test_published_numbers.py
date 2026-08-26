"""The numbers in the prose have to be the numbers in the data.

The README claims the demo figures are "generated, not asserted" and cannot drift. That
claim was false when it was written: the README, the project story and the demo script all
hand-type the figures, and nothing read those files. This suite makes the claim true.

It matters more than it looks. `docs/project-story.md` is written for publication, and the
figures have already been wrong twice — once because the parameters handed to the random
generator were mistaken for the sample statistics it produces, and once because a
"verification" script drew the same values in a different order.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from prove_it.demo_data import OBSERVED, effect_size
from prove_it.genie.client import DEFAULT_TIMEOUT_SECONDS

ROOT = Path(__file__).resolve().parents[1]

# Every file that quotes the demo figures to a reader.
PUBLISHED = [
    ROOT / "README.md",
    ROOT / "docs" / "project-story.md",
    ROOT / "docs" / "demo-script.md",
]

# Values that were published at some point and are now wrong. If one reappears, a document
# has been reverted or copied from an old draft.
SUPERSEDED = ["494.2", "489.1", "92.6", "88.4", "486.9", "88.6", "5.1", "5.7"]


def documents() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in PUBLISHED if p.exists()]


def test_the_published_documents_exist() -> None:
    """Guards against the glob silently covering nothing."""
    assert len(documents()) == len(PUBLISHED)


@pytest.mark.parametrize("gender", sorted(OBSERVED))
def test_the_current_figures_appear_in_the_project_story(gender: str) -> None:
    """The story is the public artifact; its numbers must be the real ones."""
    story = (ROOT / "docs" / "project-story.md").read_text(encoding="utf-8")
    observed = OBSERVED[gender]

    assert str(observed.maths_mean) in story, f"{gender} mean missing from the story"
    assert str(observed.maths_sd) in story, f"{gender} spread missing from the story"


def test_the_headline_gap_is_stated_correctly() -> None:
    gap = round(abs(OBSERVED["boy"].maths_mean - OBSERVED["girl"].maths_mean), 1)
    story = (ROOT / "docs" / "project-story.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert str(gap) in story, f"the story should quote a gap of {gap}"
    assert str(gap) in readme, f"the README should quote a gap of {gap}"


def test_the_stated_effect_size_matches_the_data() -> None:
    published = f"{effect_size():.2f}"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert published in readme, f"the README should quote an effect size of {published}"


@pytest.mark.parametrize(
    ("path", "stale"),
    [(p, s) for p in PUBLISHED for s in SUPERSEDED],
    ids=lambda v: getattr(v, "name", v),
)
def test_no_superseded_figure_survives_in_the_prose(path: Path, stale: str) -> None:
    """Catches a document reverted to, or copied from, an older draft."""
    if not path.exists():
        pytest.skip(f"{path.name} not present")
    text = path.read_text(encoding="utf-8")

    # Allow a superseded value that is genuinely a different quantity — match only when it
    # reads as a standalone figure rather than part of a longer number or a date.
    pattern = re.compile(rf"(?<![\d.]){re.escape(stale)}(?![\d])")
    assert not pattern.search(text), (
        f"{path.name} still quotes {stale}, which is no longer what the data says. "
        f"Current figures: {dict(OBSERVED)}"
    )


# -- strings the docs quote from the UI itself ---------------------------------------
#
# The demo script and the project story both quote captions the app renders. Those are
# computed, so they drift silently: the chart's axis floor is
# `low - (high - low) * 0.35` and the overlap is an integral over two densities. Neither
# is something a writer can re-derive in their head, and the story is written for
# publication. The axis figure was published as 486 against a rendered 487 within an hour
# of this section being added.


def _rendered_chart() -> str:
    """The chart as the app builds it: Genie's returned rows, through `group_means`.

    Deliberately not built from `OBSERVED`. An earlier version of this helper passed the
    already-rounded published means, so it exercised a path the app never takes — the app
    receives 492.64332917705605 from Genie, not 492.6 — and it certified an axis floor one
    higher than the one on screen. A drift test that invents its own input tests nothing.
    """
    from prove_it.domain.distribution import group_means
    from prove_it.genie.fake import demo_client
    from prove_it.ui.headline_chart import render_headline_chart

    client = demo_client()
    turn = client.ask("boys are better at maths")
    return render_headline_chart(group_means(client.fetch_result(turn)))


def _rendered_axis_floor() -> str:
    """The number the chart actually prints in its own `axis starts at …` label."""
    found = re.search(r"axis starts at ([\d.]+), not 0", _rendered_chart())
    assert found, "the chart no longer labels its truncated axis"
    return found.group(1)


def test_the_chart_caption_agrees_with_its_own_bar_labels() -> None:
    """The chart rounds its labels to one decimal place. If the gap in the caption is
    computed from the unrounded value, the caption contradicts the numbers printed
    directly above it — on the one panel whose whole subject is a misleading picture."""
    chart = _rendered_chart()
    labels = [float(v) for v in re.findall(r'class="hc-value">([\d.]+)<', chart)]
    assert len(labels) == 2, f"expected two bar labels, got {labels}"

    # The caption wraps in the source, so the number can sit on the next line.
    stated = re.search(r"a gap of\s+([\d.]+)", chart)
    assert stated is not None
    assert float(stated.group(1)) == pytest.approx(abs(labels[0] - labels[1]), abs=0.05)


def _rendered_overlap_percent() -> str:
    from prove_it.domain.distribution import GroupShape, overlap_fraction

    shapes = [
        GroupShape(g, o.students, o.maths_mean, o.maths_sd) for g, o in sorted(OBSERVED.items())
    ]
    overlap = overlap_fraction(shapes)
    assert overlap is not None
    return f"{overlap * 100:.0f}%"


def test_the_story_quotes_the_axis_label_the_chart_actually_draws() -> None:
    floor = _rendered_axis_floor()
    story = (ROOT / "docs" / "project-story.md").read_text(encoding="utf-8")
    assert f"axis starts at {floor}, not 0" in story, (
        f"the story quotes a different axis floor; the chart renders {floor}"
    )


def test_the_demo_script_quotes_the_same_axis_floor() -> None:
    floor = _rendered_axis_floor()
    script = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")
    assert script.count(floor) >= 2, (
        f"the demo script should name the rendered axis floor {floor} where it cues the chart"
    )


def test_the_published_overlap_matches_the_computed_one() -> None:
    """The one statistic the app states to a child in its own voice."""
    percent = _rendered_overlap_percent()
    story = (ROOT / "docs" / "project-story.md").read_text(encoding="utf-8")
    script = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")
    assert percent in story, f"the story should quote an overlap of {percent}"
    assert percent in script, f"the demo script should quote an overlap of {percent}"


# -- identifiers quoted in the prose -------------------------------------------------


def test_the_conversation_id_in_the_prose_is_the_recorded_one() -> None:
    """The README and the project story print a real Genie conversation id as the proof
    that both queries came from one exchange. `fixtures/recorded-demo.json` is committed,
    so that id is reproducible from the repo — and must not drift from it if the demo is
    ever re-recorded.
    """
    from prove_it.genie.fake import demo_client

    client = demo_client()
    first = client.ask("boys are better at maths")
    second = client.follow_up(first, "show the spread too")
    assert first.conversation_id == second.conversation_id, (
        "the recording no longer spans a single conversation, which is the claim the "
        "prose makes about it"
    )

    quoted = first.conversation_id
    for name in ("README.md", "docs/project-story.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert quoted in text, f"{name} quotes a conversation id that is not the recorded one"
        assert text.count(quoted) >= 2, (
            f"{name} should show the id on both queries — one occurrence does not "
            "demonstrate that they match"
        )


# -- the estimate ruler, and the gaps the prose quotes -------------------------------


def test_every_case_that_asks_for_an_estimate_can_be_answered_on_its_own_ruler() -> None:
    """A scale the true value falls off is a question with no right answer on it.

    The truth here is `Analysis.delta` over the recorded rows — the same number the app
    scores the player against — rather than a figure typed into this test.
    """
    import os

    os.environ.setdefault("PROVE_IT_OFFLINE", "1")
    os.environ.setdefault("PROVE_IT_TEMPO", "0")
    from prove_it.config import Settings
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.estimate import verdict_gap
    from prove_it.domain.game import Call, Stake
    from prove_it.session import Investigation

    settings = Settings.from_env()
    for case in DOCKET:
        inv = Investigation.open_case(case, settings.build_client(case.key))
        inv.ask_genie()
        inv.commit_call(Call.TRICK, Stake.HUNCH)
        gap = verdict_gap(inv.first_analysis.delta if inv.first_analysis else None)

        if case.estimate is None:
            assert gap is None, (
                f"{case.key} produces a gap of {gap} but asks for no estimate — either ask "
                f"for one, or the case changed shape"
            )
            continue

        assert gap is not None, (
            f"{case.key} asks the player to estimate a gap the analysis does not produce"
        )
        assert case.estimate.lo < gap < case.estimate.hi, (
            f"{case.key}: the real gap {gap:.1f} is off its own ruler "
            f"({case.estimate.lo}..{case.estimate.hi})"
        )


def test_the_demo_script_overshoot_is_above_the_real_gap_it_is_shot_against() -> None:
    """The script tells the presenter to place a deliberate overshoot and then read the
    real number back. Written once with the wrong case's gap in it — the beat is shot on
    Berkeley, whose gap is 14.2, and it quoted the maths case's 4.5.
    """
    script = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")
    assert "14.2" in script or "fourteen" in script, (
        "the estimate beat is shot on Berkeley; its real pooled gap must be the number read back"
    )
    assert "You said eighteen. It is four and a half." not in script, (
        "that pairing belongs to the maths case, which this beat is not shot on"
    )


# -- the docs must describe what the app actually shows -------------------------------


def test_the_denominator_prose_describes_the_reveal_the_app_actually_produces() -> None:
    """The worst class of bug this project can have, caught by a claims audit.

    The docs described the denominator case as "China 8.37 t, rank 19, below the USA at
    14.30". Those figures are genuinely in the table — but they are not what the case
    produces: Genie answers "show it per person" with a top ten, and China is not in it.
    The prose described the DATA instead of the PRODUCT, in a contest deliverable, for an
    app whose whole argument is to check the claim against what the evidence says.

    Pinned against the recorded conversation rather than against a number typed here, so
    the docs cannot drift from the reveal again.
    """
    import json

    fixture = json.loads((ROOT / "fixtures" / "case-denominator.json").read_text(encoding="utf-8"))
    leaders: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "rows" and isinstance(value, list) and value:
                    leaders.append(str(value[0][0]))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(fixture)
    assert leaders, "the fixture should contain result rows"
    per_person_leader = leaders[-1]
    assert per_person_leader == "Qatar", (
        f"the recorded per-person reveal is led by {per_person_leader!r}; if that changed, "
        f"the prose describing it has to change too"
    )

    # The README is in this list because it was the one file that escaped an earlier pass of
    # exactly this audit: it still read "China ... and 19th per person" long after the docs
    # had been corrected, because the loop only walked `docs/`. The front door is the page
    # most readers see, so it is the last place this claim should survive.
    for path in (
        ROOT / "docs" / "cases.md",
        ROOT / "docs" / "project-story.md",
        ROOT / "README.md",
    ):
        name = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        assert "Qatar" in text, (
            f"{name} describes the denominator reveal without naming Qatar, which is "
            f"what the app actually shows"
        )
        # Blockquotes are where both files record the correction, and recording it means
        # quoting the wording that was wrong. Only assertive prose is checked.
        asserted = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith(">")
        )
        for stale in ("rank 19", "19th"):
            assert stale not in asserted, (
                f"{name} still states a China per-person rank as fact; the reveal is a "
                f"top ten that does not include China"
            )


def test_every_docket_case_is_written_up_in_cases_md() -> None:
    """`cases.md` opens by claiming to hold every figure and its source. The reading case
    was missing from it entirely — a fifth of the live docket, silently absent."""
    from prove_it.domain.cases import DOCKET

    text = (ROOT / "docs" / "cases.md").read_text(encoding="utf-8")
    # Matched on the case TITLE rather than the claim string: cases.md legitimately quotes
    # some claims in the wording it evaluated rather than the wording that shipped, and a
    # test that forced them to be identical would be pinning prose, not coverage.
    missing = [c.key for c in DOCKET if c.title.lower() not in text.lower()]
    assert not missing, f"cases.md documents no figures for: {missing}"


def test_the_published_genie_timeout_is_the_one_the_client_waits() -> None:
    """A limit stated in prose is a claim like any other, and this one drifted.

    The README's "Known limits" and the demo script both told readers a cold warehouse could
    push Genie's first call past a *five-minute* timeout. The client has waited 180 seconds
    for as long as it has existed. Nothing failed, because no test read the sentence — the
    same gap that let the denominator prose describe the data instead of the product, and a
    worse one to leave in the section whose whole purpose is being honest about the limits.
    """
    stated = f"{DEFAULT_TIMEOUT_SECONDS:.0f}-second"
    for path in (ROOT / "README.md", ROOT / "docs" / "demo-script.md"):
        name = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for stale in ("five-minute", "five minute", "5-minute"):
            assert stale not in text.lower(), (
                f"{name} still quotes a {stale} Genie timeout; the client waits "
                f"{DEFAULT_TIMEOUT_SECONDS:.0f}s"
            )
        assert stated in text, (
            f"{name} describes the cold-warehouse wait but never as {stated}, which is what "
            f"DEFAULT_TIMEOUT_SECONDS actually is"
        )
