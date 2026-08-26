"""Test-wide defaults.

The offline replay paces the recorded Genie wait so the interrogation room plays at a
watchable speed. That is right in the app and wrong in a test: a flow test that drives the
real app through AppTest would otherwise sleep through a ~20s recorded timeline per turn.
Pinning the tempo to zero makes the replay instant everywhere unless a test opts back in.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _instant_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVE_IT_TEMPO", "0")
