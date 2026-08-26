"""The interrogation room: the wait as a beat.

The one property that matters and is easy to get wrong is that the clock is owned by the
iframe and derived from a start epoch, not driven from Python — because Streamlit remounts
the component on every poll, and anything Python drove would restart at zero each tick.
"""

from __future__ import annotations

import json

from prove_it.ui.interrogation import PHASE_ORDER, phase_for, render_room


def payload_of(html: str) -> dict:
    return json.loads(html[html.index("var D = ") + 8 : html.index(";\n  var root")])


def test_each_genie_status_maps_to_a_board_light() -> None:
    assert phase_for("FETCHING_METADATA") == "READY"
    assert phase_for("PENDING_WAREHOUSE") == "READY"
    assert phase_for("ASKING_AI") == "THINKING"
    assert phase_for("EXECUTING_QUERY") == "QUERYING"
    assert phase_for("COMPLETED") == "SEALED"


def test_an_unknown_status_holds_the_first_light_rather_than_inventing_one() -> None:
    assert phase_for("SOME_NEW_STATUS") == "READY"


def test_the_board_lights_up_to_the_phase_reached() -> None:
    d = payload_of(render_room(phase="QUERYING", started_at_ms=1000.0, done=False))
    assert d["reached"] == PHASE_ORDER.index("QUERYING")
    assert d["order"] == PHASE_ORDER


def test_the_clock_is_derived_from_the_start_epoch_not_driven_from_python() -> None:
    html = render_room(phase="THINKING", started_at_ms=1712345678000.0, done=False)
    d = payload_of(html)
    assert d["startedAt"] == 1712345678000.0
    # The clock counts up from Date.now() - startedAt, inside the iframe, so a remount
    # mid-wait resumes rather than restarting at zero.
    assert "Date.now() - D.startedAt" in html
    assert "requestAnimationFrame(tick)" in html
    # Painted once synchronously before the first frame, so a remount mid-wait resumes at
    # the true elapsed time rather than flashing the static "0.0s" for a frame.
    assert html.index("paint();") < html.index("requestAnimationFrame(tick)")


def test_the_sealed_frame_freezes_the_clock() -> None:
    html = render_room(phase="SEALED", started_at_ms=1000.0, done=True)
    d = payload_of(html)
    assert d["done"] is True
    # done short-circuits the animation loop.
    assert "if (!D.done) requestAnimationFrame(tick)" in html


def test_the_frame_measures_its_content_not_the_document() -> None:
    html = render_room(phase="READY", started_at_ms=0.0, done=False)
    assert "getBoundingClientRect().height" in html
    assert "scrollHeight" not in html
