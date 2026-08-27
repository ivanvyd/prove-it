"""Prove It — the Evidence Room, in a Databricks App.

Two scenes, the way the design file draws them. The archive: a dark room, a desk, and the
case files lying on it as folders. The board: one case pinned to a corkboard — the claim,
Genie's reasoning, the search warrant carrying its query, the sealed result — with the desk
under it holding whichever panel the case has reached: the wager, the review, the retrial,
the closed case.

The view holds no logic worth testing: it renders what `Investigation` decided. That is
deliberate, because the interesting rules — when rows may be fetched, what counts as a call,
how a verdict is reached — belong where a test can reach them.
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
from prove_it.domain.custody import custody_of
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
    Call,
    Outcome,
    Run,
    Stake,
    calibration,
    next_rank,
    rank_for,
)
from prove_it.domain.record import Record
from prove_it.domain.verdict import Verdict, series_points, subgroup_rates
from prove_it.session import Investigation, Stage
from prove_it.ui.archive import (
    ARCHIVE_CSS,
    archive_script,
    folder,
    footer,
    header_bar,
    hero,
    own_folder,
)
from prove_it.ui.board import board_height, phase_of, render_board
from prove_it.ui.components import gap_mark
from prove_it.ui.desk import (
    CLOSE_LINE,
    DESK_CSS,
    FLIP_LINE,
    case_bar,
    props,
    seal_hint,
    slate,
    under,
    wager_head,
)
from prove_it.ui.headline_chart import render_headline_chart
from prove_it.ui.interrogation import phase_for, render_room, room_height
from prove_it.ui.kit import (
    KIT_CSS,
    antibody_card,
    copy_frame,
    share_caption,
    share_card,
    share_svg,
)
from prove_it.ui.pupil_cloud import cloud_height, render_cloud
from prove_it.ui.query_panel import panel_height, render_query_panel
from prove_it.ui.render import (
    bring_into_view,
    estimate_line,
    provenance_panel,
    render_exhibits,
    render_table,
    verdict_chip,
)
from prove_it.ui.reversal_chart import chart_height as reversal_height
from prove_it.ui.reversal_chart import render_reversal
from prove_it.ui.style import CSS, DEFAULT_NUDGE, DEFAULT_REPAIR_LABEL, FONT_LINK, FRAME_THEME
from prove_it.ui.window_chart import chart_height as window_height
from prove_it.ui.window_chart import render_window

OFFLINE_NOTE = "Offline demo — replaying a recorded Genie conversation"

# -- scene one: the archive -----------------------------------------------------------


def render_folder(case: Case, index: int, *, up_next: bool, closed: Verdict | None) -> bool:
    """One case on the desk. Returns True when it is picked.

    The folder is the click target, as in the design: the real button lies over it,
    invisible but present, so a screen reader hears "Open case 3 — The paradox" and a
    keyboard reaches it.
    """
    st.markdown(folder(case, index, up_next=up_next, closed=closed), unsafe_allow_html=True)
    return st.button(
        f"Open case {index + 1} — {case.title}", key=f"case-{case.key}", width="stretch"
    )


def render_own_folder() -> bool:
    st.markdown(own_folder(), unsafe_allow_html=True)
    return st.button("Open case 0 — bring your own rumour", key="case-own", width="stretch")


def closed_verdicts(run: Run) -> dict[str, Verdict]:
    """Which cases were called this session, and what each reached — for the stamps."""
    return {call.key: call.verdict for call in run.calls}


def run_with_room(call, label: str, *, slot=None):
    """Run one Genie turn while showing the interrogation room instead of a spinner.

    `call` takes an `on_status(status, elapsed)` callback and does the Genie work. Each
    status paints the room into a single `st.empty()` slot; because the room's clock is
    derived from a start epoch it keeps running smoothly even though the slot is rewritten
    on every phase. `label` is the accessible caption on the room, the one line a screen
    reader gets where a sighted user gets the board.
    """
    # The caller may hand in a slot it created at a path that exists on EVERY run.
    # Making one here on only some runs shifts every later element's path, and Streamlit
    # matches keyed containers by path — the shifted run then duplicates the desk and
    # leaves the old one behind as a permanently dimmed zombie.
    slot = st.empty() if slot is None else slot
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
                render_room(phase=phase, started_at_ms=started_ms, done=False),
                height=room_height(),
            )

    on_status("PENDING", 0.0)
    result = call(on_status)
    with slot.container():
        st.caption(label)
        st.iframe(
            render_room(phase="DONE", started_at_ms=started_ms, done=True), height=room_height()
        )
    return result


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


def beat_archive(settings: Settings) -> None:
    docket = session_docket(settings)
    run = session_run()
    record = session_record()
    st.markdown(
        '<span class="pi-archive"></span>'
        + header_bar(
            run, kit=len(record.antibodies), docket_size=len(docket), source_url=settings.source_url
        ),
        unsafe_allow_html=True,
    )
    st.markdown(hero(len(docket)), unsafe_allow_html=True)

    closed = closed_verdicts(run)
    up_next = next((case.key for case in docket if case.key not in closed), None)
    chosen: Case | None = None
    claim = ""

    # One wrapping row: the design's drawer, which lays four abreast and lets the fifth
    # fall to the next line. Streamlit columns are made to wrap by the archive's CSS.
    columns = st.columns(len(docket) + (1 if settings.free_text else 0), gap="small")
    for index, case in enumerate(docket):
        with columns[index]:
            if render_folder(case, index, up_next=case.key == up_next, closed=closed.get(case.key)):
                chosen = case
    if settings.free_text:
        with columns[-1]:
            if render_own_folder():
                st.session_state.own_open = not st.session_state.get("own_open", False)
                st.rerun()
        if st.session_state.get("own_open"):
            # A form, so the claim is only sent when it is submitted. A bare text_input
            # returns its value on every rerun, which would fire a Genie call at whatever
            # had been typed so far.
            with st.form("claim-form", clear_on_submit=False):
                typed = st.text_input(
                    "Your rumour",
                    placeholder="write your own rumour here .........",
                    label_visibility="collapsed",
                )
                if st.form_submit_button("Test it", type="primary") and typed.strip():
                    claim = typed.strip()
            st.markdown(
                '<div class="pi-own-note">Most typed claims end in &ldquo;can&rsquo;t tell&rdquo; '
                "&mdash; the data has no column for them. That is a win, not a failure.</div>",
                unsafe_allow_html=True,
            )

    st.markdown(footer(OFFLINE_NOTE if settings.offline else None), unsafe_allow_html=True)
    mapping_panel(settings, docket)
    st.iframe(archive_script(), height=1)

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

    # The room renders here, once, directly after the drawer — not inside the column of
    # the folder that was clicked. Writing into a container created inside a column AFTER
    # the loop has emitted later columns makes Streamlit re-emit that column's block, and
    # the docket grew a second, greyed-out copy of the case below the real one.
    run_with_room(investigation.ask_genie, "Genie is working out how to check that…")
    st.session_state.investigation = investigation
    st.session_state.scroll_to_top = True
    st.session_state.scene_enter = True
    st.rerun()


# -- scene two: the board -------------------------------------------------------------


def case_number(inv: Investigation) -> int:
    """The case's number on the docket, one-based; 0 for a rumour someone typed."""
    if inv.case is None:
        return 0
    for index, case in enumerate(session_docket()):
        if case.key == inv.case.key:
            return index + 1
    return 0


