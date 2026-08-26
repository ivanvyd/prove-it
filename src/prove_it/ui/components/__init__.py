"""Bidirectional Streamlit components — the ones that answer back.

Every other visual in this app renders through `st.iframe`, which is a one-way frame: it
can show, but nothing it does can reach Python. That is fine for a chart and useless for a
control.

`declare_component(path=...)` is the other kind. Streamlit serves the directory from the
app's own server and speaks a small postMessage protocol to it, so a component here can
send a value back and cause a rerun with that value in hand. The protocol is spoken by
hand in `index.html` — no npm, no React, no build step, and nothing fetched from outside,
which the product forbids and Free Edition's allowlist would block regardless.

The cost is real and worth stating: every value that comes back re-runs the entire
Streamlit script. Components here report on release, never on every frame of a drag.
"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_HERE = Path(__file__).resolve().parent

_gapmark = components.declare_component("prove_it_gapmark", path=str(_HERE / "gapmark"))


def gap_mark(
    *,
    prompt: str,
    lo: float,
    hi: float,
    lo_label: str,
    hi_label: str,
    theme: dict[str, str],
    unit: str = "",
    decimals: int = 1,
    fraction: float | None = None,
    key: str = "gapmark",
) -> dict | None:
    """Ask for a number by making the player place it, before any row is fetched.

    Returns `{"fraction": 0..1, "value": <in lo..hi>}` once the player has committed a
    mark, and `None` until then — so "has not answered" and "answered zero" stay
    different things, which matters because zero is a real answer to "how big is the
    gap".

    `fraction` is handed back in so the mark survives a rerun caused by anything else on
    the page.
    """
    return _gapmark(
        prompt=prompt,
        lo=lo,
        hi=hi,
        lo_label=lo_label,
        hi_label=hi_label,
        unit=unit,
        decimals=decimals,
        fraction=fraction,
        theme=theme,
        key=key,
        default=None,
    )
