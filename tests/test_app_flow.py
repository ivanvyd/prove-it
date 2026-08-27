"""Drives the real Streamlit script through the archive and the board.

These are not unit tests of the view; they run the app the way a child does, so a
regression that only shows up once Streamlit's rerun model is involved gets caught here
rather than in front of a class.
"""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from prove_it.domain.cases import DOCKET, case_for

APP = str(Path(__file__).resolve().parents[1] / "src" / "prove_it" / "ui" / "app.py")


def launch() -> AppTest:
    """A fresh app. AppTest starts each instance with its own empty session state."""
    return AppTest.from_file(APP, default_timeout=30).run()


def all_text(app: AppTest) -> str:
    """Everything the page rendered, markdown, status widgets and inline frames alike.

    The frames matter and used to be invisible here. The board is one `st.iframe`
    document — the warrant, the sealed bag, the result strip and the second warrant are
    all inside it — so a helper that read only markdown would see none of the case.
    AppTest keeps the frame's markup on the element, so the text is reachable; it just has
    to be asked for.
    """
    parts: list[str] = []
    for group in (app.markdown, app.caption, app.info, app.success, app.warning):
        parts += [str(element.value) for element in group]
    for element in app._tree.get("iframe") or []:
        srcdoc = getattr(getattr(element, "proto", None), "srcdoc", "")
        if srcdoc:
            parts.append(srcdoc)
    return "\n".join(parts)


def mark(app: AppTest, value: float) -> None:
    """Place the gap mark the way the component would.

    AppTest cannot drag a custom component, so this writes the slot the component reports
    into. That is the real seam rather than a shortcut: the app reads the mark from
    session state, not from the investigation, so setting `inv.guess` directly would be
    overwritten by the very `commit_call` under test — which is how this test first failed.
    """
    inv = app.session_state["investigation"]
    spec = inv.case.estimate
    app.session_state[f"guess-{inv.run_key}"] = {
        "fraction": spec.fraction_of(value),
        "value": value,
    }


def click(app: AppTest, label_contains: str) -> AppTest:
    for button in app.button:
        if label_contains.lower() in str(button.label).lower():
            return button.click().run()
    raise AssertionError(
        f"No button matching {label_contains!r}. Buttons: {[b.label for b in app.button]}"
    )


def call(app: AppTest, slip: str, stake: str = "Hunch") -> AppTest:
    """The design's three-step wager: pick a slip, stake a coin, break the seal."""
    app = click(app, slip)
    app = click(app, stake)
    return click(app, "Break the seal")


def open_own(app: AppTest) -> AppTest:
    """Case file Nº 0: the folder has to be opened before the sheet to write on appears."""
    return click(app, "Open case 0")


SEALED = "Result rows inside"


def test_the_app_starts_without_credentials_and_offers_the_docket() -> None:
    app = launch()
    assert not app.exception
    labels = [str(b.label) for b in app.button]
    assert any("The average" in label for label in labels)
    assert "Offline demo" in all_text(app)


def test_the_sealed_board_shows_sql_but_no_numbers() -> None:
    """The query is on the warrant; the result is in the bag."""
    app = click(launch(), "The average")
    assert not app.exception

    text = all_text(app)
    # Quoting-agnostic on purpose: real Genie emits AVG(`maths_score`) with backticks, and
    # asserting the unquoted form was encoding a guess about its formatting rather than a
    # requirement. What matters is that the query is on screen and the numbers are not.
    assert "AVG(" in text and "maths_score" in text, "the query Genie wrote should be visible"
    assert SEALED in text and "do not open" in text
    for leaked in ("492.6", "488.1", "494.2"):
        assert leaked not in text, f"the answer ({leaked}) leaked before the child predicted"
    assert app.dataframe == [], "no result table may render while the result is sealed"