def gap_estimate(inv: Investigation) -> float | None:
    """Ask the player to place the gap before the seal breaks, and remember where.

    Returns the value in the case's own units, or None when this case does not ask or the
    player has not marked one — untouched has to stay distinguishable from zero, because
    "no gap at all" is a real answer and on the maths case very nearly the right one.

    The mark is held in session state and handed back to the component on every render,
    because a Streamlit rerun triggered by anything else on this screen — picking a slip,
    most obviously — rebuilds the iframe from scratch and would otherwise wipe it.
    """
    if inv.case is None or inv.case.estimate is None:
        return None
    spec = inv.case.estimate
    slot = f"guess-{inv.run_key}"
    held = st.session_state.get(slot)

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
    return float(held["value"]) if held else None


def wager_panel(inv: Investigation) -> None:
    """THE WAGER: pick a slip, stake a coin, break the seal.

    The design's three-step wager. The slip and the coin are choices held in session
    state; only the seal commits, and it stays dim until both are on record — which is
    what makes the call cost something before any row is fetched.
    """
    pick_slot, stake_slot = f"pick-{inv.run_key}", f"stake-{inv.run_key}"
    picked = st.session_state.get(pick_slot)
    staked = st.session_state.get(stake_slot)
    # "The data can't say" is a call only on a claim the player typed. Every docket case
    # was probed to a verdict, so there it would be a slip that only ever loses.
    calls = [Call.HOLDS_UP, Call.TRICK] + ([Call.CANT_SAY] if inv.case is None else [])

    st.markdown(wager_head("Does this claim survive a <b>fair</b> check?"), unsafe_allow_html=True)

    # Two columns, the way a desk lays it out: the call on the left — slips, then the
    # estimate — and the stake on the right, coins over the seal. Wide, not tall: a
    # single-column tower left the panel three screens deep with the seal at the bottom.
    # On a narrow screen Streamlit stacks the columns and the tower returns, which is
    # right on a phone.
    slips_col, stake_col = st.columns([1.45, 1], gap="large")
    with slips_col:
        for call in calls:
            on = picked == call.name
            with st.container(key=f"slip-{call.name}-{'on' if on else 'off'}"):
                if st.button(call.value, key=f"pick-{call.name}", width="stretch"):
                    st.session_state[pick_slot] = call.name
                    st.rerun()
        guess = gap_estimate(inv)

    with stake_col:
        st.markdown('<div class="pi-stake-label">Stake</div>', unsafe_allow_html=True)
        # A horizontal container rather than st.columns(3): three equal columns each took
        # a third of the panel and left the coins spread edge to edge. A centred
        # horizontal row keeps them a tight group.
        with st.container(key="coins", horizontal=True, horizontal_alignment="center", gap="small"):
            for option in Stake:
                on = staked == option.name
                with st.container(key=f"coin-{option.name}-{'on' if on else 'off'}"):
                    if st.button(
                        f"{option.label} **×{option.multiplier}**", key=f"stake-{option.name}"
                    ):
                        st.session_state[stake_slot] = option.name
                        st.rerun()
        st.markdown(
            '<div class="pi-stake-note">Sure &amp; wrong is the expensive kind of wrong</div>',
            unsafe_allow_html=True,
        )

        ready = picked is not None and staked is not None
        with st.container(key="seal"):
            if st.button("Break the seal", key="break-seal", disabled=not ready):
                assert picked is not None and staked is not None
                inv.commit_call(Call[picked], Stake[staked], guess)
                st.session_state.scroll_to_top = True
                st.rerun()
        hint = seal_hint(picked=picked is not None, staked=staked is not None)
        st.markdown(f'<div class="pi-seal-hint">{hint}</div>', unsafe_allow_html=True)


