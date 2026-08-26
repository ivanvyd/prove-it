"""Guards the numbers a child is shown against the numbers the data contains.

This suite exists because they already diverged once: the README, the offline fake and
the spec all quoted the generator's *input parameters* as though they were the sample
statistics. Drawing ~4,800 values from a normal distribution lands near the requested
mean, never on it.

It also gives the notebook real coverage. The notebook itself cannot run here — it needs
Spark — but its data generation is the part that can be wrong in a way nobody notices,
and that part lives in `prove_it.demo_data` where it can be executed.
"""

import pytest

from prove_it.demo_data import (
    GROUPS,
    OBSERVED,
    SEED,
    effect_size,
    generate_students,
)
from prove_it.domain.verdict import Column, ResultTable, Verdict, analyse
from prove_it.genie.fake import DEMO_RESULTS

pytest.importorskip("pandas", reason="pandas ships with Streamlit and the Databricks runtime")


def sample_stats() -> dict[str, tuple[int, float, float]]:
    students = generate_students()
    grouped = students.groupby("gender")["maths_score"]
    return {
        gender: (
            int(grouped.count()[gender]),
            round(float(grouped.mean()[gender]), 1),
            round(float(grouped.std(ddof=1)[gender]), 1),
        )
        for gender in GROUPS
    }


def test_the_generator_is_deterministic_for_the_seed() -> None:
    first = generate_students()
    second = generate_students()
    assert first.equals(second), f"generation is not reproducible at SEED={SEED}"


def test_observed_statistics_match_what_the_generator_produces() -> None:
    """If this fails, every number quoted to a reader is now wrong. Update OBSERVED."""
    actual = sample_stats()
    for gender, expected in OBSERVED.items():
        n, mean, sd = actual[gender]
        assert n == expected.students, gender
        assert mean == pytest.approx(expected.maths_mean, abs=0.05), gender
        assert sd == pytest.approx(expected.maths_sd, abs=0.05), gender


def test_the_offline_demo_shows_the_same_numbers_as_the_real_data() -> None:
    """The recorded fake must not tell a different story from the live table."""
    v2 = DEMO_RESULTS["demo-message-2"]
    by_gender = {row[0]: row for row in v2.rows}

    for gender, expected in OBSERVED.items():
        row = by_gender[gender]
        assert int(row[1]) == expected.students, gender
        assert float(row[2]) == pytest.approx(expected.maths_mean, abs=0.05), gender
        assert float(row[3]) == pytest.approx(expected.maths_sd, abs=0.05), gender

    v1 = DEMO_RESULTS["demo-message-1"]
    for row in v1.rows:
        assert float(row[1]) == pytest.approx(OBSERVED[row[0]].maths_mean, abs=0.05)


def test_the_gap_stays_negligible_or_the_lesson_inverts() -> None:
    """The whole product depends on the repaired query overturning the naive one."""
    assert effect_size() < 0.2, (
        "The maths gap is no longer negligible, so the repaired query would CONFIRM the "
        "claim instead of busting it. Widen the spread or narrow the means."
    )
    assert effect_size() < 0.1, "the demo is most convincing well below the threshold"


def test_the_demo_rows_really_do_produce_the_two_verdicts_they_promise() -> None:
    """End to end on the real numbers: naive query holds, repaired query busts."""
    assert analyse(DEMO_RESULTS["demo-message-1"]).verdict is Verdict.HOLDS
    assert analyse(DEMO_RESULTS["demo-message-2"]).verdict is Verdict.BUSTED


def test_reading_scores_run_the_other_way_so_some_claims_survive() -> None:
    """A product that only ever says 'busted' teaches cynicism rather than scepticism."""
    students = generate_students()
    grouped = students.groupby("gender")["reading_score"]
    table = ResultTable(
        [Column("gender"), Column("students"), Column("avg_score"), Column("spread")],
        [
            [
                g,
                str(int(grouped.count()[g])),
                f"{grouped.mean()[g]:.1f}",
                f"{grouped.std(ddof=1)[g]:.1f}",
            ]
            for g in GROUPS
        ],
    )
    result = analyse(table)
    assert result.verdict is Verdict.HOLDS, "girls-read-better should survive the spread check"
    assert result.groups is not None
    assert result.delta is not None and result.delta < 0, "girls should be ahead on reading"
