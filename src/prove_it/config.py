"""Runtime configuration.

Free Edition gives one workspace and one warehouse, so there is very little to configure.
What is here exists so the app can run in three places: a laptop with no credentials
(offline), a laptop with a token (live), and Databricks Apps (live, service principal).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from prove_it.catalog import read_schema, space_tables
from prove_it.domain.discovery import DiscoveredTable
from prove_it.genie.client import DatabricksGenieClient, GenieClient
from prove_it.genie.fake import client_from_fixture, demo_client


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _tempo() -> float:
    """How fast the offline replay plays the recorded wait. 1.0 is real time; the video
    cut sets PROVE_IT_TEMPO=0.35 to keep the real phase order at a watchable pace."""
    raw = os.environ.get("PROVE_IT_TEMPO")
    if raw is None:
        return 1.0
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 1.0


@dataclass(frozen=True)
class Settings:
    offline: bool
    space_id: str | None
    fixture_path: str | None
    free_text: bool
    # Where to go looking for tables the docket could be built from. Defaults to this
    # project's own schema; point it anywhere and the app builds a docket out of what it
    # finds there instead.
    # Defaulted so every existing construction site keeps working: these three are how the
    # app behaves when nobody says otherwise, not decisions a caller has to make.
    catalog: str = "workspace"
    schema: str = "prove_it"
    # Generate cases from tables the curated docket does not cover. On by default, because
    # the alternative — five cases naming five tables a given workspace may not have — is
    # what made this app unusable outside the workspace it was written in.
    discover: bool = True
    # Where the masthead's source link points. The whole product's claim is that the app
    # never writes SQL, and the only way a judge can check that is to read the code — so the
    # link is chrome that carries an argument, not a courtesy. Configurable because a fork
    # pointing visitors at this repo would be claiming someone else's provenance for its own
    # docket; set it to empty and the link is not rendered at all.
    source_url: str = "https://github.com/ivanvyd/prove-it"

    @classmethod
    def from_env(cls) -> Settings:
        # Databricks Apps injects the Genie space resource under this name when the app
        # declares it in app.yaml with valueFrom.
        space_id = os.environ.get("GENIE_SPACE_ID") or os.environ.get("DATABRICKS_GENIE_SPACE_ID")
        return cls(
            offline=_flag("PROVE_IT_OFFLINE", default=not space_id),
            space_id=space_id,
            fixture_path=os.environ.get("PROVE_IT_FIXTURE"),
            # Flipped to False if the day-one probe shows free-text claims are unreliable;
            # the curated deck then becomes the only input. See R11 in docs/requirement.md.
            free_text=_flag("PROVE_IT_FREE_TEXT", default=True),
            catalog=os.environ.get("PROVE_IT_CATALOG", "workspace"),
            schema=os.environ.get("PROVE_IT_SCHEMA", "prove_it"),
            discover=_flag("PROVE_IT_DISCOVER", default=True),
            source_url=os.environ.get("PROVE_IT_SOURCE_URL", cls.source_url),
        )

    def readable_tables(self) -> list[DiscoveredTable]:
        """What the catalog says is there.

        Narrowed to what the Genie space can actually query, because those are two
        different sets: discovery reads the catalog, and Genie answers only about the
        tables its space declares. A case built on a table outside the space cannot be
        answered — the query comes back refused and the player is left wondering what they
        did wrong. Better never to offer it.

        The narrowing is skipped when the space cannot be read, which means "cannot check"
        rather than "nothing is allowed". Empty offline, and empty on any failure.
        """
        if self.offline or self.fixture_path:
            return []
        try:
            from databricks.sdk import WorkspaceClient

            client = WorkspaceClient()
            tables = read_schema(client, self.catalog, self.schema)
            allowed = space_tables(client, self.space_id) if self.space_id else set()
            if allowed:
                tables = [t for t in tables if t.full_name in allowed]
            return tables
        except Exception:  # noqa: BLE001 - a docket is better than a stack trace
            return []

    def build_client(self, case_key: str | None = None) -> GenieClient:
        """The client for one investigation.

        `case_key` only matters offline, where each case replays its own recorded
        conversation. Live, Genie is asked the claim and answers it.
        """
        if self.fixture_path:
            return _paced(client_from_fixture(self.fixture_path))
        if self.offline or not self.space_id:
            return _paced(demo_client(case_key))
        return DatabricksGenieClient(space_id=self.space_id)


def _paced(client: GenieClient) -> GenieClient:
    """Give an offline client a real sleep, scaled by tempo, so the recorded wait plays
    at a watchable pace instead of resolving instantly. A tempo of 0 makes it instant,
    which is what the tests want and what a headless probe does not care about."""
    tempo = _tempo()
    if tempo > 0 and hasattr(client, "sleep"):
        client.sleep = lambda seconds: time.sleep(seconds * tempo)  # type: ignore[attr-defined]
    return client


# Rumours children actually repeat. Used as the suggestion chips, and as the whole input
# surface if free text has to be switched off.
RUMOUR_DECK = [
    "Boys are better at maths",
    "Girls are better at reading",
    "Pupils at bigger schools score higher",
    "Kids with phones read worse",
    "Scores went down after 2020",
    "Our region is the poorest",
]