def test_the_seal_cannot_be_broken_without_a_slip_and_a_stake() -> None:
    """The wager is three steps, and the third is dim until the first two are on record."""
    app = click(launch(), "The average")
    seal = next(b for b in app.button if "Break the seal" in str(b.label))
    assert seal.disabled, "the seal must wait for a call and a stake"
    app = click(app, "There's a trick")
    seal = next(b for b in app.button if "Break the seal" in str(b.label))
    assert seal.disabled, "a slip alone is not a wager"
    app = click(app, "Fairly sure")
    seal = next(b for b in app.button if "Break the seal" in str(b.label))
    assert not seal.disabled
    assert SEALED in all_text(app), "nothing opens until the seal is broken"


def test_returned_numbers_are_rounded_for_a_child_to_read() -> None:
    """Genie returns 492.64332917705605; fifteen decimals is noise on a classroom screen."""
    from prove_it.ui.render import for_display

    assert for_display("492.64332917705605") == "492.6"
    assert for_display("91.71313655709994") == "91.7"
    assert for_display("4812") == "4812", "counts must stay counts, not become 4812.0"
    assert for_display("boy") == "boy"
    assert for_display(None) is None
    assert for_display("NaN") == "NaN", "leave what it cannot read alone"


def test_a_rate_is_shown_as_a_percentage_not_rounded_into_uselessness() -> None:
    """Berkeley's pooled rates rendered as 0.4 and 0.3 on a live screen.

    That is not a cosmetic rounding loss. Department D admits 33.1% of men and 34.9% of
    women, and at one decimal place both read 0.3 — so a department that reverses stops
    appearing to reverse, in the table the entire case rests on.
    """
    from prove_it.ui.render import for_display

    assert for_display("0.4451876625789669", "admit_rate") == "44.5%"
    assert for_display("0.3035422343324251", "admit_rate") == "30.4%"

    # The two departments the old formatting erased.
    assert for_display("0.3309352517985612", "admit_rate") != for_display(
        "0.3493333333333333", "admit_rate"
    )
    assert for_display("0.0589812332439678", "admit_rate") != for_display(
        "0.0703812316715543", "admit_rate"
    )


def test_a_column_already_expressed_as_a_percentage_is_left_alone() -> None:
    """`combined_expenditure_share_gdp` matches the rate test by NAME, and its values are
    already percentages — 3.53 means 3.53% of GDP. Multiplying by a hundred would invent a
    number, so the 0..1 guard is what keeps the window case honest."""
    from prove_it.ui.render import for_display

    assert for_display("3.5299999713897705", "combined_expenditure_share_gdp") == "3.5"
    assert for_display("4.5", "combined_expenditure_share_gdp") == "4.5"
    # And a per-capita figure is not a rate at all.
    assert for_display("8.3712", "co2_per_capita") == "8.4"


def test_the_reasoning_cards_render_with_their_labels() -> None:
    app = click(launch(), "The average")
    text = all_text(app)
    assert "How it read the question" in text
    assert "Where it looked" in text
    assert "What it worked out" in text


def test_breaking_the_seal_pins_the_naive_result_to_the_board() -> None:
    """The gap looks real when only averages are on screen."""
    app = call(click(launch(), "The average"), "There's a trick")
    assert not app.exception

    text = all_text(app)
    # The call stands, unsettled: a "trick" call at LOOKS TRUE looks lost, and the desk
    # must say the cross-examination decides rather than scoring it here.
    # The apostrophe is HTML-escaped on the way out, so match around it.
    assert "Called: There" in text and "s a trick" in text
    assert "cross-examination decides" in text
    assert "staked" in text
    assert "Looks true" in text
    assert "higher average" in text
    assert "492.6" in text, "the v1 rows are on the strip now"
    assert "query v1" in text


def test_a_holds_up_call_is_settled_only_at_the_retrial() -> None:
    """LOOKS TRUE appears to vindicate "it holds up"; the fairer query takes it away.
    Nothing may pay out or be lost before that."""
    app = call(click(launch(), "The average"), "It holds up")
    text = all_text(app)
    assert "Called: It holds up" in text
    assert "Missed" not in text and "Called it" not in text, "nothing settles at the reveal"

    app = click(app, "show the spread")
    text = all_text(app)
    assert "Missed" in text, "a holds-up call against a bust loses its stake"
    # The overturning still pays, because the player made it happen by cross-examining.
    assert "Verdict overturned" in text


