"""Prove It — the five beats, in a Databricks App.

The view holds no logic worth testing: it renders what `Investigation` decided. That is
deliberate, because the interesting rules — when rows may be fetched, what counts as a
falsifying prediction, how a verdict is reached — belong where a test can reach them.
"""

from __future__ import annotations

import html
import sys
import time
from pathlib import Path

# Streamlit runs this file by path (`streamlit run src/prove_it/ui/app.py`), which puts
# only this directory on sys.path — not `src`. That works while the editable install is
# intact and fails with ModuleNotFoundError when it is not, which is a real failure mode:
# an `-e` install can register its metadata without writing the .pth that does the actual
# path wiring, and the app then dies on import with no clue why. Making the documented
# command work on its own terms is cheaper than making everyone debug their install.
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from prove_it.config import Settings  # noqa: E402
from prove_it.domain.cases import DOCKET, Case
from prove_it.domain.claim import ClaimError, repair_question
from prove_it.domain.custody import evidence_tag, same_conversation
from prove_it.domain.discovery import (
    MAX_DISCOVERED,
    DiscoveredTable,
    build_docket,
    hidden_cases,
    matches_dropped,
)
from prove_it.domain.distribution import group_means, group_shapes  # noqa: E402
from prove_it.domain.estimate import EstimateResult, score_estimate, verdict_gap
from prove_it.domain.exhibits import exhibits_for, weighting_exhibits
from prove_it.domain.game import (
    CALL_POINTS,
    Call,
    Run,
    Stake,
    calibration,
    next_rank,
    rank_for,
)
from prove_it.domain.record import Record
from prove_it.domain.sqldiff import Change, diff_tokens
from prove_it.domain.verdict import series_points, subgroup_rates
from prove_it.session import Investigation, Stage
from prove_it.ui.components import gap_mark
from prove_it.ui.headline_chart import render_headline_chart
from prove_it.ui.interrogation import phase_for, render_room, room_height
from prove_it.ui.pupil_cloud import cloud_height, render_cloud
from prove_it.ui.query_panel import panel_height, render_query_panel
from prove_it.ui.render import (
    bring_into_view,
    call_line,
    custody_line,
    estimate_line,
    hud,
    payout_line,
    provenance_panel,
    render_diff,
    render_exhibits,
    render_sql,
    render_table,
    render_thoughts,
    seal_panel,
    source_link,
    step_rail,
    verdict_chip,
)
from prove_it.ui.reversal_chart import chart_height as reversal_height
from prove_it.ui.reversal_chart import render_reversal
from prove_it.ui.style import CSS, DEFAULT_NUDGE, DEFAULT_REPAIR_LABEL, FRAME_THEME
from prove_it.ui.verdict_slam import SLAM_MARKER, render_slam, slam_height
from prove_it.ui.window_chart import chart_height as window_height
from prove_it.ui.window_chart import render_window

# -- beats --------------------------------------------------------------------------


def render_case_card(case: Case, index: int) -> bool:
    """One case on the docket. Returns True when it is picked.

    The trick is named on the card before the case is opened, not withheld as a surprise.
    Knowing it is "the missing denominator" does not spoil anything — the work is spotting
    where it applies, and a player who knows what they are looking for engages harder than
    one being set up.
    """
    # The eyebrow is the SHAPE of the evidence, not the trick. Once a call can be lost, a
    # card reading "Simpson's paradox" is a bet that cannot lose; the trick is named at
    # the flip and on the antibody card, where it lands as a reveal.
    # A discovered case has never been run. Saying so on the card is not a disclaimer, it
    # is the same honesty the rest of the app runs on: the curated five advertise an arc
    # because someone measured it three times, and this one cannot make that claim.
    unverified = (
        '<span class="pi-case-new">found in your data · unchecked</span>' if not case.probed else ""
    )
    st.markdown(
        # The folder's angle in the drawer, carried on the card so the CSS can find it.
        # It was `:nth-of-type` on the column until a browser measurement showed Streamlit
        # renders each docket row as its own columns container, which resets the count: all
        # five folders were drawing at one of two angles, and three of the design's five
        # never appeared. Keyed off the case index instead, so the angle belongs to the
        # case rather than to where it happens to sit in a row.
        #
        # A cycle of five, not five unique angles: discovery can push the docket to fifteen
        # cases, and the sixth folder repeats the first's tilt. That is the intended
        # behaviour rather than a cap — folders sharing an angle three rows apart read as a
        # drawer, and inventing ten more angles would only make the tilt look arbitrary.
        f'<div class="pi-case-trick pi-tilt-{index % 5}">'
        f"{html.escape(case.evidence)}{unverified}</div>"
        f'<div class="pi-case-claim">&ldquo;{html.escape(case.claim)}&rdquo;</div>'
        f'<div class="pi-case-source">{"Real data" if case.real_data else "Synthetic data"}'
        f" · {html.escape(case.source)}</div>",
        unsafe_allow_html=True,
    )
    return st.button(
        f"Open case {index + 1} — {case.title}",
        width="stretch",
        key=f"case-{case.key}",
    )


