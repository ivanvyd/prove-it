"""Reading what the workspace actually contains, without asking it a question.

Unity Catalog will describe every table in a schema — names and types — through its own
API, in one call, with no warehouse involved. That matters three times over.

It is **not SQL**, so it does not touch the rule this entry is built on: the app composes
no query, and `tests/test_no_sql_in_app_code.py` fails the build if it ever does. Asking
"what columns exist" through the catalog is a different act from asking "what is in them",
and only the second one needs Genie.

It is **free and instant**. A discovery pass that profiled values would need the warehouse
awake and would cost a query per table; this costs one metadata call and works while the
warehouse is cold.

And it is **the honest division of labour**. This app decides what is worth asking. Genie
decides how to ask it. Reading the catalog is the first half; it never becomes the second.

Failure here is never fatal. A workspace the app cannot read, or credentials it does not
have, means an empty list and a docket built from whatever else is available — the curated
cases, offline fixtures, or nothing at all. Losing discovery must not lose the app.
"""

from __future__ import annotations

import logging

from prove_it.domain.discovery import DiscoveredColumn, DiscoveredTable

log = logging.getLogger(__name__)


def _column(raw: object) -> DiscoveredColumn:
    name = getattr(raw, "name", "") or ""
    type_name = getattr(raw, "type_name", None)
    # The SDK hands back an enum whose `str()` is `ColumnTypeName.DOUBLE`; the classifier
    # wants the bare word. `.value` when it is an enum, the string itself when it is not,
    # because a fixture or an older SDK may hand over either.
    text = getattr(type_name, "value", type_name)
    return DiscoveredColumn(name=name, type_name=str(text or ""))


SPACE_PATH = "/api/2.0/genie/spaces"


def space_tables(client: object, space_id: str) -> set[str]:
    """The tables the Genie space is actually allowed to query.

    Discovery finds tables in the *catalog*; Genie can only answer about tables in its
    *space*. Those two sets are not the same, and where they differ the app would generate
    a case Genie cannot possibly run — the query comes back empty or refused, the verdict
    degrades to "can't tell", and the player is left wondering what they did wrong.

    Knowing the difference is what lets the docket say so instead. Returns an empty set
    when the space cannot be read, which callers treat as "cannot check" rather than as
    "nothing is allowed" — the difference matters, and guessing the harsher reading would
    hide every case.
    """
    try:
        raw = client.api_client.do(  # type: ignore[attr-defined]
            "GET", f"{SPACE_PATH}/{space_id}", query={"include_serialized_space": "true"}
        )
        serialized = raw.get("serialized_space")
        if not serialized:
            return set()
        import json

        space = json.loads(serialized) if isinstance(serialized, str) else serialized
        tables = space.get("data_sources", {}).get("tables", [])
        return {t.get("identifier", "") for t in tables if t.get("identifier")}
    except Exception as exc:  # noqa: BLE001 - see the module docstring: never fatal
        log.warning("Could not read the Genie space %s: %s", space_id, exc)
        return set()


def read_schema(client: object, catalog: str, schema: str) -> list[DiscoveredTable]:
    """Every table in one schema, as shapes rather than data.

    `client` is a `WorkspaceClient`, passed in rather than constructed here so a test can
    hand over a stub and never touch a network.
    """
    try:
        raw_tables = list(client.tables.list(catalog_name=catalog, schema_name=schema))  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001 - see the module docstring: never fatal
        log.warning("Could not read %s.%s from the catalog: %s", catalog, schema, exc)
        return []

    tables: list[DiscoveredTable] = []
    for raw in raw_tables:
        columns = tuple(_column(c) for c in (getattr(raw, "columns", None) or ()))
        if not columns:
            # A table whose columns the catalog did not return tells us nothing about what
            # could be asked of it, and guessing would be worse than skipping it.
            continue
        tables.append(
            DiscoveredTable(full_name=getattr(raw, "full_name", "") or "", columns=columns)
        )
    return tables