def call_chit(inv: Investigation) -> str:
    """The call, standing, as the design's torn chit. At this beat a "trick" call looks
    lost and a "holds up" call looks won, and neither is settled: the first verdict is the
    witness's testimony and the cross-examination decides."""
    if inv.call is None or inv.stake is None:
        return ""
    standing = " &mdash; the cross-examination decides" if inv.can_repair else ""
    return (
        f'<div class="pi-chit">Called: {html.escape(inv.call.value)} &middot; '
        f"staked &times;{inv.stake.multiplier}{standing}</div>"
    )


def cross_examine(inv: Investigation, label: str) -> None:
    """The follow-up, in the player's own words if they want it.

    Pre-filled rather than blank on purpose. The suggested wording is what the probe
    measured producing the repaired query on live Genie, so accepting it keeps the
    docket's arcs reliable; a blank box would make every case a coin-flip on phrasing.
    The words go into the question, Genie writes the query — the app still writes no SQL.
    """
    default = inv.case.follow_up if inv.case else repair_question()
    with st.form(f"repair-{inv.run_key}", clear_on_submit=False):
        asked = st.text_input(
            "Ask Genie a fairer question",
            value=default,
            label_visibility="collapsed",
            key=f"repair-text-{inv.run_key}",
        )
        submitted = st.form_submit_button(f"{label} →")
    st.markdown(under(FLIP_LINE), unsafe_allow_html=True)
    if submitted:
        # The repair does not run here. `run_with_room` reruns from inside this panel, and a
        # rerun from a nested container to the same scene leaves this panel's elements orphaned
        # in the DOM behind the retrial's — two desks stacked. Stashed and run at the top of
        # `beat_case` instead, where the room replaces the whole desk cleanly, the way
        # `ask_genie` runs at the top of the archive.
        st.session_state.repairing = asked
        st.rerun()