def run_with_room(call, label: str):
    """Run one Genie turn while showing the interrogation room instead of a spinner.

    `call` takes an `on_status(status, elapsed)` callback and does the Genie work. Each
    status paints the room into a single `st.empty()` slot; because the room's clock is
    derived from a start epoch it keeps running smoothly even though the slot is rewritten
    on every phase. `label` is the accessible caption on the room, the one line a screen
    reader gets where a sighted user gets the board.
    """
    slot = st.empty()
    started_ms = time.time() * 1000
    # The last phase actually painted. The client reports a status every second, but the
    # room only changes when the PHASE changes — several raw statuses fold onto one light.
    # Repainting regardless tore down and rebuilt the iframe on every tick: a cold wait
    # approaching the 180s timeout meant ~180 document reloads for the three or four
    # transitions a viewer can actually see. The clock keeps running between them because
    # the frame derives it from a start epoch rather than from Python.
    painted: list[str | None] = [None]

    def on_status(status: str, _elapsed: float) -> None:
        phase = phase_for(status)
        if phase == painted[0]:
            return
        painted[0] = phase
        with slot.container():
            st.caption(label)
            st.iframe(
                render_room(phase=phase, started_at_ms=started_ms, done=phase == "SEALED"),
                height=room_height(),
            )

    # Show the opening frame at once, so the room is up before Genie's first phase lands.
    on_status("SUBMITTED", 0.0)
    try:
        call(on_status)
    finally:
        slot.empty()


def mapping_panel(settings: Settings, docket: list[Case]) -> None:
    """Where every case on this docket came from, and what was passed over.

    The docket is no longer a list someone typed — it is a mapping from the tables this
    workspace actually has onto the tricks they can carry. That mapping is a decision the
    app made on your behalf, so it is shown rather than hidden: which table, which trick,
    which columns it will be asked about, and which tables matched nothing.

    An expander rather than a screen. A player never needs it; anyone pointing the app at
    their own catalog needs it immediately.
    """
    tables = session_tables(settings)
    if not tables:
        return

    generated = [c for c in docket if not c.probed]
    label = (
        f"Where these cases came from — {len(tables)} tables in "
        f"{settings.catalog}.{settings.schema}"
    )
    with st.expander(label):
        rows = "".join(
            f"<tr><td>{html.escape(c.table)}</td><td>{html.escape(c.trick)}</td>"
            f"<td>{'checked' if c.probed else 'unchecked'}</td></tr>"
            for c in docket
        )
        st.markdown(
            '<div class="pi-prov"><table>'
            "<tr><th>Table</th><th>Trick it is being asked about</th><th>Arc</th></tr>"
            f"{rows}</table></div>",
            unsafe_allow_html=True,
        )

        # The failure this panel was rewritten for: a Databricks App runs as its own
        # service principal, that principal had SELECT on two of four tables, and the
        # docket quietly became three cases long with nothing on screen to say so.
        hidden = hidden_cases(DOCKET, tables)
        if hidden:
            st.warning(
                f"**{len(hidden)} checked cases are missing**, because this app cannot "
                f"read the tables behind them: "
                + ", ".join(sorted({c.table for c in hidden}))
                + ". A Databricks App runs as its own service principal, not as you, and "
                "it needs SELECT on each table plus CAN_USE on the warehouse. Run "
                "`python scripts/grant_app_access.py --app <name>` to grant both."
            )

        matched = {c.table for c in docket}
        passed_over = [t.short_name for t in tables if t.short_name not in matched]
        if passed_over:
            st.caption(
                "No case built from: "
                + ", ".join(sorted(passed_over))
                + ". A table needs the columns a trick is made of — a measure and "
                "something to group it by, or a tried/succeeded pair, or a year and a "
                "series. Nothing here matched, and a case whose query cannot be asked is "
                "worse than no case."
            )
        # A cap nobody is told about reads as "this is everything".
        dropped = matches_dropped(tables)
        if dropped:
            st.caption(
                f"{dropped} more tables matched a trick and are not shown — a docket is "
                f"{MAX_DISCOVERED} cases, not a catalogue. The strongest matches were kept."
            )
        if generated:
            st.caption(
                f"{len(generated)} of these were built from your own tables just now and "
                "have never been run. They may not flip, and if the data cannot rule the "
                "verdict will honestly say so — which this app scores as a win."
            )
        st.caption(
            f"Point it somewhere else with PROVE_IT_CATALOG / PROVE_IT_SCHEMA (currently "
            f"{settings.catalog}.{settings.schema}), or set PROVE_IT_DISCOVER=0 to play "
            f"only the checked cases."
        )


