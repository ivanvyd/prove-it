"""R10 — the app writes no SQL of its own.

This is the twenty-point judging criterion expressed as a build gate. If a SELECT ever
appears in a string the application code actually uses, Genie has stopped being the
engine and become decoration, and the entry loses the half of the score it was designed
around. Better to fail here.

The check walks the AST rather than grepping the text, so modules stay free to *discuss*
SQL in a docstring — which they need to, because explaining why the app must not write
SQL is most of what these modules are documenting.

`genie/fake.py` is the one exemption, and it is exempt for a specific reason: it holds
*recorded* Genie output for offline replay. That is data the app displays, not SQL the
app composed and ran.
"""

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "prove_it"

EXEMPT = {"fake.py"}

# Patterns, not substrings. This code is prose-heavy on purpose — it explains itself to
# a child — and bare words like "from" and "select" appear in ordinary English, so a
# loose substring gate cries wolf. A composed query always pairs SELECT with FROM.
SQL_PATTERNS = (
    re.compile(r"\bSELECT\b[\s\S]{0,300}\bFROM\b", re.I),
    re.compile(r"\bGROUP\s+BY\b", re.I),
    re.compile(r"\bINSERT\s+INTO\b", re.I),
    re.compile(r"\bCREATE\s+TABLE\b", re.I),
    re.compile(r"\bSTDDEV\s*\(", re.I),
)


def app_modules() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.py") if p.name not in EXEMPT)


def docstring_nodes(tree: ast.Module) -> set[int]:
    """Ids of the string constants that are docstrings, so prose can be skipped."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def assembled_strings(tree: ast.Module, skip: set[int]) -> list[tuple[int, str]]:
    """Every string this module builds, as the reader would see it — not as the parser
    stores it.

    Inspecting `ast.Constant` nodes one at a time is what the gate used to do, and it left
    a hole big enough to drive ordinary code through. A query written the way anyone would
    actually write one —

        query = f"SELECT {column} FROM scores"

    — compiles to a `JoinedStr` whose literal halves are two separate Constants, `"SELECT "`
    and `" FROM scores"`. Neither contains both keywords, so neither matches, and the gate
    passes a file that composes SQL. The same is true of `"SELECT x " + "FROM y"`.

    Measured before this was fixed: of six ways to write the same query, the old gate caught
    two. It missed `+` concatenation, `.join()`, a split f-string, and the plain interpolated
    f-string above — the most natural of the six.

    So the concatenation is done here first. `+` chains and f-strings are flattened into the
    text they produce, with interpolations standing in as a placeholder, and the patterns run
    against that.
    """
    out: list[tuple[int, str]] = []

    def flatten(node: ast.AST) -> str | None:
        """The literal text of a string expression, or None if it is not one."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return None if id(node) in skip else node.value
        if isinstance(node, ast.JoinedStr):
            # `{expr}` becomes a space: it stands for *something*, and the question is
            # whether SQL keywords surround it, not what it evaluates to.
            parts = [
                value.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
                else " "
                for value in node.values
            ]
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = flatten(node.left), flatten(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr | ast.BinOp):
            text = flatten(node)
            if text:
                out.append((getattr(node, "lineno", 0), text))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in skip:
                out.append((node.lineno, node.value))
        elif isinstance(node, ast.Call):
            # `" ".join([...])` — the separator and every literal element, in order.
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "join":
                sep = flatten(func.value) or ""
                if node.args and isinstance(node.args[0], ast.List | ast.Tuple):
                    pieces = [flatten(e) for e in node.args[0].elts]
                    if all(p is not None for p in pieces):
                        out.append((node.lineno, sep.join(p for p in pieces if p)))
    return out


def test_there_are_modules_to_check() -> None:
    """Guards against the gate silently passing because the glob broke."""
    names = {p.name for p in app_modules()}
    assert {"session.py", "verdict.py", "claim.py", "app.py"} <= names