def review_panel(inv: Investigation) -> None:
    """SEAL BROKEN · REVIEW: is that a fair way to check it? Then cross-examine."""
    nudge = inv.case.nudge if inv.case else DEFAULT_NUDGE
    question, _, rest = nudge.partition("** ")
    question = question.strip("* ")
    left, right = st.columns([1.6, 1], gap="medium")
    with left:
        st.markdown(call_chit(inv) + estimate_line(inv), unsafe_allow_html=True)
        if inv.can_repair:
            st.markdown(
                f'<div class="pi-review-q">{html.escape(question)}</div>'
                f'<div class="pi-review-t">{html.escape(rest.strip())}</div>',
                unsafe_allow_html=True,
            )
        else:
            reason = inv.first_analysis.reason if inv.first_analysis else ""
            st.markdown(
                '<div class="pi-review-q">There was no query to look at.</div>'
                f'<div class="pi-review-t">{html.escape(reason)} Working out that a claim '
                "<strong>cannot</strong> be checked with what you have is a real result "
                "&mdash; often a more useful one than an answer.</div>",
                unsafe_allow_html=True,
            )
    with right:
        if inv.can_repair:
            label = inv.case.repair_label if inv.case else DEFAULT_REPAIR_LABEL
            cross_examine(inv, label)
        else:
            close_button(inv)


def close_button(inv: Investigation) -> None:
    number = case_number(inv)
    label = f"Close the case — mint antibody Nº {number}" if number else "Close the case"
    if st.button(label, key="close-case", type="primary", width="stretch"):
        st.session_state.finished = True
        st.session_state.scroll_to_top = True
        st.rerun()
    st.markdown(under(CLOSE_LINE), unsafe_allow_html=True)


def retrial_panel(inv: Investigation, settlement) -> None:
    """RETRIAL · VERDICT FLIPPED: what the fair query did, and what it paid."""
    second = inv.second_analysis
    left, right = st.columns([1.6, 1], gap="medium")
    with left:
        chits = ""
        if settlement is not None:
            if settlement.outcome is Outcome.VOID:
                chits = (
                    '<div class="pi-chit pi-chit--void">The data could not rule &mdash; '
                    "nothing scored, nothing lost</div>"
                )
            else:
                chits = "".join(
                    f'<div class="pi-chit">{a.points:+d} {html.escape(a.label)}</div>'
                    for a in settlement.awards
                )
        if inv.lesson_landed:
            line = "Same table, same claim, one more column &mdash; and the answer changed."
            sub = (
                f"{html.escape(second.reason) if second else ''} That is why you read the "
                "query, not the answer."
            )
        else:
            line = "Same table, same claim, a fairer query &mdash; and the answer stood."
            sub = html.escape(second.reason) if second else ""
        st.markdown(
            f'{chits}<div class="pi-retrial-line">{line}</div>'
            f'<div class="pi-retrial-sub">{sub}</div>',
            unsafe_allow_html=True,
        )
    with right:
        close_button(inv)


def closed_panel(inv: Investigation) -> None:
    number = case_number(inv)
    label, tone = verdict_chip_text(inv.verdict)
    case = f"Case N&ordm; {number:02d}" if number else "Your case"
    left, right = st.columns([1.6, 1], gap="medium")
    with left:
        st.markdown(
            f'<div class="pi-closed-line">{case} closed &mdash; <span class="v {tone}">'
            f"{html.escape(label)}.</span> The trick is in your kit now.</div>",
            unsafe_allow_html=True,
        )
    with right:
        if st.button("Return to the archive →", key="return", width="stretch"):
            start_over()


def verdict_chip_text(verdict: Verdict) -> tuple[str, str]:
    from prove_it.ui.style import VERDICT_TEXT  # noqa: PLC0415

    return VERDICT_TEXT[verdict]