def beat_claim(settings: Settings) -> None:
    st.markdown('<div class="pi-eyebrow">The docket</div>', unsafe_allow_html=True)
    st.markdown(
        '<h2 class="pi-bigq">Pick a claim. The app will not tell you whether it is true.</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pi-lede">Genie writes the query that would test it. You see the query '
        "and the reasoning — the result stays sealed until you lock your call: does it "
        "hold up, or is there a trick? How sure you are multiplies what that call is "
        "worth. Then one follow-up in plain English, and the answer often changes."
        "</div>",
        unsafe_allow_html=True,
    )

    claim = ""
    chosen: Case | None = None

    # A fresh pair of columns per row, rather than two tall columns filled alternately.
    # Streamlit stacks columns in DOM order when they collapse, so two tall columns read
    # "case 1, case 3, case 2, case 4" on a phone — visibly wrong, because the numbers are
    # in the button labels. Row-wise, the same grid stacks 1, 2, 3, 4.
    docket = session_docket(settings)
    for start in range(0, len(docket), 2):
        row = st.columns(2, gap="large")
        for offset, case in enumerate(docket[start : start + 2]):
            with row[offset]:
                if render_case_card(case, start + offset):
                    chosen = case

    mapping_panel(settings, docket)

    if settings.free_text:
        st.markdown(
            '<div class="pi-vlabel">Case zero — bring your own</div>', unsafe_allow_html=True
        )
        # A form, so the claim is only sent when it is submitted. A bare text_input returns
        # its value on every rerun, which would fire a Genie call at whatever had been
        # typed so far.
        with st.form("claim-form", clear_on_submit=False):
            typed = st.text_input(
                "Your claim",
                placeholder="Something you have heard and never checked",
                label_visibility="collapsed",
            )
            if st.form_submit_button("Test it", type="primary") and typed.strip():
                claim = typed
        st.caption(
            "Most typed claims end in “can't tell” — the data has no column for them. "
            "That is a win, not a failure."
        )

    if chosen is None and not claim:
        return

    try:
        client = settings.build_client(chosen.key if chosen is not None else None)
        investigation = (
            Investigation.open_case(chosen, client)
            if chosen is not None
            else Investigation.open(claim, client)
        )
    except ClaimError as exc:
        st.warning(str(exc))
        return

    # The room renders here, once, directly after the grid — not inside the column of the
    # folder that was clicked. Writing into a container created inside a column AFTER the
    # loop has emitted later rows makes Streamlit re-emit that column's block, and the
    # docket grew a second, greyed-out copy of the case below the real one. The frame
    # brings itself into view on its first phase, which is what the container was reaching
    # for anyway.
    run_with_room(investigation.ask_genie, "Genie is working out how to check that…")
    st.session_state.investigation = investigation
    st.session_state.scroll_to_top = True
    st.rerun()


