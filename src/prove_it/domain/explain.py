"""Genie's query, said out loud in words a ten-year-old already has.

The whole product asks a child to read a query before they are allowed to see its answer.
On the maths case that is fair: `SELECT gender, AVG(maths_score) ... GROUP BY gender` is
almost English already. On the denominator case Genie returns two CTEs and a window
function, and "read the query, then bet on it" quietly becomes "trust the app, then bet on
it" — which is the one thing this product must never ask for.

So every part the app can name is annotated in place: point at it, or tab to it, and the
panel says what that part does.

**This module reads SQL and never writes it.** Every pattern below matches a clause inside
a string Genie already returned; nothing here assembles a query and nothing here runs one.
`tests/test_no_sql_in_app_code.py` covers this file like any other in the package, which is
why the patterns are clause fragments rather than anything resembling a statement.

Deliberately shallow, and explicit about it. A real parser would read any query anyone
could write; this names only what it can name *locally* — each note describes the characters
it covers and nothing else, which is what keeps it correct inside a CTE or a window function
where a whole-query summary would not be. An earlier version summarised the whole query and
announced "asks for the biggest of year" about a two-CTE per-person ranking, with total
confidence. A wrong reading is worse than none, because the reading is what the bet gets
placed on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A note on the build gate, because this file looks like exactly what the gate forbids.
# `tests/test_no_sql_in_app_code.py` rejects a module whose strings pair the projection
# keyword with the source keyword — that is what composing a query looks like. The patterns
# here survive it for a real reason rather than by luck: every one begins `\b`, so the
# keyword inside the literal is preceded by a word character and the gate's own `\b` cannot
# match there. A genuinely composed query in this file would still be caught. Verified by
# running the gate against this module, not assumed.
_IDENT = re.compile(r"[`\"]([^`\"]+)[`\"]")
_NOT_NULL = re.compile(r"[`\"]?([\w.]+)[`\"]?\s+IS\s+NOT\s+NULL", re.I)
_LIKE = re.compile(r"[`\"]?([\w.]+)[`\"]?\s+I?LIKE\s+'%?([^%']+)%?'", re.I)
_IN = re.compile(r"[`\"]?([\w.]+)[`\"]?\s+IN\s*\(([^()]*)\)", re.I)
# One quoted value inside an IN list. Splitting that list on commas instead reported
# `IN ('Korea, Rep.', 'Egypt, Arab Rep.')` as four countries rather than two — a confidently
# wrong reading, on exactly the comma-bearing country names the window case's own table is
# full of.
_QUOTED = re.compile(r"'([^']*)'|\"([^\"]*)\"|`([^`]*)`")
# A function call whose argument may itself contain calls, so the outermost one wins.
_CALL = re.compile(r"\b([A-Za-z_]+)\s*\(")
# A value worth repeating back to a child. `LIKE '%(%'` matched the old pattern and
# produced "keeps only rows where x is (", which says nothing and looks broken.
_MEANINGFUL = re.compile(r"[A-Za-z0-9]")

# Each template carries its own preposition. A shared "of {name}" read as "how spread out
# of reading score is" for STDDEV, which is the sort of sentence that tells a child the
# app is not really speaking to them.
_FUNCTIONS = {
    "AVG": "the average of {name}",
    "SUM": "the total of {name}",
    "COUNT": "how many rows are in each group",
    "STDDEV": "how spread out {name} is",
    "MIN": "the smallest {name}",
    "MAX": "the biggest {name}",
    "TRY_DIVIDE": "one number divided by another, as a rate",
}


@dataclass(frozen=True)
class Fragment:
    """One run of the query, with what it does if this module recognised it.

    `note` is None for the punctuation and keywords between the parts worth explaining.
    Concatenating every `text` in order reproduces the query exactly, which is what lets
    the view render the annotation over Genie's own SQL rather than over a paraphrase.
    """

    text: str
    note: str | None = None


def _pretty(name: str) -> str:
    """A column or table identifier as a person would say it."""
    bare = name.replace("`", "").replace('"', "").rsplit(".", 1)[-1]
    return bare.replace("_", " ").strip()


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(i for i in items if i))


def _split_top_level(fragment: str) -> list[str]:
    """Split on commas that are not inside brackets."""
    out: list[str] = []
    depth = 0
    current: list[str] = []
    for char in fragment:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            out.append("".join(current))
            current = []
        else:
            current.append(char)
    out.append("".join(current))
    return out


def _describe(piece: str) -> str | None:
    """One selected thing, as English. The outermost call decides what it is."""
    text = piece.strip()
    if not text:
        return None
    call = _CALL.search(text)
    if call and call.group(1).upper() in _FUNCTIONS:
        template = _FUNCTIONS[call.group(1).upper()]
        if "{name}" not in template:
            return template
        # The argument of the OUTERMOST call only. Reading into a nested call is how
        # `try_divide(SUM(admitted), SUM(applicants))` came out as "the total of admitted"
        # twice, describing neither the division nor the rate it produces.
        inner = _IDENT.search(text[call.end() :])
        return template.format(name=_pretty(inner.group(1)) if inner else "these rows")
    ident = _IDENT.search(text)
    return _pretty(ident.group(1)) if ident else None


def _closing_bracket(text: str, opening: int) -> int | None:
    """Where the bracket opened at `opening` closes, or None if it never does.

    Quotes are tracked, because a bracket inside a string literal is not a bracket. Counting
    every character alike meant `AVG(CASE WHEN x LIKE '%(%' THEN 1 ELSE 0 END)` — an
    ordinary conditional rate — never found its closing bracket, and the aggregate went
    unexplained on the screen built to explain aggregates.
    """
    depth = 0
    quote: str | None = None
    for index in range(opening, len(text)):
        char = text[index]
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _in_values(listed: str) -> list[str]:
    """The values in an IN list, respecting quotes.

    Splitting on commas treated `'Korea, Rep.'` as two entries, so a filter picking two
    countries was described as picking four. Quoted values are taken whole; only when the
    list contains no quotes at all does the comma become a separator, which is the numeric
    case (`IN (1991, 1996)`).
    """
    quoted = [
        next(g for g in match.groups() if g is not None) for match in _QUOTED.finditer(listed)
    ]
    if quoted:
        return _unique([v.strip() for v in quoted if v.strip()])
    return _unique([v.strip() for v in listed.split(",") if v.strip()])


def _join(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _spans(flat: str) -> list[tuple[int, int, str]]:
    """Every part of the query this module can name, as (start, end, note).

    Each pattern is *locally* true: it describes only the characters it covers, so it stays
    correct inside a CTE or a window function where a whole-query summary would not.
    """
    found: list[tuple[int, int, str]] = []

    for match in re.finditer(r"\b([A-Za-z_]+)\s*\(", flat):
        name = match.group(1).upper()
        if name not in _FUNCTIONS:
            continue
        end = _closing_bracket(flat, match.end() - 1)
        if end is None:
            # An unbalanced call: describe nothing rather than guess where it ended.
            continue
        note = _describe(flat[match.start() : end])
        if note:
            found.append((match.start(), end, f"This works out {note}."))

    for match in re.finditer(r"\bFROM\s+([`\"\w.]+)", flat, re.I):
        target = match.group(1)
        # A bare name with no catalog path and no quoting is a working table this query
        # built a moment ago, not evidence from the warehouse. Calling it "the latest year
        # table" implied the workspace held one.
        note = (
            f"The evidence: the {_pretty(target)} table."
            if ("." in target or "`" in target or '"' in target)
            else "Reads back the working table this query built above."
        )
        found.append((match.start(), match.end(), note))
    for match in _NOT_NULL.finditer(flat):
        found.append(
            (
                match.start(),
                match.end(),
                f"Ignores rows with no {_pretty(match.group(1))} recorded, so blanks "
                f"cannot tilt the answer.",
            )
        )
    for match in _LIKE.finditer(flat):
        value = match.group(2).strip()
        if not _MEANINGFUL.search(value):
            continue
        found.append(
            (
                match.start(),
                match.end(),
                f"Keeps only rows where {_pretty(match.group(1))} is {value}.",
            )
        )
    for match in _IN.finditer(flat):
        listed = _in_values(match.group(2))
        if not listed:
            continue
        found.append(
            (
                match.start(),
                match.end(),
                f"Keeps only {_pretty(match.group(1))} {_join(listed)} — and nothing in between.",
            )
        )
    for match in re.finditer(r"\bGROUP\s+BY\b(.*?)(?=\bORDER\b|\bLIMIT\b|$)", flat, re.I):
        by = _unique([_describe(p) or "" for p in _split_top_level(match.group(1))])
        if by:
            found.append(
                (match.start(), match.end(), f"Works it out separately for each {_join(by)}.")
            )
    for match in re.finditer(r"\bORDER\s+BY\b(.*?)(?=\bLIMIT\b|;|$)", flat, re.I):
        by = _unique([_describe(p) or "" for p in _split_top_level(match.group(1))])
        if by:
            found.append((match.start(), match.end(), f"Puts the rows in order of {_join(by)}."))
    for match in re.finditer(r"\bLIMIT\s+\d+", flat, re.I):
        found.append((match.start(), match.end(), "Keeps only the first few rows."))
    for match in re.finditer(r"\bOVER\s*\([^)]*\)", flat, re.I):
        found.append(
            (match.start(), match.end(), "Compares each row against all the others, in order.")
        )
    for match in re.finditer(r"\bWITH\b", flat, re.I):
        found.append(
            (match.start(), match.end(), "Builds a working table first, then asks about that.")
        )
    return found


def annotate(sql: str | None) -> tuple[Fragment, ...]:
    """Genie's query, split into runs, each carrying what it does.

    The point is that a child can put a pointer on `STDDEV(maths_score)` and be told it
    measures how spread out the scores are — on the query itself, in place, rather than in
    a glossary somewhere else. Text is preserved exactly: the fragments concatenate back to
    the query Genie wrote, character for character.
    """
    if not sql or not sql.strip():
        return ()

    # Longest first at the same start, so `FROM x` wins over a bare identifier inside it.
    spans = sorted(_spans(sql), key=lambda s: (s[0], -(s[1] - s[0])))
    taken: list[tuple[int, int, str]] = []
    for start, end, note in spans:
        if taken and start < taken[-1][1]:
            continue
        taken.append((start, end, note))

    out: list[Fragment] = []
    cursor = 0
    for start, end, note in taken:
        if start > cursor:
            out.append(Fragment(sql[cursor:start]))
        out.append(Fragment(sql[start:end], note))
        cursor = end
    if cursor < len(sql):
        out.append(Fragment(sql[cursor:]))
    return tuple(out)