def exhibits_below(inv: Investigation, exhibits) -> None:
    """The pictures the retrial produced, pinned below the desk: the added columns, and
    whichever chart the returned rows can support — a breakdown gets the reversal, a
    comparison with spreads gets the cloud, a run of years gets the window."""
    if exhibits:
        st.markdown(
            '<div class="pi-vlabel">What the added columns showed</div>', unsafe_allow_html=True
        )
        st.markdown(render_exhibits(exhibits), unsafe_allow_html=True)
    subgroups, pooled = subgroup_rates(inv.second_result) if inv.second_result else ([], (0.0, 0.0))
    reversal = render_reversal(subgroups, pooled)
    if reversal:
        st.iframe(reversal, height=reversal_height(subgroups) + 150)
    full_series = series_points(inv.second_result)
    naive_years = [year for year, _ in series_points(inv.first_result)]
    series = render_window(
        full_series,
        window=(min(naive_years), max(naive_years)) if len(naive_years) >= 2 else None,
    )
    if series:
        st.iframe(series, height=window_height() + 150)
    shapes = group_shapes(inv.second_result)
    cloud = render_cloud(shapes)
    if cloud:
        st.iframe(cloud, height=cloud_height(shapes) + 168)


def headline_below(inv: Investigation) -> None:
    """The chart that would have convinced them, with its own thumb on the scale showing.
    Only two means are needed, so it appears at the reveal — the point is to catch the
    trick while the naive verdict still stands."""
    # No page label over this one: the sheet opens with its own header, and Streamlit
    # measured the label's box at 2px here, which slid the text under the sheet.
    chart = render_headline_chart(group_means(inv.first_result))
    if chart:
        st.iframe(chart, height=300)


def receipt_below(inv: Investigation, settlement) -> None:
    """The printed artifact you leave with, laid on the desk under the closed case: what
    was found, the run so far, both queries in full, every trick met, and the ledger of
    ids a judge can check against Genie's own history."""
    final = inv.final_analysis
    assert final is not None
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
    st.markdown('<div class="pi-vlabel">Your receipt</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pi-receipt">{verdict_chip(final.verdict)}'
        f'<h2 class="pi-claim" style="margin:10px 0">“{html.escape(inv.claim)}”</h2>'
        f"{body}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="pi-punch">{html.escape(final.reason)}</div>', unsafe_allow_html=True)

    # The run so far: rank, score, streak, and how often each level of confidence was
    # borne out. The share strip is plain text and spoiler-free — how you did, never which
    # claim was which — so it can be pasted anywhere without ruining the docket.
    run = session_run()
    if run.cases_called:
        rank = rank_for(run.points)
        upcoming = next_rank(run.points)
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
            f"{run.cases_called} of {len(session_docket())} cases · streak {run.streak}</div>"
            f'<div class="pi-runrow">{html.escape(lines)}</div></div>',
            unsafe_allow_html=True,
        )
        st.code(f"Prove It · {rank.title} · {run.points} pts\n{run.share_strip()}", language=None)

    # R9: the receipt carries the queries themselves rather than a count of them. A child
    # showing someone what Genie wrote is the entire point of the exercise. The rows the
    # board could not hold are here in full.
    for label, turn, table in (
        ("Query v1", inv.first, inv.first_result),
        ("Query v2", inv.second, inv.second_result),
    ):
        if turn is not None and turn.has_query:
            st.iframe(
                render_query_panel(turn.sql, label=f"{label} — written by Genie"),
                height=panel_height(turn.sql),
            )
            render_table(table)

    render_antibody_wall(session_record())
    panel = provenance_panel(inv)
    if panel:
        with st.expander("Where these queries came from"):
            st.markdown(panel, unsafe_allow_html=True)