@pytest.mark.parametrize("module", app_modules(), ids=lambda p: p.name)
def test_no_sql_literal_in_application_code(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"))
    skip = docstring_nodes(tree)

    for lineno, text in assembled_strings(tree, skip):
        for pattern in SQL_PATTERNS:
            assert not pattern.search(text), (
                f"{module.name}:{lineno} has {pattern.pattern!r} in a live string. "
                f"The app must never compose SQL — every query has to come from Genie."
            )


@pytest.mark.parametrize(
    ("shape", "source"),
    [
        ("a plain literal", 'q = "SELECT gender FROM scores"'),
        ("adjacent literals", 'q = ("SELECT gender " "FROM scores")'),
        ("+ concatenation", 'q = "SELECT gender " + "FROM scores"'),
        ("an interpolated f-string", 'q = f"SELECT {col} FROM scores"'),
        ("a split f-string", 'q = f"SELECT {col} " f"FROM scores"'),
        ("str.join", 'q = " ".join(["SELECT gender", "FROM scores"])'),
        ("a GROUP BY on its own", 'q = f"...{x} GROUP BY gender"'),
    ],
)
def test_the_gate_catches_sql_however_it_was_assembled(shape: str, source: str) -> None:
    """The gate's own self-test, and the reason it was rewritten.

    Each of these composes the same query a different way. The gate used to inspect string
    constants individually and caught only the first two — so the most ordinary form of all,
    an f-string with one interpolation, would have passed a file that builds SQL. This is
    the twenty-point criterion, so the gate has to hold against ordinary code, not just
    against a literal nobody would write.
    """
    tree = ast.parse(source)
    found = [
        text
        for _, text in assembled_strings(tree, docstring_nodes(tree))
        if any(p.search(text) for p in SQL_PATTERNS)
    ]
    assert found, f"the gate would not catch SQL written as {shape}"


def test_the_gate_does_not_fire_on_ordinary_prose() -> None:
    """The other half: this codebase explains itself constantly, and a gate that trips on
    the word "from" in a sentence would be turned off within a day."""
    # Deliberately NOT "select a claim from the docket". That sentence trips the gate, and
    # it should: the patterns are case-insensitive, and a lowercase `select … from` is the
    # exact shape being guarded against. A gate that let it through to spare an English
    # sentence would be trading the twenty-point criterion for a copy-editing convenience.
    # The wording in the app avoids it — "Pick a claim", not "select a claim".
    source = (
        'a = f"You want to compare {group} against the others"\n'
        'b = "Pick a claim. The app will not tell you whether it is true."\n'
        'c = "an average tells you where a group sits, not how much it varies"\n'
    )
    tree = ast.parse(source)
    tripped = [
        text
        for _, text in assembled_strings(tree, docstring_nodes(tree))
        if any(p.search(text) for p in SQL_PATTERNS)
    ]
    assert not tripped, f"the gate cried wolf on prose: {tripped}"


def test_the_questions_sent_to_genie_are_english() -> None:
    """The other half of the same rule: nothing SQL-shaped goes *to* Genie either."""
    from prove_it.domain.claim import opening_question, repair_question

    for question in (opening_question("boys are better at maths"), repair_question()):
        for pattern in SQL_PATTERNS:
            assert not pattern.search(question), f"{question!r} looks like SQL"


def test_the_gate_would_actually_catch_composed_sql(tmp_path: Path) -> None:
    """Proves the gate bites, rather than passing because it checks nothing."""
    offender = tmp_path / "offender.py"
    offender.write_text('QUERY = "SELECT gender FROM scores"\n', encoding="utf-8")

    tree = ast.parse(offender.read_text(encoding="utf-8"))
    skip = docstring_nodes(tree)
    hits = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
        and any(pattern.search(node.value) for pattern in SQL_PATTERNS)
    ]
    assert hits == ["SELECT gender FROM scores"]
