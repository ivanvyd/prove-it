"""Reading the workspace's shape, and refusing to guess when it cannot be read.

`catalog.py` is the only module that talks to Unity Catalog, and every one of its failure
modes ends somewhere a player can see: an empty docket, a case Genie cannot answer, or a
stack trace instead of an app. The client is passed in rather than constructed, so all of
that is testable here without a network.

The rule these tests exist to hold: **losing discovery must never lose the app.**
"""

from __future__ import annotations

import json

from prove_it.catalog import read_schema, space_tables


class FakeColumn:
    def __init__(self, name: str, type_name: str = "STRING", comment: str = "") -> None:
        self.name = name
        self.type_name = type_name
        self.comment = comment


class FakeEnumType:
    """The SDK hands back an enum whose `str()` is `ColumnTypeName.DOUBLE`, not `DOUBLE`."""

    def __init__(self, value: str) -> None:
        self.value = value


class FakeTable:
    def __init__(self, full_name: str, columns=None, comment: str = "") -> None:
        self.full_name = full_name
        self.columns = columns
        self.comment = comment


class FakeTables:
    def __init__(self, tables, raises: Exception | None = None) -> None:
        self._tables = tables
        self._raises = raises

    def list(self, catalog_name: str, schema_name: str):
        if self._raises:
            raise self._raises
        return list(self._tables)


class FakeClient:
    def __init__(self, tables=None, raises=None, space_response=None, space_raises=None) -> None:
        self.tables = FakeTables(tables or [], raises)
        self._space_response = space_response
        self._space_raises = space_raises
        self.api_client = self

    def do(self, method: str, path: str, query=None, body=None):
        if self._space_raises:
            raise self._space_raises
        return self._space_response or {}


# -- reading a schema -----------------------------------------------------------------


def test_columns_are_read_with_their_types() -> None:
    client = FakeClient([FakeTable("c.s.t", [FakeColumn("gender", "STRING")])])
    tables = read_schema(client, "c", "s")

    assert len(tables) == 1
    assert tables[0].short_name == "t"
    assert tables[0].columns[0].name == "gender"
    assert tables[0].columns[0].type_name == "STRING"


def test_an_enum_type_is_unwrapped_to_the_bare_word() -> None:
    """`str(ColumnTypeName.DOUBLE)` is not `DOUBLE`, and the classifier compares against a
    set of bare type names — so an un-unwrapped enum silently makes every column a label."""
    client = FakeClient([FakeTable("c.s.t", [FakeColumn("score", FakeEnumType("DOUBLE"))])])
    assert read_schema(client, "c", "s")[0].columns[0].type_name == "DOUBLE"


def test_a_table_with_no_columns_is_skipped_rather_than_guessed_at() -> None:
    """Real behaviour, not hypothetical: `samples.tpch` and `samples.nyctaxi` return their
    tables with no column detail at all, through both `list` and `get`. A table whose
    columns are unknown says nothing about what could be asked of it."""
    client = FakeClient([FakeTable("c.s.empty", []), FakeTable("c.s.ok", [FakeColumn("x")])])
    assert [t.short_name for t in read_schema(client, "c", "s")] == ["ok"]


def test_a_catalog_that_cannot_be_read_returns_nothing_rather_than_raising() -> None:
    """Missing credentials, a deleted schema, a permissions error. The caller falls back
    to the curated docket; an exception here would take the whole app down."""
    client = FakeClient(raises=RuntimeError("PERMISSION_DENIED"))
    assert read_schema(client, "c", "s") == []


# -- what the Genie space will actually answer about ----------------------------------


def test_the_spaces_declared_tables_are_returned() -> None:
    space = {"data_sources": {"tables": [{"identifier": "c.s.a"}, {"identifier": "c.s.b"}]}}
    client = FakeClient(space_response={"serialized_space": json.dumps(space)})
    assert space_tables(client, "space-1") == {"c.s.a", "c.s.b"}


def test_a_space_that_cannot_be_read_returns_empty_meaning_cannot_check() -> None:
    """The distinction that matters: empty means "could not check", and the caller must
    treat it as "do not narrow" rather than "nothing is allowed". Reading it the harsh way
    would hide every case in the docket."""
    client = FakeClient(space_raises=RuntimeError("404"))
    assert space_tables(client, "space-1") == set()


def test_a_space_with_no_serialized_body_is_not_mistaken_for_an_empty_space() -> None:
    client = FakeClient(space_response={})
    assert space_tables(client, "space-1") == set()


def test_a_table_entry_with_no_identifier_is_ignored() -> None:
    space = {"data_sources": {"tables": [{"identifier": "c.s.a"}, {}]}}
    client = FakeClient(space_response={"serialized_space": json.dumps(space)})
    assert space_tables(client, "space-1") == {"c.s.a"}
