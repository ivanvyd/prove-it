"""Build everything in the workspace that can be built from here.

`docs/setup.md` describes importing a notebook and running it by hand. That works, but it
is four manual steps that can go subtly wrong, and the data it produces has to match the
numbers the app and the tests quote. This script does the same work from the same
generator, so it cannot drift.

    databricks auth login --host https://<workspace>.cloud.databricks.com
    python scripts/setup_workspace.py

It creates the schema, a volume, uploads the generated pupil data, builds the Delta table
and documents every column. It stops short of creating the Genie space: the API needs a
`serialized_space` payload you can only obtain from a space that already exists, so that
part stays a few clicks in the UI, and the script prints exactly what to do.

Everything it does is idempotent — run it again and it converges rather than duplicating.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prove_it.demo_data import (  # noqa: E402
    CATALOG,
    COLUMN_COMMENTS,
    INDICATOR_COLUMN_COMMENTS,
    INDICATORS_COMMENT,
    OBSERVED,
    SCHEMA,
    TABLE_COMMENT,
    effect_size,
    generate_students,
)

VOLUME = "seed"
CSV_NAME = "student_scores.csv"

# Catalog and schema arrive from the command line and end up inside DDL, where an
# identifier cannot be parameterised. Restrict them to what Unity Catalog names actually
# look like rather than trusting the caller.
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def identifier(name: str, what: str) -> str:
    if not _IDENTIFIER.match(name):
        raise SystemExit(f"--{what} must be letters, digits or underscores only, got {name!r}")
    return name


def sql_literal(value: str) -> str:
    """Quote a string for SQL, doubling any embedded quote.

    The table and column comments are English prose written for children, and prose
    acquires apostrophes — "the pupil's score" is one edit away at all times. Without
    this, that edit produces a statement with an unbalanced quote and the setup breaks
    somewhere confusing, or worse, the text after the apostrophe is executed.
    """
    return "'" + value.replace("'", "''") + "'"


TERMINAL_OK = {"SUCCEEDED"}
TERMINAL_BAD = {"FAILED", "CANCELED", "CANCELLED", "CLOSED"}
PENDING_STATES = {"PENDING", "RUNNING"}


def _state_of(response) -> str:
    state = getattr(getattr(response, "status", None), "state", None)
    return str(getattr(state, "value", state) or "").upper()


def sql(client, warehouse_id: str, statement: str, *, timeout: str = "50s", poll_for: int = 300):
    """Run one statement, wait for it to actually finish, and raise if it failed.

    `execute_statement` runs in hybrid mode: if the statement outlives `wait_timeout` it
    returns with a non-terminal state and a statement id rather than an error. A cold
    2X-Small warehouse routinely takes longer than that to start, so treating PENDING or
    RUNNING as success meant the script moved on to upload a file to a volume whose CREATE
    had not completed — and then reported a spurious data mismatch at the end that was
    really just timing.
    """
    response = client.statement_execution.execute_statement(
        statement=statement, warehouse_id=warehouse_id, wait_timeout=timeout
    )

    deadline = poll_for
    while _state_of(response) in PENDING_STATES and deadline > 0:
        statement_id = getattr(response, "statement_id", None)
        if not statement_id:
            break
        time.sleep(2)
        deadline -= 2
        response = client.statement_execution.get_statement(statement_id)

    state = _state_of(response)
    if state in TERMINAL_BAD or (state in PENDING_STATES and deadline <= 0):
        error = getattr(getattr(response, "status", None), "error", None)
        raise RuntimeError(
            f"{state or 'UNKNOWN'}: {getattr(error, 'message', error)}\n  {statement[:200]}"
        )
    if state and state not in TERMINAL_OK and state not in PENDING_STATES:
        raise RuntimeError(f"{state}: unexpected statement state\n  {statement[:200]}")
    return response


def compare_to_expected(rows) -> list[tuple[str, tuple, tuple]]:
    """Check what the warehouse actually returned against the numbers we publish.

    The app, the tests and the project story all quote `demo_data.OBSERVED`. If the table
    in the workspace says something else, every one of those is now lying, and the place
    to find that out is here rather than mid-demo. Rows come back as strings.

    A gender missing from the result is a mismatch, not a pass — an empty result set must
    not read as agreement.
    """
    expected = {g: (o.students, o.maths_mean, o.maths_sd) for g, o in OBSERVED.items()}
    seen: dict[str, tuple] = {}
    mismatched: list[tuple[str, tuple, tuple]] = []

    for row in rows:
        gender = str(row[0])
        if gender not in expected:
            continue
        try:
            got = (int(float(row[1])), float(row[2]), float(row[3]))
        except (TypeError, ValueError):
            mismatched.append((gender, expected[gender], tuple(row[1:4])))
            continue
        seen[gender] = got
        want = expected[gender]
        if got[0] != want[0] or abs(got[1] - want[1]) > 0.05 or abs(got[2] - want[2]) > 0.05:
            mismatched.append((gender, want, got))

    for gender, want in expected.items():
        if gender not in seen and not any(m[0] == gender for m in mismatched):
            mismatched.append((gender, want, ("missing from result",)))

    return mismatched


def pick_warehouse(client, preferred: str | None) -> str:
    warehouses = list(client.warehouses.list())
    if not warehouses:
        raise SystemExit(
            "No SQL warehouse found. Free Edition gives you one — open the workspace, go to "
            "SQL Warehouses, and start it, then re-run."
        )
    if preferred:
        for w in warehouses:
            if w.id == preferred or w.name == preferred:
                return w.id
        raise SystemExit(
            f"No warehouse matching {preferred!r}. Found: {[w.name for w in warehouses]}"
        )
    running = [
        w for w in warehouses if str(getattr(w.state, "value", w.state)).upper() == "RUNNING"
    ]
    chosen = (running or warehouses)[0]
    print(f"  warehouse: {chosen.name} ({chosen.id})")
    return chosen.id


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove It — build the workspace objects")
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument("--schema", default=SCHEMA)
    parser.add_argument("--warehouse", default=None, help="warehouse id or name")
    parser.add_argument("--profile", default=None, help="~/.databrickscfg profile")
    parser.add_argument(
        "--indicators-csv",
        default=None,
        help=(
            "path to a real public-data CSV (World Bank / Our World in Data) to load as "
            "country_indicators. Free Edition restricts outbound internet, so download it "
            "yourself and pass the file."
        ),
    )
    args = parser.parse_args()

    indicators_csv = Path(args.indicators_csv) if args.indicators_csv else None
    if indicators_csv and not indicators_csv.is_file():
        raise SystemExit(f"--indicators-csv: no such file: {indicators_csv}")

    from databricks.sdk import WorkspaceClient

    client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()

    me = client.current_user.me()
    print(f"Authenticated as {me.user_name}")

    warehouse_id = pick_warehouse(client, args.warehouse)
    catalog = identifier(args.catalog, "catalog")
    schema = identifier(args.schema, "schema")
    fq_schema = f"{catalog}.{schema}"
    table = f"{fq_schema}.student_scores"

    print(f"\nCreating {fq_schema} …")
    sql(client, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {fq_schema}")
    sql(client, warehouse_id, f"CREATE VOLUME IF NOT EXISTS {fq_schema}.{VOLUME}")

    print("Generating pupil data from prove_it.demo_data …")
    students = generate_students()
    buffer = io.StringIO()
    students.to_csv(buffer, index=False)
    payload = buffer.getvalue().encode("utf-8")
    print(f"  {len(students):,} rows, {len(payload) / 1024:.0f} kB")

    volume_path = f"/Volumes/{catalog}/{schema}/{VOLUME}/{CSV_NAME}"
    print(f"Uploading to {volume_path} …")
    client.files.upload(volume_path, io.BytesIO(payload), overwrite=True)

    print(f"Building {table} …")
    sql(
        client,
        warehouse_id,
        f"""
        CREATE OR REPLACE TABLE {table} AS
        -- Dropped deliberately. read_files adds a _rescued_data column when inferring a
        -- schema, and a Genie space shows every column it is given: a child would see a
        -- stray ingestion artifact next to maths_score, and Genie might try to reason
        -- about it. There is nothing to rescue from a file this code just wrote.
        -- (Setting rescuedDataColumn => '' does not work — it asks Unity Catalog to
        -- create a column with an empty name, which it rejects.)
        SELECT * EXCEPT (_rescued_data) FROM read_files(
            '{volume_path}',
            format => 'csv',
            header => true,
            inferSchema => true
        )
        """,
        timeout="50s",
    )

    print("Documenting columns for Genie …")
    sql(client, warehouse_id, f"COMMENT ON TABLE {table} IS {sql_literal(TABLE_COMMENT)}")
    for column, comment in COLUMN_COMMENTS.items():
        sql(
            client,
            warehouse_id,
            f"ALTER TABLE {table} ALTER COLUMN {column} COMMENT {sql_literal(comment)}",
        )

    print("\nVerifying the lesson still lands …")
    result = sql(
        client,
        warehouse_id,
        f"""
        SELECT gender, COUNT(*) AS students,
               ROUND(AVG(maths_score), 1) AS avg_score,
               ROUND(STDDEV(maths_score), 1) AS spread
        FROM {table} GROUP BY gender ORDER BY gender
        """,
    )
    rows = getattr(getattr(result, "result", None), "data_array", None) or []
    for row in rows:
        print(f"  {row}")

    mismatched = compare_to_expected(rows)

    if mismatched:
        print("\n  WARNING — the table does not match prove_it.demo_data.OBSERVED:")
        for gender, want, got in mismatched:
            print(f"    {gender}: expected {want}, got {got}")
        print("  The app and the project story quote OBSERVED, so fix this before the demo.")
    else:
        print("  Matches prove_it.demo_data.OBSERVED exactly.")

    verdict = (
        "negligible, the lesson lands"
        if effect_size() < 0.2
        else "TOO LARGE, the repaired query would confirm the claim"
    )
    print(f"  effect size {effect_size():.3f} — {verdict}")

    indicators_table = f"{fq_schema}.country_indicators"
    if indicators_csv:
        print(f"\nLoading real public data from {indicators_csv.name} …")
        remote = f"/Volumes/{catalog}/{schema}/{VOLUME}/{indicators_csv.name}"
        client.files.upload(remote, io.BytesIO(indicators_csv.read_bytes()), overwrite=True)
        sql(
            client,
            warehouse_id,
            f"""
            CREATE OR REPLACE TABLE {indicators_table} AS
            -- Same exclusion as the pupil table: read_files adds _rescued_data when it
            -- infers a schema, and every column here ends up in front of Genie.
            SELECT * EXCEPT (_rescued_data) FROM read_files(
                '{remote}', format => 'csv', header => true, inferSchema => true
            )
            """,
        )
        sql(
            client,
            warehouse_id,
            f"COMMENT ON TABLE {indicators_table} IS {sql_literal(INDICATORS_COMMENT)}",
        )

        # Document whichever columns this CSV happens to have. A Genie space reasons from
        # column comments, and the published header names are not self-explanatory.
        present = {c.name for c in (client.tables.get(indicators_table).columns or []) if c.name}
        documented = 0
        for column, comment in INDICATOR_COLUMN_COMMENTS.items():
            if column in present:
                sql(
                    client,
                    warehouse_id,
                    f"ALTER TABLE {indicators_table} ALTER COLUMN {column} "
                    f"COMMENT {sql_literal(comment)}",
                )
                documented += 1
        undocumented = sorted(present - set(INDICATOR_COLUMN_COMMENTS))
        print(f"  documented {documented} of {len(present)} columns")
        if undocumented:
            print(
                f"  no comment for: {', '.join(undocumented)} — add them to "
                "INDICATOR_COLUMN_COMMENTS in prove_it/demo_data.py so Genie can use them"
            )

        count = sql(client, warehouse_id, f"SELECT COUNT(*) FROM {indicators_table}")
        rows_loaded = getattr(getattr(count, "result", None), "data_array", None) or [["?"]]
        print(f"  {indicators_table}: {rows_loaded[0][0]} rows")
    else:
        print("""
No real-data table loaded. The app works without it — you lose the second demo rumour,
not the product — but the demo video is stronger if it ends on real public figures.

  Download an indicator CSV from https://data.worldbank.org/indicator (e.g.
  SE.XPD.TOTL.GD.ZS) or https://ourworldindata.org/, then re-run with:

    python scripts/setup_workspace.py --indicators-csv <path-to.csv>""")

    print(f"""
Done. What is left has to be done in the UI, because the Genie space API needs a
serialized payload you can only get from a space that already exists:

  1. Genie -> New space
  2. Add the table(s): {table}{f", {indicators_table}" if indicators_csv else ""}
  3. Warehouse:      the one above
  4. Paste the instructions from docs/genie-space-instructions.md
  5. Copy the space id out of the URL (/genie/rooms/<space-id>)

Then run the day-one gate, which is the thing that decides whether the concept holds:

  python scripts/probe.py --space-id <space-id> --repeats 3 --record
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