def beat_instrument(inv: Investigation) -> None:
    turn = inv.first
    assert turn is not None

    st.markdown(f'<h2 class="pi-claim">“{html.escape(inv.claim)}”</h2>', unsafe_allow_html=True)
    st.markdown(
        step_rail(2, "Genie wrote a query to test it"),
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        # The annotated panel carries its own label, so the page does not print a second
        # one above it. This is the screen the whole bet is placed on, so it is the screen
        # where the query has to be readable rather than merely present.
        st.iframe(
            render_query_panel(turn.sql, label="The query Genie wrote"),
            height=panel_height(turn.sql),
        )
        st.markdown(custody_line(turn), unsafe_allow_html=True)
        st.markdown(
            seal_panel(
                opened=False,
                tag=evidence_tag(turn),
                question=(
                    "Before you look — lock your call. Does this claim survive a "
                    "<em>fair</em> check?"
                ),
            ),
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="pi-vlabel">How it got there</div>', unsafe_allow_html=True)
        render_thoughts(turn)

    st.divider()
    st.markdown(
        step_rail(3, "Lock your call")
        + '<h2 class="pi-bigq">Does this claim survive a fair check?</h2>',
        unsafe_allow_html=True,
    )
    # The stake before the call. It is what makes the call cost something, and a stake
    # chosen after the buttons reads as an afterthought. The rule is stated where the
    # chips are chosen, in the one sentence the whole scoring layer reduces to.
    stake_label = st.radio(
        "How sure are you?",
        [f"{s.label} ×{s.multiplier}" for s in Stake],
        horizontal=True,
        key="stake",
        help=(
            "Your stake multiplies what the call is worth — and what it costs. "
            "Sure and wrong is the expensive kind of wrong."
        ),
    )
    stake = next(s for s in Stake if stake_label.startswith(s.label))
    st.markdown(
        f'<div class="pi-stakeline">Called right: +{CALL_POINTS * stake.multiplier} · '
        f"called wrong: −{CALL_POINTS * stake.multiplier}</div>",
        unsafe_allow_html=True,
    )

    # The estimate, where the case asks for one. It sits above the call buttons rather
    # than beside them because it is the first half of the same commitment: place the
    # number, then say what it means. Both are locked by the one click below.
    guess = gap_estimate(inv)

    # "The data can't say" is a call only on a claim the player typed. Every docket case
    # was probed to a verdict, so there it would be a button that only ever loses.
    calls = [Call.HOLDS_UP, Call.TRICK] + ([Call.CANT_SAY] if inv.case is None else [])
    columns = st.columns(len(calls))
    for column, call in zip(columns, calls, strict=True):
        if column.button(call.value, width="stretch", key=f"call-{call.name}"):
            with st.spinner("Opening the seal…"):
                inv.commit_call(call, stake, guess)
            # The reveal reads top-down: the call, the estimate against the real gap, the
            # seal breaking, then the rows. Left where the buttons were, the player landed
            # on the rows and read the ending first.
            st.session_state.scroll_to_top = True
            st.rerun()


def cross_examine(inv: Investigation, label: str) -> None:
    """The follow-up, in the player's own words if they want it.

    This was a button. Pressing a button the app had already written is watching a
    cross-examination; typing the question is conducting one, and the flip that follows
    belongs to the player rather than to the app. It costs no extra Genie call, and the
    app still writes no SQL — the words go into the question, Genie writes the query.

    Pre-filled rather than blank on purpose. The suggested wording is what the probe
    measured producing the repaired query on live Genie, so accepting it keeps the
    docket's arcs reliable; a blank box would make every case a coin-flip on phrasing and
    would put the demo at the mercy of whatever gets typed on the day.
    """
    default = inv.case.follow_up if inv.case else repair_question()
    st.markdown(
        '<div class="pi-vlabel">Your cross-examination — change it if you want</div>',
        unsafe_allow_html=True,
    )
    with st.form(f"repair-{inv.run_key}", clear_on_submit=False):
        asked = st.text_input(
            "Ask Genie a fairer question",
            value=default,
            label_visibility="collapsed",
            key=f"repair-text-{inv.run_key}",
        )
        submitted = st.form_submit_button(label, type="primary")
    st.caption(
        "Genie writes the SQL either way — this is the question, not the query. Your own "
        "wording may not land the trick, and if it does not, the verdict honestly will "
        "not move."
    )
    if submitted:
        run_with_room(
            lambda on_status: inv.repair(on_status, asked=asked),
            "Genie is rewriting the query…",
        )
        st.session_state.scroll_to_flip = True
        st.rerun()


def gap_estimate(inv: Investigation) -> float | None:
    """Ask the player to place the gap before the seal breaks, and remember where.

    Returns the value in the case's own units, or None when this case does not ask or the
    player has not marked one — untouched has to stay distinguishable from zero, because
    "no gap at all" is a real answer and on the maths case very nearly the right one.

    The mark is held in session state and handed back to the component on every render,
    because a Streamlit rerun triggered by anything else on this screen — changing the
    stake, most obviously — rebuilds the iframe from scratch and would otherwise wipe it.
    """
    if inv.case is None or inv.case.estimate is None:
        return None
    spec = inv.case.estimate
    slot = f"guess-{inv.run_key}"
    held = st.session_state.get(slot)

    st.markdown(
        '<div class="pi-vlabel">Mark the gap — before you look</div>', unsafe_allow_html=True
    )
    marked = gap_mark(
        prompt=spec.prompt,
        lo=spec.lo,
        hi=spec.hi,
        lo_label=spec.lo_label,
        hi_label=spec.hi_label,
        unit=spec.unit,
        decimals=spec.decimals,
        theme=FRAME_THEME,
        fraction=held["fraction"] if held else None,
        key=f"gapmark-{inv.run_key}",
    )
    if marked:
        st.session_state[slot] = marked
        held = marked
    st.caption(
        "Optional, and it can only earn — a wide mark costs nothing. Guessing where the "
        "number lands before you see it is the part that makes the answer stick."
    )
    return float(held["value"]) if held else None


def beat_reveal(inv: Investigation) -> None:
    analysis = inv.first_analysis
    assert analysis is not None

    st.markdown(f'<h2 class="pi-claim">“{html.escape(inv.claim)}”</h2>', unsafe_allow_html=True)
    st.markdown(step_rail(4, "The result"), unsafe_allow_html=True)

    # The call, standing. At this beat a "trick" call looks lost and a "holds up" call
    # looks won, and neither is settled: the first verdict is the witness's testimony
    # and the cross-examination decides. Saying so here is what makes the reveal a
    # beat rather than an answer.
    st.markdown(call_line(inv), unsafe_allow_html=True)

    # The mark against the truth. This is the beat the estimate exists for: not the
    # guessing, the *gap between the guess and the data*, which is the thing the CHI
    # result says people remember. Rendered before the rows, so it lands as the answer to
    # the question the player just committed to rather than as a footnote to the table.
    st.markdown(estimate_line(inv), unsafe_allow_html=True)

    if inv.first is not None and inv.first.has_query:
        # The same seal the child was just looking at, opened. Rendering it here rather
        # than simply showing the rows means the reveal reads as *this* result arriving,
        # not as a new screen — and the demo can cut between the two poses.
        #
        # The column split matches beat_instrument's exactly, and that is the whole point:
        # measured full-width the open seal came out 1080px against the locked seal's 589,
        # so the cut read as two unrelated frames rather than one object opening.
        seal_column, _ = st.columns([1.15, 0.85], gap="large")
        with seal_column:
            wager = (
                f"{inv.call.value} · staked {inv.stake.label.lower()} (×{inv.stake.multiplier})"
                if inv.stake is not None and inv.call is not None
                else None
            )
            st.markdown(
                seal_panel(opened=True, tag=evidence_tag(inv.first), wager=wager),
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="pi-vlabel">Query v1 — Genie&rsquo;s first draft</div>'
            f"{verdict_chip(analysis.verdict, arrive=True)}",
            unsafe_allow_html=True,
        )
        st.iframe(
            render_query_panel(inv.first.sql, label="Query v1 — as Genie wrote it"),
            height=panel_height(inv.first.sql),
        )
        st.markdown(custody_line(inv.first), unsafe_allow_html=True)
        render_table(inv.first_result)

        # The chart that would have convinced them, with its own thumb on the scale
        # showing. Only two means are needed, so it appears here rather than after the
        # repair — the point is to catch the trick while the naive verdict still stands.
        chart = render_headline_chart(group_means(inv.first_result))
        if chart:
            st.iframe(chart, height=300)
    else:
        # Genie wrote no query, so steps 2 and 3 never happened. Say so plainly and give
        # this outcome the same verdict chip as any other, or it reads as the app
        # skipping steps or breaking.
        st.markdown(verdict_chip(analysis.verdict), unsafe_allow_html=True)
        st.markdown(
            "**There was no query to look at.** Genie could not turn that claim into a "
            "question this data can answer, so there was nothing to seal and nothing to "
            "predict. Working out that a claim *cannot* be checked with what you have is "
            "a real result — often a more useful one than an answer.",
        )

    st.markdown(
        f'<div class="pi-punch">{html.escape(analysis.reason)}</div>', unsafe_allow_html=True
    )

    if inv.can_repair:
        st.divider()
        # The case supplies both, because a typed claim and four different tricks cannot
        # share one argument. The wording here is the free-text default, and it is also
        # what the spread case says.
        nudge = inv.case.nudge if inv.case else DEFAULT_NUDGE
        label = inv.case.repair_label if inv.case else DEFAULT_REPAIR_LABEL
        st.markdown(nudge)
        cross_examine(inv, label)
    else:
        finish_button()


def beat_repaired(inv: Investigation) -> None:
    first, second = inv.first_analysis, inv.second_analysis
    assert first is not None and second is not None

    st.markdown(f'<h2 class="pi-claim">“{html.escape(inv.claim)}”</h2>', unsafe_allow_html=True)
    st.markdown(
        step_rail(4, "The same claim, a fairer query"),
        unsafe_allow_html=True,
    )

    # The flip, staged, before the evidence is laid out beneath it. Settled first so the
    # chips it counts up to are the run's real total; the additions it lights up are the
    # same token diff the side-by-side panels highlight, so the beat and the exhibit
    # cannot disagree about what changed.
    settlement = settle_into_run(inv)
    run = session_run()
    scored = next((c for c in run.calls if c.key == inv.run_key), None)
    added = [
        line.text.strip()
        for line in diff_tokens(
            inv.first.sql if inv.first else None, inv.second.sql if inv.second else None
        )
        if line.change is Change.ADDED
    ]
    st.iframe(
        render_slam(
            first=first.verdict,
            second=second.verdict,
            trick=inv.case.trick if inv.case and inv.case.turns_the_verdict else None,
            follow_up=inv.transcript[-1],
            added=added,
            settlement=settlement,
            stake_label=inv.stake.label if inv.stake else None,
            points_before=scored.points_before if scored else run.points,
            points_after=run.points,
        ),
        height=slam_height(),
    )
    # Land the player on the slam. They pressed the cross-examination a screen below where
    # this renders, and the beat that pays for the whole case must not play to nobody.
    if st.session_state.pop("scroll_to_flip", False):
        bring_into_view(SLAM_MARKER)

    # Column exhibits when the repair added columns; the weighting explanation when it
    # added a GROUP BY instead. A breakdown adds no column at all, so the column narrator
    # finds nothing and the paradox case reached this screen with no exhibits on it —
    # missing precisely the explanation that stops Simpson's paradox being a magic trick.
    exhibits = exhibits_for(
        inv.first.sql if inv.first else None,
        inv.second.sql if inv.second else None,
        inv.second_result,
        second,
    ) or weighting_exhibits(inv.second_result)

    left, right = st.columns(2, gap="large")
    with left:
        # The stamp only lands when the arithmetic says it should: lesson_landed is
        # exactly "v1 said HOLDS and v2 said BUSTED". When it does not, the same layout
        # plays a quieter line rather than a triumphal one it has not earned.
        stamp = '<span class="pi-stamp">Overturned</span>' if inv.lesson_landed else ""
        st.markdown(
            f'<div class="pi-vlabel">The first verdict</div>'
            f'<div class="pi-chiprow">{verdict_chip(first.verdict)}{stamp}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(render_sql(inv.first.sql if inv.first else None), unsafe_allow_html=True)
        st.markdown(custody_line(inv.first), unsafe_allow_html=True)
        render_table(inv.first_result)
    with right:
        st.markdown(
            f'<div class="pi-vlabel">The retrial — after your follow-up</div>'
            f'<div class="pi-chiprow">{verdict_chip(second.verdict)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            render_diff(
                inv.first.sql if inv.first else None,
                inv.second.sql if inv.second else None,
                exhibits,
            ),
            unsafe_allow_html=True,
        )
        # The strongest line in the app for "Genie is the engine": the id says this was
        # the same exchange continued, not a second question asked from scratch.
        st.markdown(
            custody_line(inv.second, continues=same_conversation(inv.first, inv.second)),
            unsafe_allow_html=True,
        )
        render_table(inv.second_result)

    st.markdown(
        f'<div class="pi-said">You asked: “{html.escape(inv.transcript[-1])}”</div>',
        unsafe_allow_html=True,
    )

    if exhibits:
        st.markdown(render_exhibits(exhibits), unsafe_allow_html=True)

    # Both pictures are offered to every case and drawn by whichever one the returned rows
    # can actually support — the same shape-not-case rule the judges follow. A breakdown
    # gets the reversal; a comparison with spreads gets the evidence room; a claim someone
    # typed gets whichever its rows happen to fit.
    subgroups, pooled = subgroup_rates(inv.second_result) if inv.second_result else ([], (0.0, 0.0))
    reversal = render_reversal(subgroups, pooled)
    if reversal:
        st.iframe(reversal, height=reversal_height(subgroups) + 150)

    # The band is the years the NAIVE query was asked about, so it is read off the first
    # turn's rows rather than the repaired ones. Without that the chart would draw the
    # whole run and quietly win the argument by leaving the window out — the same trick
    # in the other direction.
    full_series = series_points(inv.second_result)
    naive_years = [year for year, _ in series_points(inv.first_result)]
    series = render_window(
        full_series,
        window=(min(naive_years), max(naive_years)) if len(naive_years) >= 2 else None,
    )
    if series:
        st.iframe(series, height=window_height() + 150)

    # The app has been asserting "nearly everyone overlaps" in prose. This is the first
    # time a child can see it: the same dots, once where the averages put them and once
    # where they actually are.
    shapes = group_shapes(inv.second_result)
    cloud = render_cloud(shapes)
    if cloud:
        st.iframe(cloud, height=cloud_height(shapes) + 168)

    st.markdown(f'<div class="pi-punch">{html.escape(second.reason)}</div>', unsafe_allow_html=True)
    if inv.lesson_landed:
        st.info(
            "Same table, same claim, one more column — and the answer changed. "
            "That is why reading the query matters more than reading the answer."
        )

    # The payout in prose as well as in the slam above: the slam is a canvas nobody can
    # copy from or read with a screen reader, and the flow tests reach this line.
    if settlement is not None:
        st.markdown(payout_line(inv, settlement), unsafe_allow_html=True)
    finish_button()


def session_record() -> Record:
    """The wall, kept for as long as the browser tab is open and no longer.

    Persistence is ruled out, so this lives in session state beside the investigation.
    A wall that outlived the tab would need somewhere to live and someone to own it.
    """
    if "record" not in st.session_state:
        st.session_state.record = Record()
    return st.session_state.record


def session_tables(settings: Settings | None = None) -> list[DiscoveredTable]:
    """What the catalog holds, read once per session.

    The single cache both the docket and the mapping panel draw from. It exists because
    `Settings.readable_tables()` makes a live Unity Catalog call, and Streamlit re-runs
    this entire script on every widget interaction — so an uncached caller puts a network
    round-trip behind every button on the page. The mapping panel used to be exactly that
    caller, and opening its own expander paid for a fresh catalog read.

    `None` and `[]` are both cached: "the catalog could not be read" is an answer, and
    re-asking on every rerun would be slowest precisely when the workspace is unreachable.
    """
    if "tables" not in st.session_state:
        resolved = settings or Settings.from_env()
        st.session_state.tables = resolved.readable_tables()
    return st.session_state.tables


def session_docket(settings: Settings | None = None) -> list[Case]:
    """The docket this workspace can play, worked out once per session.

    The fallback is the curated docket rather than an empty list. A workspace the app
    cannot read should cost you discovery, not the product.
    """
    if "docket" not in st.session_state:
        resolved = settings or Settings.from_env()
        st.session_state.docket = build_docket(
            DOCKET, session_tables(resolved), discover=resolved.discover
        ) or list(DOCKET)
    return st.session_state.docket


def session_run() -> Run:
    """The score, for as long as the tab is open. Survives `start_over` on purpose: the
    run is the thing that spans cases, and a docket played for chips that reset between
    cases is five separate games."""
    if "run" not in st.session_state:
        st.session_state.run = Run()
    return st.session_state.run


def settle_into_run(inv: Investigation):
    """Settle this case's call onto the run, if a call was made. Returns the settlement
    or None. Safe to call from both the retrial and the receipt — `Run.close` returns the
    existing settlement on a repeat, and a case that skipped the retrial (a refusal, a
    typed claim Genie could not answer) still gets settled at the receipt."""
    if inv.call is None or inv.stake is None:
        return None
    # The first verdict as well as the final one: the run pays for the OVERTURNING, and it
    # cannot see that from the final verdict alone. A case that never reached a repair
    # passes the same verdict twice, which is exactly right — nothing was overturned.
    first = inv.first_analysis.verdict if inv.first_analysis else inv.verdict
    return session_run().close(
        inv.run_key,
        inv.call,
        inv.stake,
        first,
        inv.verdict,
        docket_size=len(session_docket()),
        estimate=estimate_result(inv),
    )


def estimate_result(inv: Investigation) -> EstimateResult | None:
    """Score the gap the player marked, against the gap the arithmetic found.

    Scored against the FIRST analysis, not the final one: the mark was placed while the
    naive query was the only thing on screen, so it is a prediction about that result and
    grading it against the repaired one would be moving the target after the shot.
    """
    if inv.guess is None or inv.case is None or inv.case.estimate is None:
        return None
    actual = verdict_gap(inv.first_analysis.delta if inv.first_analysis else None)
    if actual is None:
        return None
    return score_estimate(inv.guess, actual, inv.case.estimate)


def render_antibody_wall(record: Record) -> None:
    """Every trick met this session, named.

    Shown on the receipt rather than only at the very end, because a player who closes one
    case and stops should still leave with the thing worth keeping.
    """
    if not record.antibodies:
        return
    st.markdown(
        '<div class="pi-vlabel">What you now know to look for</div>'
        f'<div class="pi-wall-summary">{html.escape(record.summary())}</div>',
        unsafe_allow_html=True,
    )
    cards = "".join(
        f'<div class="pi-card">'
        f'<div class="pi-card-trick">{html.escape(a.trick)}</div>'
        f'<div class="pi-card-lesson">{html.escape(a.lesson)}</div>'
        f'<div class="pi-card-wild">Where you will meet it again: '
        f"{html.escape(a.in_the_wild)}</div></div>"
        for a in record.antibodies
    )
    st.markdown(f'<div class="pi-wall">{cards}</div>', unsafe_allow_html=True)


def beat_receipt(inv: Investigation) -> None:
    final = inv.final_analysis
    assert final is not None

    # Recorded once per case, on arrival at the receipt. `Record.add` is idempotent per
    # trick, so a rerun of this beat — and Streamlit reruns it on every interaction —
    # cannot stack the same card up.
    session_record().add(inv.case, inv.claim, final.verdict)
    settlement = settle_into_run(inv)

    st.markdown(step_rail(5, "Your receipt"), unsafe_allow_html=True)

    rows = [
        ("Queries written by Genie", str(inv.queries_written_by_genie)),
        ("Queries written by this app", "0"),
    ]
    if final.delta is not None:
        rows.append(("Gap found", f"{abs(final.delta):.1f}"))
    if final.pooled_spread is not None:
        rows.append(("Spread within groups", f"~{final.pooled_spread:.0f}"))
    if inv.call is not None and inv.stake is not None:
        rows.append(("Your call", f"{inv.call.value} · {inv.stake.label}"))
    if settlement is not None:
        rows.append(("Points", f"{settlement.points:+d}" if settlement.points else "no score"))

    body = "".join(f'<div class="pi-rrow"><span>{k}</span><span>{v}</span></div>' for k, v in rows)
    st.markdown(
        f'<div class="pi-receipt">{verdict_chip(final.verdict)}'
        f'<h2 class="pi-claim" style="margin:10px 0">“{html.escape(inv.claim)}”</h2>'
        f"{body}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="pi-punch">{html.escape(final.reason)}</div>', unsafe_allow_html=True)

    # The run so far: rank, score, and how often each level of confidence was borne out.
    # The share strip is plain text and spoiler-free — how you did, never which claim was
    # which — so it can be pasted anywhere without ruining the docket.
    run = session_run()
    if run.cases_called:
        rank = rank_for(run.points)
        upcoming = next_rank(run.points)
        # The ladder is what makes a score read as progress rather than a tally, so the
        # gap to the next rung is named whenever there is one.
        to_next = (
            f" · {upcoming.floor - run.points} to {upcoming.title}" if upcoming else " · top rank"
        )
        lines = " · ".join(
            f"{line.stake.label}: {line.right} of {line.made} right" for line in calibration(run)
        )
        st.markdown(
            f'<div class="pi-run"><div class="pi-vlabel">Case closed</div>'
            f'<div class="pi-rank">{html.escape(rank.title)}</div>'
            f'<div class="pi-runrow">{run.points} pts{html.escape(to_next)} · '
            f"{run.cases_called} of {len(session_docket())} cases</div>"
            f'<div class="pi-runrow">{html.escape(lines)}</div></div>',
            unsafe_allow_html=True,
        )
        st.code(f"Prove It · {rank.title} · {run.points} pts\n{run.share_strip()}", language=None)

    # R9: the receipt is meant to be a printable artifact of the investigation, so it
    # carries the queries themselves rather than a count of them. A child showing someone
    # what Genie wrote is the entire point of the exercise.
    for label, turn in (("Query v1", inv.first), ("Query v2", inv.second)):
        if turn is not None and turn.has_query:
            st.iframe(
                render_query_panel(turn.sql, label=f"{label} — written by Genie"),
                height=panel_height(turn.sql),
            )

    # Full identifiers, folded away. "Queries written by this app: 0" is the app marking
    # its own homework; these ids are the same claim made checkable against a record the
    # app does not own. It belongs here, at the end, and nowhere near the sealed screen.
    render_antibody_wall(session_record())

    panel = provenance_panel(inv)
    if panel:
        with st.expander("Where these queries came from"):
            st.markdown(panel, unsafe_allow_html=True)

    if st.button("Check another claim"):
        start_over()


def start_over() -> None:
    """Abandon the current investigation and go back to the claim screen."""
    st.session_state.pop("investigation", None)
    st.session_state.pop("finished", None)
    st.session_state.scroll_to_top = True
    st.rerun()


def finish_button() -> None:
    if st.button("Print my receipt", type="primary"):
        st.session_state.finished = True
        st.session_state.scroll_to_top = True
        st.rerun()


# -- entry ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Prove It", page_icon="🔎", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    settings = Settings.from_env()

    inv: Investigation | None = st.session_state.get("investigation")

    # Settle BEFORE the masthead draws, or the HUD shows the chips from the previous rerun
    # while the payout line beneath it announces new ones — which it did, on a live
    # screen. `settle_into_run` is idempotent, so the beats calling it again is harmless.
    if inv is not None and (inv.stage is Stage.REPAIRED or st.session_state.get("finished")):
        settle_into_run(inv)
    run = session_run()

    # The masthead: wordmark, plate, and the run's numbers, all in one navy bar across the
    # top of the sheet. The HUD lives here rather than in the page body because it is
    # instrumentation about the session, not content — and it is what makes the docket read
    # as one game rather than five separate pages.
    st.markdown(
        '<div class="pi-mast">'
        # The app's name is the page's one first-level heading. Before this the document
        # had no h1 at all, so a screen-reader user pressing "1" to jump to the top of the
        # content landed nowhere, and the heading outline started at level 2.
        '<h1 class="pi-logo">Prove<span>It</span></h1>'
        '<span class="pi-plate">THE EVIDENCE ROOM</span>'
        '<span class="pi-mast-spacer"></span>'
        f"{hud(run, len(session_docket())) if (inv is not None or run.cases_called) else ''}"
        f"{source_link(settings.source_url)}"
        "</div>",
        unsafe_allow_html=True,
    )
    if settings.offline:
        st.caption("Offline demo — replaying a recorded Genie conversation.")
    if st.session_state.pop("scroll_to_top", False):
        bring_into_view()

    # Reachable at every stage. A player who picks the wrong claim, or a teacher moving a
    # group along in a timed rotation, must not have to finish an investigation first.
    if inv is not None and st.button("← Back to the docket", key="start-over"):
        start_over()

    if inv is None:
        beat_claim(settings)
    elif st.session_state.get("finished"):
        beat_receipt(inv)
    elif inv.stage is Stage.INSTRUMENT:
        beat_instrument(inv)
    elif inv.stage is Stage.REVEALED:
        beat_reveal(inv)
    elif inv.stage is Stage.REPAIRED:
        beat_repaired(inv)
    else:
        # Stage.CLAIM with a stored investigation means ask_genie never ran. Fail loudly
        # rather than rendering a blank page, which is far harder to diagnose.
        raise AssertionError(f"Unhandled stage: {inv.stage}")


if __name__ == "__main__":
    main()