def kit_overlay(inv: Investigation) -> None:
    """The minted card over the board, then the share card. Pinning it puts it away."""
    number = case_number(inv)
    docket = session_docket()
    run = session_run()
    called = {c.key for c in run.calls}
    kit = []
    for index, case in enumerate(docket):
        state = (
            "this"
            if inv.case and case.key == inv.case.key
            else ("done" if case.key in called else "open")
        )
        kit.append((index + 1, state))
    kit.append((0, "own"))
    if inv.case is not None:
        trick, lesson, wild = inv.case.trick, inv.case.lesson, inv.case.in_the_wild
    else:
        trick, lesson, wild = (
            verdict_chip_text(inv.verdict)[0],
            inv.final_analysis.reason if inv.final_analysis else "",
            "Any rumour the data has no column for.",
        )
    if st.session_state.get("share_open"):
        record = custody_of(inv.first)
        conversation = record.short_conversation if record else "—"
        args = dict(
            number=number,
            claim=inv.claim,
            trick=trick,
            reason=inv.final_analysis.reason if inv.final_analysis else "",
            verdict=inv.verdict,
            real_data=inv.case.real_data if inv.case else False,
            queries=inv.queries_written_by_genie,
            flipped=inv.lesson_landed,
            conversation=conversation,
        )
        st.markdown(share_card(**args), unsafe_allow_html=True)
        with st.container(key="share-actions"):
            a, b, c = st.columns(3)
            with a:
                st.download_button(
                    "Download the card",
                    data=share_svg(**args),
                    file_name=f"prove-it-case-{number:02d}.svg",
                    mime="image/svg+xml",
                    key="share-download",
                )
            with b:
                st.iframe(
                    copy_frame(share_caption(claim=inv.claim, trick=trick, verdict=inv.verdict)),
                    height=48,
                )
            with c, st.container(key="share-back"):
                if st.button("← Back to the card", key="share-back-btn"):
                    st.session_state.share_open = False
                    st.rerun()
        return
    st.markdown(
        antibody_card(
            number=number,
            case=inv.case,
            trick=trick,
            lesson=lesson,
            wild=wild,
            verdict=inv.verdict,
            kit=kit,
        ),
        unsafe_allow_html=True,
    )
    with st.container(key="kit-actions"):
        a, b = st.columns(2)
        with a:
            if st.button("Share the case card →", key="kit-share", type="primary"):
                st.session_state.share_open = True
                st.rerun()
        with b:
            if st.button("Pin it to the kit →", key="kit-pin"):
                st.session_state.card_pinned = True
                st.rerun()


def beat_case(inv: Investigation, settings: Settings, *, finished: bool) -> None:
    # A slot that exists on EVERY run of this beat, repair or not, so the elements after
    # it keep the same paths run over run. The follow-up renders the interrogation room
    # into it while Genie works, then FALLS THROUGH — no st.rerun(), and no extra
    # elements: either would shift or abandon paths, and Streamlit matches keyed
    # containers by path, which is exactly how the review desk survived as a permanently
    # dimmed zombie above the retrial. Repairing mutates inv.stage in place, so this very
    # run carries on and renders the retrial clean; the scroll iframe takes the room's
    # place inside the same slot.
    room_slot = st.empty()
    asked = st.session_state.pop("repairing", None)
    if asked is not None and inv.stage is Stage.REVEALED:
        run_with_room(
            lambda on_status: inv.repair(on_status, asked=asked),
            "Genie is rewriting the query…",
            slot=room_slot,
        )
        with room_slot:
            bring_into_view()

    phase = phase_of(inv, finished=finished)
    number = case_number(inv)
    run = session_run()
    settlement = settle_into_run(inv) if phase in ("retrial", "closed") else None
    scored = next((c for c in run.calls if c.key == inv.run_key), None)
    promoted = (
        scored is not None and rank_for(scored.points_before).title != rank_for(run.points).title
    )
    title = inv.case.title if inv.case else "Your own rumour"
    exhibits = (
        exhibits_for(
            inv.first.sql if inv.first else None,
            inv.second.sql if inv.second else None,
            inv.second_result,
            inv.second_analysis,
        )
        or weighting_exhibits(inv.second_result)
        if phase in ("retrial", "closed") and inv.second_analysis is not None
        else []
    )
    if finished:
        # Recorded once per case, on closing. `Record.add` is idempotent per trick, so a
        # rerun of this beat cannot stack the same card up.
        session_record().add(inv.case, inv.claim, inv.verdict)

    # The bar.
    back, bar = st.columns([1, 9], gap="small")
    with back:
        if st.button("← The archive", key="start-over"):
            start_over()
    with bar:
        st.markdown(
            case_bar(
                number=number,
                title=title,
                claim=inv.claim,
                points=run.points,
                rank=rank_for(run.points),
                promoted=promoted,
                source_url=settings.source_url,
            ),
            unsafe_allow_html=True,
        )

    # The board.
    st.iframe(
        render_board(inv, number=number, phase=phase, exhibits=exhibits),
        height=board_height(phase),
    )

    # The desk.
    gain = settlement.points if settlement is not None else 0
    slate_phase = phase if phase != "retrial" or inv.lesson_landed else "retrial-stood"
    with st.container(key="desk"):
        left, middle, right = st.columns([1.1, 3.4, 1.4], gap="medium")
        with left:
            st.markdown(
                slate(number=number, title=title, phase=slate_phase, gain=gain),
                unsafe_allow_html=True,
            )
        # Keyed by phase, so Streamlit treats each phase's panel as its own subtree and
        # swaps it whole. With one stable key the review panel's elements were kept in the
        # DOM behind the retrial's — two desks stacked — because Streamlit diffs by path and
        # matched the old children to the new ones. `run_with_room` reruns from inside this
        # container, which is what surfaced it.
        with middle, st.container(key=f"panel-{phase}"):
            if phase == "wager":
                wager_panel(inv)
            elif phase == "revealed":
                review_panel(inv)
            elif phase == "retrial":
                retrial_panel(inv, settlement)
            else:
                closed_panel(inv)
        with right:
            st.markdown(props(), unsafe_allow_html=True)

    # What lies below.
    with st.container(key="below"):
        if phase == "revealed":
            headline_below(inv)
        if phase in ("retrial", "closed"):
            exhibits_below(inv, exhibits)
        if phase == "closed":
            receipt_below(inv, settlement)

    if finished and not st.session_state.get("card_pinned"):
        kit_overlay(inv)


