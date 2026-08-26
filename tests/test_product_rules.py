"""The product's own rules, checked against the code rather than against memory.

Every rule here was written after something went wrong: a webfont import that reached the
network, a grep-based check that failed on comments, a second call site that would have
opened the seal. Each was being honoured by intention, which is the weakest kind of
compliance, because nothing failed when it slipped. This suite is where they stop depending
on whoever edits next knowing the history.

Deliberately mechanical. A rule that cannot be checked by a machine does not belong here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from prove_it.domain.cases import DOCKET
from prove_it.domain.verdict import Verdict

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "prove_it"


def app_source() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in sorted(SRC.rglob("*.py"))]


# -- What will not be built ----------------------------------------------------------


def test_no_clickable_tab_navigation() -> None:
    """`st.tabs` is banned, and the reason is the product's core rule.

    Real tabs are clickable, so a player could reach the reveal before predicting — the
    one thing the sealing rule exists to prevent, one tap away.
    """
    for path, source in app_source():
        assert "st.tabs" not in source, f"{path.name} uses st.tabs; the seal forbids it"


def test_no_file_upload_surface() -> None:
    """No CSV/PDF upload. It turns the app into a document chatbot."""
    for path, source in app_source():
        assert "file_uploader" not in source, f"{path.name} offers an upload"


def test_the_page_makes_no_outbound_network_call() -> None:
    """No in-app network call. A webfont @import was a real breach of this in v1."""
    banned = re.compile(r"\b(requests\.|urllib|httpx|aiohttp|socket\.)|@import\s+url", re.I)
    for path, source in app_source():
        if path.name in {"client.py"}:
            # The Genie client is the app's one intended outbound path, through the SDK.
            continue
        found = banned.search(source)
        assert not found, f"{path.name} reaches the network: {found.group(0)!r}"


def test_no_account_or_login_surface() -> None:
    """No accounts, no SSO. Pupils never enter anything personal."""
    banned = re.compile(r"\b(st\.login|sign[_ ]?up|create[_ ]account|password)\b", re.I)
    for path, source in app_source():
        found = banned.search(source)
        assert not found, f"{path.name} looks like an account surface: {found.group(0)!r}"


def test_the_app_is_still_called_prove_it() -> None:
    """The name is on the deployed app and in the project story."""
    assert (SRC / "ui" / "app.py").read_text(encoding="utf-8").count("Prove It") >= 1


# -- Rules that survived v1 ----------------------------------------------------------


def test_rows_are_fetched_in_exactly_one_place() -> None:
    """Rows stay sealed until a committed call, enforced in session.py.

    Not "the UI does not call it" — the point is that there is one place to audit. A
    second call site is how the rule quietly stops holding.
    """
    session = (SRC / "session.py").read_text(encoding="utf-8")
    assert session.count("fetch_result(") == 2, (
        "expected exactly two fetch_result calls in session.py — one in commit_call, "
        "one in repair. A third is a new way to open the seal."
    )
    for path, source in app_source():
        if path.name in {"session.py", "client.py", "fake.py"}:
            continue
        assert "fetch_result" not in source, f"{path.name} fetches rows outside session.py"


def test_no_model_judges_a_claim() -> None:
    """Verdicts are arithmetic; a model never judges a model.

    Checked on the imports rather than on the prose. The first version of this grepped for
    the word "Genie" and failed on the COMMENTS, which are full of it for good reason —
    they explain what Genie returns. What actually matters is that the module deciding
    verdicts cannot reach the thing that talks to the model: it takes rows and returns a
    verdict, and there is no path from one to the other.
    """
    import ast

    tree = ast.parse((SRC / "domain" / "verdict.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    for module in imported:
        assert "genie" not in module, f"the verdict engine imports {module}"
        assert "client" not in module, f"the verdict engine imports {module}"
    # Pure arithmetic over rows: it needs nothing but the standard library.
    internal = sorted(m for m in imported if m.startswith("prove_it"))
    assert not internal, f"the verdict engine now depends on {internal}"


def test_every_verdict_has_screen_copy() -> None:
    """A verdict with no chip text raises a KeyError in front of a player."""
    from prove_it.ui.style import VERDICT_TEXT

    for verdict in Verdict:
        assert verdict in VERDICT_TEXT, f"{verdict.name} has no chip"
        label, css = VERDICT_TEXT[verdict]
        assert label.strip() and css.strip()


def test_cant_tell_is_reachable_and_celebrated() -> None:
    """Any Genie shape degrades to CANT_TELL, never an error screen."""
    from prove_it.domain.verdict import Column, ResultTable, analyse

    assert analyse(ResultTable([], [])).verdict is Verdict.CANT_TELL
    assert analyse(ResultTable([Column("x")], [["not a number"]])).verdict is Verdict.CANT_TELL


def test_offline_mode_still_says_so() -> None:
    """Passing a replay off as live is forbidden. The banner is the whole mechanism."""
    app = (SRC / "ui" / "app.py").read_text(encoding="utf-8")
    assert "Offline demo" in app
    assert "settings.offline" in app


def test_no_real_children_are_in_the_data() -> None:
    """Synthetic or open public data only. The per-pupil table is generated from a seed."""
    from prove_it.domain.cases import SPREAD

    assert SPREAD.real_data is False
    assert "seed" in SPREAD.source.lower()


# -- The docket keeps its shape ------------------------------------------------------


def test_every_curated_case_is_present() -> None:
    """The four tricks the docket was designed around cannot quietly drop out."""
    keys = {c.key for c in DOCKET}
    assert {"spread", "paradox", "window", "denominator"} <= keys


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_each_case_keeps_the_arc_it_was_designed_for(case) -> None:
    """`probe_cases.py` measures the same pairs live.

    Both read from `cases.py`, so this checks the shape rather than restating the values:
    every case starts by appearing to confirm its claim, and none of them ends on
    CANT_TELL, which would mean the docket offered a case with nothing to show.
    """
    first, second = case.expect
    assert first is Verdict.HOLDS
    assert second is not Verdict.CANT_TELL


def test_the_probe_and_the_docket_cannot_drift() -> None:
    """The gate must test the claims the app actually sends.

    A claim edited in `cases.py` and not in the probe would ship unmeasured, which is the
    exact failure the live probe exists to prevent.
    """
    probe = (ROOT / "scripts" / "probe_cases.py").read_text(encoding="utf-8")
    for case in DOCKET:
        assert case.claim in probe, f"{case.key}: the probe does not test this claim"
        assert case.follow_up in probe, f"{case.key}: the probe does not test this follow-up"
