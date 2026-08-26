"""The one definition of the teaching dataset.

These figures were previously written by hand in five places — the notebook, the offline
fake, the README, the spec and the tests — and they drifted: four of them quoted the
*parameters* handed to the random generator rather than the sample statistics it actually
produces, which are close but never equal.

So the generator lives here, the notebook imports it, and `tests/test_demo_data.py`
regenerates from the seed and fails if `OBSERVED` no longer matches. Numbers a reader is
shown have to be numbers the data really contains.

Imported by `prove_it.genie.fake` (for `OBSERVED`, so the offline demo shows the same
numbers as the real table), by the notebook and the setup script (for the generator), and
by the tests.

numpy and pandas are imported inside `generate_students` on purpose. `OBSERVED` is a plain
dict of NamedTuples, so the app can import it without dragging either into the running
app's import path — only the notebook and the setup script actually generate data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:  # pragma: no cover
    import pandas as pd

SEED = 20260831

CATALOG = "workspace"
SCHEMA = "prove_it"
STUDENTS_TABLE = f"{CATALOG}.{SCHEMA}.student_scores"
INDICATORS_TABLE = f"{CATALOG}.{SCHEMA}.country_indicators"


class GroupSpec(NamedTuple):
    """What the generator is asked for — not what it produces."""

    n: int
    maths_mean: float
    maths_sd: float
    reading_bonus: float


# A deliberately small maths gap against a large spread: that combination is the entire
# lesson, because it is the case where quoting two averages misleads. Reading runs the
# other way and by enough to survive, so the app is not a machine that only ever says
# "busted" — a child needs to see a claim hold up too, or the lesson is just cynicism.
GROUPS: dict[str, GroupSpec] = {
    "boy": GroupSpec(n=4812, maths_mean=494.2, maths_sd=92.6, reading_bonus=0.0),
    "girl": GroupSpec(n=4903, maths_mean=489.1, maths_sd=88.4, reading_bonus=28.0),
}

READING_SD = 90.0
SCHOOL_COUNT = 40
FIRST_STUDENT_ID = 10001


class Observed(NamedTuple):
    """Sample statistics the seeded generator really produces, to one decimal place."""

    students: int
    maths_mean: float
    maths_sd: float


# Verified by tests/test_demo_data.py, which regenerates these from SEED.
OBSERVED: dict[str, Observed] = {
    "boy": Observed(students=4812, maths_mean=492.6, maths_sd=91.7),
    "girl": Observed(students=4903, maths_mean=488.1, maths_sd=87.2),
}


def generate_students() -> pd.DataFrame:
    """Build the synthetic pupil table. Deterministic for a given SEED."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(SEED)
    schools = [f"S-{i:03d}" for i in range(1, SCHOOL_COUNT + 1)]

    frames = []
    for gender, spec in GROUPS.items():
        maths = rng.normal(spec.maths_mean, spec.maths_sd, spec.n)
        reading = rng.normal(spec.maths_mean + spec.reading_bonus, READING_SD, spec.n)
        frames.append(
            pd.DataFrame(
                {
                    "gender": gender,
                    "maths_score": np.clip(maths, 0, 800).round(1),
                    "reading_score": np.clip(reading, 0, 800).round(1),
                    "school_id": rng.choice(schools, spec.n),
                    "year_group": rng.integers(7, 12, spec.n),
                    "exam_year": rng.choice([2019, 2020, 2021, 2022], spec.n),
                }
            )
        )

    students = pd.concat(frames, ignore_index=True)
    students.insert(0, "student_id", range(FIRST_STUDENT_ID, FIRST_STUDENT_ID + len(students)))
    return students


def effect_size(observed: dict[str, Observed] | None = None) -> float:
    """Standardised difference in maths means, pooled and weighted by group size.

    The demo only works while this stays well under 0.2. If a change to the generator
    pushes it above, the repaired query would confirm the claim instead of overturning
    it and the lesson inverts — so it is asserted in the tests, not merely printed.
    """
    stats = observed or OBSERVED
    a, b = stats["boy"], stats["girl"]
    numerator = (a.students - 1) * a.maths_sd**2 + (b.students - 1) * b.maths_sd**2
    pooled = (numerator / (a.students + b.students - 2)) ** 0.5
    return abs(a.maths_mean - b.maths_mean) / pooled


COLUMN_COMMENTS = {
    "student_id": "Unique id for one pupil. Not a real person.",
    "gender": "Either boy or girl.",
    "maths_score": "Maths test score for this pupil, roughly 0-800.",
    "reading_score": "Reading test score for this pupil, roughly 0-800.",
    "school_id": "The school this pupil attends.",
    "year_group": "School year, 7 to 11.",
    "exam_year": "Calendar year the test was taken.",
}

TABLE_COMMENT = (
    "One row per pupil. Synthetic data generated for a data-literacy teaching app; it "
    "contains no real pupils. Use it to compare groups of pupils on maths_score or "
    "reading_score."
)

# The second table is genuinely real published data, so the lesson can end on the actual
# world rather than on numbers we made up. Telling Genie plainly that it is aggregate is
# what lets it answer "this data cannot say that about an individual" instead of guessing.
INDICATORS_COMMENT = (
    "Real published country-level indicators, downloaded from a public source such as the "
    "World Bank or Our World in Data. One row per country per year. Aggregate data: it has "
    "no per-person rows, so it can compare countries but cannot say anything about any "
    "individual person."
)

# Applied to whichever of these columns the uploaded CSV actually has, so the loader stays
# generic while the recommended dataset still arrives documented. A Genie space is only as
# good as its column comments, and a column called combined_expenditure_share_gdp means
# nothing to a model or a child without one.
INDICATOR_COLUMN_COMMENTS = {
    "entity": "The country or region this row is about.",
    "country": "The country or region this row is about.",
    "code": "Three-letter country code, for example GBR or BRA.",
    "year": "Calendar year the figure was recorded.",
    "combined_expenditure_share_gdp": (
        "How much the government spent on education that year, as a percentage of the "
        "country's GDP. Higher means a larger share of the economy went on education."
    ),
}
