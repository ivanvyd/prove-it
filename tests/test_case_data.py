"""The transcribed figures have to reproduce what was published.

`case_data` holds numbers copied from someone else's paper. A generator can be re-run to
check itself; a transcription can only be checked against its source, and a wrong digit
here reaches the screen, the project story and a judge who may know the real figure.

So nothing published is *stored*: the percentages and the marginals are computed from the
twelve transcribed cells and compared against the published values. A mistyped count would
have to be wrong in a way that still reproduces twelve percentages and four totals, which
is not a mistake anyone makes.
"""

from __future__ import annotations

import pytest

from prove_it.case_data import (
    BERKELEY,
    berkeley_departments_favouring_women,
    berkeley_pooled,
    berkeley_rows,
)

# Bickel et al. (1975), as reproduced in the standard sources: applicants and admit
# percentage per department per gender. Percentages are published rounded to whole
# numbers, so the check allows half a point either side.
PUBLISHED = {
    "A": {"men": (825, 62), "women": (108, 82)},
    "B": {"men": (560, 63), "women": (25, 68)},
    "C": {"men": (325, 37), "women": (593, 34)},
    "D": {"men": (417, 33), "women": (375, 35)},
    "E": {"men": (191, 28), "women": (393, 24)},
    "F": {"men": (373, 6), "women": (341, 7)},
}

# Independently from R's `datasets::UCBAdmissions` manual page: the marginals, and the
# total observation count. These come from a different source than the table above, which
# is what makes the pair of checks worth more than either alone.
R_MARGINALS = {
    "men_applied": 2691,
    "men_admitted": 1198,
    "women_applied": 1835,
    "women_admitted": 557,
    "observations": 4526,
}


@pytest.mark.parametrize("dept", sorted(PUBLISHED))
def test_each_department_reproduces_its_published_percentages(dept: str) -> None:
    row = next(d for d in BERKELEY if d.department == dept)
    want = PUBLISHED[dept]

    assert row.men_applied == want["men"][0]
    assert row.women_applied == want["women"][0]
    assert row.men_rate * 100 == pytest.approx(want["men"][1], abs=0.5)
    assert row.women_rate * 100 == pytest.approx(want["women"][1], abs=0.5)


def test_the_marginals_match_the_r_dataset() -> None:
    assert sum(d.men_applied for d in BERKELEY) == R_MARGINALS["men_applied"]
    assert sum(d.men_admitted for d in BERKELEY) == R_MARGINALS["men_admitted"]
    assert sum(d.women_applied for d in BERKELEY) == R_MARGINALS["women_applied"]
    assert sum(d.women_admitted for d in BERKELEY) == R_MARGINALS["women_admitted"]


def test_the_observation_count_matches() -> None:
    total = sum(d.men_applied + d.women_applied for d in BERKELEY)
    assert total == R_MARGINALS["observations"]


def test_nobody_was_admitted_who_did_not_apply() -> None:
    for d in BERKELEY:
        assert 0 <= d.men_admitted <= d.men_applied, d.department
        assert 0 <= d.women_admitted <= d.women_applied, d.department


# -- the paradox itself, which is the case ------------------------------------------


def test_the_pooled_rate_favours_men() -> None:
    """The naive query's answer, and the reason the case has something to overturn."""
    men, women = berkeley_pooled()
    assert men > women
    assert men * 100 == pytest.approx(44.5, abs=0.1)
    assert women * 100 == pytest.approx(30.4, abs=0.1)


def test_most_departments_favour_women() -> None:
    """Simpson's paradox, asserted as arithmetic rather than as a claim in prose.

    If this ever stops being true the case does not merely lose a line of narration, it
    stops being a paradox and the whole beat is wrong.
    """
    assert berkeley_departments_favouring_women() == 4
    assert berkeley_departments_favouring_women() > len(BERKELEY) / 2


def test_the_reversal_is_the_whole_point() -> None:
    men, women = berkeley_pooled()
    pooled_favours_men = men > women
    departments_favour_women = berkeley_departments_favouring_women() > len(BERKELEY) / 2
    assert pooled_favours_men and departments_favour_women


# -- what gets loaded ----------------------------------------------------------------


def test_the_loaded_rows_are_tidy_and_complete() -> None:
    rows = berkeley_rows()
    assert len(rows) == len(BERKELEY) * 2
    # Plural: these labels are read into generated sentences ("women did better in 4 of
    # the 6 groups underneath"), and the singular form reached a live screen.
    assert {r["gender"] for r in rows} == {"men", "women"}
    assert {r["department"] for r in rows} == {d.department for d in BERKELEY}


def test_the_loaded_rows_carry_no_precomputed_rate() -> None:
    """Genie must compute the admission rate itself.

    A `rate` column would let the naive query read one off instead of writing
    `admitted / applicants`, and the repaired query would then differ from the naive one
    only by a GROUP BY — losing the visible arithmetic that makes the case teachable.
    """
    assert set(berkeley_rows()[0]) == {"department", "gender", "applicants", "admitted"}


def test_the_loaded_totals_survive_the_round_trip() -> None:
    rows = berkeley_rows()
    men = [r for r in rows if r["gender"] == "men"]
    assert sum(int(r["applicants"]) for r in men) == R_MARGINALS["men_applied"]
    assert sum(int(r["admitted"]) for r in men) == R_MARGINALS["men_admitted"]