def test_the_repair_overturns_the_verdict_and_pins_the_second_warrant() -> None:
    """The moment the whole product exists for."""
    app = call(click(launch(), "The average"), "There's a trick")
    app = click(app, "show the spread")
    assert not app.exception

    text = all_text(app)
    assert "Busted" in text
    assert "STDDEV" in text, "the repaired query must be visible"
    assert "overlap" in text
    assert "the answer changed" in text, "the lesson line should fire"
    assert "Warrant N&ordm; 2" in text, "the second warrant fills the reserved space"
    assert "Overturned" in text, "the stamp should land when the verdict really flipped"


def test_the_retrial_names_what_each_added_column_revealed() -> None:
    """The retrial should say what changed, not just show two warrants side by side."""
    app = call(click(launch(), "The average"), "There's a trick")
    app = click(app, "show the spread")
    assert not app.exception

    text = all_text(app)
    assert "Search warrant" in text
    assert "Warrant N&ordm; 2" in text
    # Narration quoted off the returned rows, not invented.
    assert "How many are in each group" in text
    assert "Almost everyone is in the same range" in text


def test_the_stamp_does_not_fire_when_the_verdict_did_not_flip() -> None:
    """The theatre must never outrun the arithmetic."""
    from prove_it.domain.verdict import Verdict

    app = call(click(launch(), "The average"), "There's a trick")
    app = click(app, "show the spread")

    inv = app.session_state["investigation"]
    assert inv.lesson_landed is True
    assert inv.first_analysis.verdict is Verdict.HOLDS
    assert inv.second_analysis.verdict is Verdict.BUSTED


def test_closing_the_case_prints_the_receipt_that_says_the_app_wrote_no_sql() -> None:
    """This line is the twenty-point criterion, printed."""
    app = call(click(launch(), "The average"), "There's a trick")
    app = click(app, "show the spread")
    app = click(app, "Close the case")
    assert not app.exception

    text = all_text(app)
    assert "Queries written by Genie" in text
    assert "Queries written by this app" in text
    assert "Busted" in text
    # The run, settled: a hunch on "trick" against a bust pays 100 + 250 overturned +
    # 150 closed, and the ending names a rank and the gap to the next rung.
    assert "Case closed" in text
    # 100 called it (hunch) + 250 overturned + 150 closed = 500, which lands exactly on
    # Evidence Clerk's floor — so the rung named next is the one above it.
    assert "500 pts" in text
    assert "Evidence Clerk" in text
    assert "to Field Investigator" in text
    # The antibody card is minted over the board.
    assert "Antibody N&ordm; 01" in text
    # The share strip is an st.code block, which all_text does not reach.
    strip = "\n".join(str(c.value) for c in app.code)
    assert "●" in strip and "✓" in strip
    assert "boys" not in strip, "the strip must not name the claim"


def test_the_case_card_can_be_shared_and_pinned() -> None:
    app = call(click(launch(), "The average"), "There's a trick")
    app = click(app, "show the spread")
    app = click(app, "Close the case")
    app = click(app, "Share the case card")
    text = all_text(app)
    assert "the only thing that leaves the room" in text
    assert "0 by the app" in text
    app = click(app, "Back to the card")
    app = click(app, "Pin it to the kit")
    assert "Antibody N&ordm; 01" not in all_text(app), "pinning puts the card away"


def test_a_finished_investigation_can_be_restarted() -> None:
    case = case_for("paradox")
    assert case is not None
    app = call(click(launch(), case.title), "There's a trick")
    # The case's own label, not a hardcoded one: each case argues for a different repair,
    # and this test opened the paradox while still clicking the spread case's button.
    app = click(app, case.repair_label)
    app = click(app, "Close the case")
    app = click(app, "Return to the archive")

    assert not app.exception
    assert "rumours on the desk" in all_text(app), "the archive should be the screen showing"
    assert "Closed &middot; Busted" in all_text(app), "the folder is stamped with its verdict"


