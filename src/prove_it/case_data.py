"""Published figures for the real-data cases.

`demo_data` owns the synthetic pupil generator. This owns numbers that were published by
someone else and that this project only transcribes — which makes the risk different, and
worse. A generator can be re-run to check itself; a transcription can only be checked
against the source, and a digit wrong here would put a false figure on screen, in the
project story, and in front of a judge who may well know the real one.

So every table here carries its citation, and `tests/test_case_data.py` re-derives the
published summary statistics from the transcribed cells. That is the whole safeguard: the
percentages and marginals are *not* stored, they are computed, so a mistyped count cannot
agree with them by accident.
"""

from __future__ import annotations

from dataclasses import dataclass

# -- Berkeley 1973 ------------------------------------------------------------------
#
# Bickel, P.J., Hammel, E.A. & O'Connell, J.W. (1975). "Sex Bias in Graduate Admissions:
# Data from Berkeley." Science 187(4175): 398-404.
#
# Transcribed from the six-department table as reproduced in the standard sources, and
# cross-checked against R's `datasets::UCBAdmissions` (4,526 observations, Admit x Gender
# x Dept). Both checks are re-run by the test module: the twelve admitted counts below
# reproduce all twelve published admit percentages AND both marginal totals, which is a
# tighter constraint than either source alone.
#
# THE TRAP, recorded here because it is the one that would ship a wrong number: the famous
# "44% of men and 35% of women" figure is over ALL Berkeley departments - 8,442 men and
# 4,321 women. This table is only the six largest, 2,691 and 1,835, and pools to 44.5% and
# 30.4%. They are different numbers about different populations. Anything this project
# says out loud must say "the six largest departments" and must never quote 44/35.

BERKELEY_SOURCE = (
    "Bickel, Hammel & O'Connell (1975), Science 187(4175): 398-404 — the six largest departments"
)


@dataclass(frozen=True)
class Admissions:
    """One department's applications, split by gender, exactly as published."""

    department: str
    men_applied: int
    men_admitted: int
    women_applied: int
    women_admitted: int

    @property
    def men_rate(self) -> float:
        return self.men_admitted / self.men_applied

    @property
    def women_rate(self) -> float:
        return self.women_admitted / self.women_applied

    @property
    def favours_women(self) -> bool:
        """Did women get in at a higher rate here than men?"""
        return self.women_rate > self.men_rate


BERKELEY: tuple[Admissions, ...] = (
    Admissions("A", men_applied=825, men_admitted=512, women_applied=108, women_admitted=89),
    Admissions("B", men_applied=560, men_admitted=353, women_applied=25, women_admitted=17),
    Admissions("C", men_applied=325, men_admitted=120, women_applied=593, women_admitted=202),
    Admissions("D", men_applied=417, men_admitted=138, women_applied=375, women_admitted=131),
    Admissions("E", men_applied=191, men_admitted=53, women_applied=393, women_admitted=94),
    Admissions("F", men_applied=373, men_admitted=22, women_applied=341, women_admitted=24),
)


def berkeley_pooled() -> tuple[float, float]:
    """Admit rate for men and for women across these six departments.

    The number the naive query returns, and the reason the case works: it points the
    opposite way to most of the departments underneath it.
    """
    men_applied = sum(d.men_applied for d in BERKELEY)
    men_admitted = sum(d.men_admitted for d in BERKELEY)
    women_applied = sum(d.women_applied for d in BERKELEY)
    women_admitted = sum(d.women_admitted for d in BERKELEY)
    return men_admitted / men_applied, women_admitted / women_applied


def berkeley_departments_favouring_women() -> int:
    return sum(1 for d in BERKELEY if d.favours_women)


def berkeley_rows() -> list[dict[str, str | int]]:
    """The table as it is loaded into Unity Catalog: one row per department per gender.

    Long rather than wide, because Genie writes better SQL against a tidy table and
    because the naive pooled query then falls out of a plain GROUP BY - which is exactly
    the query the case needs it to reach for first.
    """
    rows: list[dict[str, str | int]] = []
    for d in BERKELEY:
        rows.append(
            {
                "department": d.department,
                # Plural, because the label is read straight into generated sentences.
                # The live probe put "man came out ahead" and "woman did better in 4 of
                # the 6 groups underneath" on screen before this was changed.
                "gender": "men",
                "applicants": d.men_applied,
                "admitted": d.men_admitted,
            }
        )
        rows.append(
            {
                "department": d.department,
                "gender": "women",
                "applicants": d.women_applied,
                "admitted": d.women_admitted,
            }
        )
    return rows


BERKELEY_TABLE_COMMENT = (
    "Graduate admissions to the six largest departments at UC Berkeley, autumn 1973, from "
    "Bickel, Hammel & O'Connell (1975), Science 187(4175). One row per department per "
    "gender. NOT the whole university: these six departments took 2,691 men and 1,835 "
    "women, so figures pooled from this table differ from the university-wide ones often "
    "quoted. Departments are anonymised as A-F in the published source."
)

BERKELEY_COLUMN_COMMENTS = {
    "department": "Anonymised department, A to F, as published. Not a subject name.",
    "gender": "'men' or 'women', as recorded in the 1973 source.",
    "applicants": "How many people of this gender applied to this department.",
    "admitted": (
        "How many of them were admitted. The admission RATE is admitted / applicants — "
        "there is no rate column, so compute it."
    ),
}


# -- Emissions (Our World in Data) ---------------------------------------------------
#
# OWID CO2 and Greenhouse Gas Emissions, CC BY 4.0. Loaded from the published CSV rather
# than transcribed, so there are no figures to protect here - only the loading rule.
#
# THE LOADING RULE: OWID puts `World`, `Asia`, `High-income countries` and similar
# aggregates in the same `country` column as real countries. A "biggest emitter" query
# against the unfiltered table answers "World", which is true and useless. The filter
# belongs in the loader and not in a Genie instruction: the app must not depend on the
# model remembering to exclude a row.

EMISSIONS_MIN_POPULATION = 1_000_000

EMISSIONS_TABLE_COMMENT = (
    "Annual CO2 emissions by country, from Our World in Data (CC BY 4.0). Aggregates such "
    "as 'World', continents and income groups have been removed, as have countries under "
    "one million people, so every row is a single country. Both a total and a per-person "
    "figure are given for the same country and year."
)

EMISSIONS_COLUMN_COMMENTS = {
    "country": "Country name. Aggregates like 'World' or 'Asia' are not in this table.",
    "year": "Calendar year.",
    "population": "Population that year.",
    "co2": "Total CO2 emissions that year, in million tonnes.",
    "co2_per_capita": (
        "CO2 emissions per person that year, in tonnes. This is the total divided by the "
        "population, and it ranks countries very differently from the total."
    ),
}