# -- session ---------------------------------------------------------------------------


def session_record() -> Record:
    """The kit, kept for as long as the browser tab is open and no longer.

    Persistence is ruled out, so this lives in session state beside the investigation.
    A kit that outlived the tab would need somewhere to live and someone to own it.
    """
    if "record" not in st.session_state:
        st.session_state.record = Record()
    return st.session_state.record


def session_tables(settings: Settings | None = None) -> list[DiscoveredTable]:
    """What the catalog holds, read once per session.

    The single cache both the docket and the mapping panel draw from. It exists because
    `Settings.readable_tables()` makes a live Unity Catalog call, and Streamlit re-runs
    this entire script on every widget interaction — so an uncached caller puts a network
    round-trip behind every button on the page.

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
    or None. Safe to call from both the retrial and the closed case — `Run.close` returns
    the existing settlement on a repeat, and a case that skipped the retrial (a refusal, a
    typed claim Genie could not answer) still gets settled when it closes."""
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


def start_over() -> None:
    """Put the case back and return to the archive."""
    st.session_state.pop("investigation", None)
    for flag in ("finished", "card_pinned", "share_open"):
        st.session_state.pop(flag, None)
    st.session_state.scroll_to_top = True
    st.session_state.scene_enter = True
    st.rerun()


# -- entry ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Prove It", page_icon="🔎", layout="wide")
    # One call per sheet, each beginning on its own line with its own <style>. Joined into
    # one string, the font links on the first line turned the rest into a paragraph and
    # the page opened on two thousand pixels of stylesheet printed as prose.
    for sheet in (FONT_LINK, CSS, ARCHIVE_CSS, DESK_CSS, KIT_CSS):
        st.markdown(sheet, unsafe_allow_html=True)
    settings = Settings.from_env()

    inv: Investigation | None = st.session_state.get("investigation")
    finished = bool(st.session_state.get("finished"))

    # Settle BEFORE anything draws, or the bar shows the points from the previous rerun
    # while the chit beneath it announces new ones — which it did, on a live screen.
    # `settle_into_run` is idempotent, so the beats calling it again is harmless.
    if inv is not None and (inv.stage is Stage.REPAIRED or finished):
        settle_into_run(inv)

    if st.session_state.pop("scene_enter", False):
        # The design swaps scenes by fading the new one in from slightly too large. The
        # marker lasts one render, so a stake click does not replay the arrival.
        st.markdown('<span class="pi-scene-enter"></span>', unsafe_allow_html=True)
    if st.session_state.pop("scroll_to_top", False):
        bring_into_view()

    if inv is None:
        beat_archive(settings)
    elif inv.stage in (Stage.INSTRUMENT, Stage.REVEALED, Stage.REPAIRED):
        beat_case(inv, settings, finished=finished)
    else:
        # Stage.CLAIM with a stored investigation means ask_genie never ran. Fail loudly
        # rather than rendering a blank page, which is far harder to diagnose.
        raise AssertionError(f"Unhandled stage: {inv.stage}")


if __name__ == "__main__":
    main()