def test_typing_a_claim_does_not_submit_it_until_the_button_is_pressed() -> None:
    """A bare text_input would fire a Genie call at whatever had been typed so far."""
    app = open_own(launch())
    app.text_input[0].input("boys are bett").run()

    assert not app.exception
    assert SEALED not in all_text(app), "the claim was sent before it was submitted"
    assert "rumours on the desk" in all_text(app), "the archive should be the screen showing"


def test_a_typed_claim_is_sent_when_submitted() -> None:
    app = open_own(launch())
    app = app.text_input[0].input("boys are better at maths").run()
    app = click(app, "Test it")

    assert not app.exception
    assert SEALED in all_text(app)


def test_submitting_an_empty_claim_does_nothing() -> None:
    app = open_own(launch())
    app = click(app, "Test it")

    assert not app.exception
    assert SEALED not in all_text(app)


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_every_case_on_the_docket_reaches_the_sealed_board(case) -> None:
    """The offline script is claim-agnostic, so no case may dead-end."""
    app = click(launch(), case.title)
    assert not app.exception
    assert SEALED in all_text(app)


# The estimate, end to end ----------------------------------------------------------


def test_a_close_estimate_pays_on_the_chit_and_the_run() -> None:
    """Drives the real script: mark the gap, call it, cross-examine, read the payout.

    Verified in a browser first — the reading case's real gap is 21.8, a mark of 22.0
    scores "Dead on", and the chits read +100 Called it · +150 Case closed · +150 Dead
    on. This pins that.
    """
    case = case_for("reading")
    assert case is not None and case.estimate is not None

    app = click(launch(), case.title)
    mark(app, 22.0)
    app = call(app, "It holds up")

    # The mark against the truth belongs to the review, where the rows have just landed
    # and the comparison is the news.
    revealed = all_text(app)
    assert "You said" in revealed and "22.0" in revealed and "21.8" in revealed
    assert "Dead on" in revealed

    app = click(app, case.repair_label)
    assert "+150 Dead on" in all_text(app), "the chit carries it forward"
    run = app.session_state["run"]
    assert run.points == 400, f"expected 100 + 150 + 150, got {run.points}"


def test_a_wide_estimate_costs_nothing_and_prints_no_chit() -> None:
    """A nil estimate chit would read as a fine for having tried."""
    case = case_for("reading")
    assert case is not None

    app = click(launch(), case.title)
    mark(app, 39.0)
    app = call(app, "It holds up")
    assert "Wide of it" in all_text(app), "the review still shows the player where they were"

    app = click(app, case.repair_label)
    text = all_text(app)
    run = app.session_state["run"]
    assert run.points == 250, "a wide mark must neither pay nor deduct"
    chits = re.findall(r'class="pi-chit">([^<]*)<', text)
    assert any("Called it" in c for c in chits)
    assert not any("Wide of it" in c for c in chits), "no nil chit belongs on the desk"


def test_every_folder_in_the_drawer_lies_at_its_own_angle() -> None:
    """Five folders, five different tilts — the thing that makes the docket read as
    objects on a desk rather than a grid of cards. The angle rides on the folder as an
    inline custom property, one per case."""
    text = all_text(launch())
    tilts = set(
        re.findall(r'class="pi-folder pi-folder--(?:case|next)" style="--rot:(-?[\d.]+)deg"', text)
    )
    assert len(tilts) == min(5, len(DOCKET)), f"expected a distinct tilt per case, got {tilts}"


def test_the_first_open_case_is_marked_up_next_and_a_called_one_is_stamped() -> None:
    text = all_text(launch())
    assert text.count("Up next") == 1, "exactly one folder is up next"
    assert "Closed &middot;" not in text, "nothing is stamped before anything is called"


def test_a_case_that_asks_for_no_estimate_still_plays() -> None:
    """The window's trick is a chosen span of years, not a distance between two numbers,
    so it asks for no mark at all — and must be unaffected."""
    case = case_for("window")
    assert case is not None and case.estimate is None

    app = call(click(launch(), case.title), "There's a trick")
    app = click(app, case.repair_label)
    assert not app.exception
    assert "You said" not in all_text(app), "a case that did not ask must not report a mark"
