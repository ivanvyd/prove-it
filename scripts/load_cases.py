"""Load the case tables that `setup_workspace.py` does not build.

Separate from that script on purpose. `setup_workspace.py` builds a workspace from
nothing and regenerates the synthetic pupil data every run; these are additional tables
for the case docket, one of them a 13 MB download, and neither needs the pupil generator
to run again to be refreshed.

    python scripts/load_cases.py                          # Berkeley only
    python scripts/load_cases.py --emissions-csv <path>   # and the OWID emissions table

Idempotent: CREATE OR REPLACE throughout, so re-running converges.

Free Edition restricts outbound internet, so the emissions CSV has to be downloaded first
and passed in — the same arrangement `--indicators-csv` already uses:
    https://nyc3.digitaloceanspaces.com/owid-public/data/co2/owid-co2-data.csv
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prove_it.case_data import (  # noqa: E402
    BERKELEY_COLUMN_COMMENTS,
    BERKELEY_TABLE_COMMENT,
    EMISSIONS_COLUMN_COMMENTS,
    EMISSIONS_MIN_POPULATION,
    EMISSIONS_TABLE_COMMENT,
    berkeley_pooled,
    berkeley_rows,
)
from prove_it.demo_data import CATALOG, SCHEMA  # noqa: E402
from setup_workspace import identifier, pick_warehouse, sql, sql_literal  # noqa: E402

VOLUME = "seed"
EMISSIONS_CSV = "emissions.csv"

# The columns kept from OWID's 79-column file. Everything else is noise in front of Genie:
# a space shows every column it is given, and a model asked for "the biggest polluter"
# should not have to choose between co2, co2_including_luc, cumulative_co2 and six others.
EMISSIONS_COLUMNS = ("country", "year", "population", "co2", "co2_per_capita")


def load_berkeley(client, warehouse_id: str, fq_schema: str) -> str:
    """Twelve rows, written as a literal VALUES list rather than uploaded as a file.

    A CSV round-trip through a volume would be the same shape as the other loaders, but
    it would also put a transcription of a published table through an inferred schema for
    no reason. Twelve rows fit in the statement, and the values come straight from
    `prove_it.case_data`, which the test suite checks against two independent sources.
    """
    table = f"{fq_schema}.berkeley_admissions"
    rows = berkeley_rows()
    values = ",\n            ".join(
        f"({sql_literal(str(r['department']))}, {sql_literal(str(r['gender']))}, "
        f"{int(r['applicants'])}, {int(r['admitted'])})"
        for r in rows
    )
    print(f"Building {table} — {len(rows)} rows …")
    sql(
        client,
        warehouse_id,
        f"""
        CREATE OR REPLACE TABLE {table} (
            department STRING,
            gender STRING,
            applicants INT,
            admitted INT
        )
        """,
    )
    sql(
        client,
        warehouse_id,
        f"""
        INSERT INTO {table} (department, gender, applicants, admitted) VALUES
            {values}
        """,
    )
    sql(client, warehouse_id, f"COMMENT ON TABLE {table} IS {sql_literal(BERKELEY_TABLE_COMMENT)}")
    for column, comment in BERKELEY_COLUMN_COMMENTS.items():
        sql(
            client,
            warehouse_id,
            f"ALTER TABLE {table} ALTER COLUMN {column} COMMENT {sql_literal(comment)}",
        )
    return table


def _gender_labels() -> tuple[str, str]:
    """The two gender labels, read off the rows rather than written down twice."""
    labels = sorted({str(r["gender"]) for r in berkeley_rows()})
    if len(labels) != 2:
        raise SystemExit(f"expected two gender labels in the Berkeley rows, got {labels}")
    # Alphabetical puts "men" before "women"; assert rather than assume.
    men = next(label for label in labels if label.startswith("m"))
    women = next(label for label in labels if label != men)
    return men, women


def verify_berkeley(client, warehouse_id: str, table: str) -> bool:
    """Ask the warehouse the naive question, and check it gives the published answer.

    This is the case's own premise. If the pooled rate does not favour men, or the
    departments do not mostly favour women, there is no paradox to overturn and the case
    is broken however green the unit tests are.
    """
    print("\nVerifying the paradox survived the round trip …")
    pooled = sql(
        client,
        warehouse_id,
        f"""
        SELECT gender, SUM(applicants) AS applicants, SUM(admitted) AS admitted,
               ROUND(100.0 * SUM(admitted) / SUM(applicants), 1) AS rate
        FROM {table} GROUP BY gender ORDER BY gender
        """,
    )
    rows = getattr(getattr(pooled, "result", None), "data_array", None) or []
    got = {r[0]: float(r[3]) for r in rows}
    for row in rows:
        print(f"  {row}")

    # Labels come from the data, never restated here. Pluralising them in case_data left
    # this checking for 'man' and 'woman', which matched nothing: the pooled lookup missed
    # and both CASE expressions in the per-department query returned NULL.
    men_label, women_label = _gender_labels()

    want_men, want_women = berkeley_pooled()
    ok = True
    for who, want in ((men_label, want_men * 100), (women_label, want_women * 100)):
        if who not in got or abs(got[who] - want) > 0.1:
            print(f"  ! {who}: expected {want:.1f}%, table says {got.get(who)}")
            ok = False
    if ok:
        print(
            f"  pooled: {men_label} {got[men_label]}%, {women_label} {got[women_label]}% "
            f"— favours {men_label}, as published"
        )

    by_dept = sql(
        client,
        warehouse_id,
        f"""
        SELECT department,
               MAX(CASE WHEN gender = {sql_literal(men_label)}
                        THEN 100.0 * admitted / applicants END) AS men,
               MAX(CASE WHEN gender = {sql_literal(women_label)}
                        THEN 100.0 * admitted / applicants END) AS women
        FROM {table} GROUP BY department ORDER BY department
        """,
    )
    dept_rows = getattr(getattr(by_dept, "result", None), "data_array", None) or []
    if any(r[1] is None or r[2] is None for r in dept_rows):
        # Both sides must be present in every department, or the count below silently
        # reports zero reversals and the case looks broken rather than the query.
        print("  ! some departments are missing one gender — check the labels in case_data")
        return False
    favouring = sum(1 for r in dept_rows if float(r[2]) > float(r[1]))
    print(
        f"  departments where women were admitted at a higher rate: {favouring} of {len(dept_rows)}"
    )
    if favouring * 2 <= len(dept_rows):
        print("  ! the reversal is gone — this case has nothing to overturn")
        ok = False
    return ok


def load_emissions(
    client, warehouse_id: str, fq_schema: str, catalog: str, schema: str, source: Path
) -> str:
    """OWID emissions, narrowed and filtered before it ever reaches Genie.

    Two filters, both load-time and neither delegated to a space instruction:

    Aggregates. OWID puts `World`, `Asia` and `High-income countries` in the same
    `country` column as real countries. Unfiltered, "who emits the most" answers "World",
    which is true and useless. Rows are kept only when they carry a real ISO code —
    aggregates have none, or an OWID_ sentinel.

    Small countries. Per-capita emissions are dominated by places with a refinery and no
    people; a top-10 per-person list of countries under a million reads as a data quirk
    rather than a lesson about denominators.
    """
    table = f"{fq_schema}.emissions"
    print(f"\nNarrowing {source.name} …")

    kept: list[list[str]] = []
    with source.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            code = (row.get("iso_code") or "").strip()
            if not code or code.startswith("OWID"):
                continue
            if not (row.get("co2") and row.get("co2_per_capita") and row.get("population")):
                continue
            if float(row["population"]) < EMISSIONS_MIN_POPULATION:
                continue
            kept.append([row[c] for c in EMISSIONS_COLUMNS])

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EMISSIONS_COLUMNS)
    writer.writerows(kept)
    payload = buffer.getvalue().encode("utf-8")
    print(f"  {len(kept):,} rows kept, {len(payload) / 1024:.0f} kB")

    remote = f"/Volumes/{catalog}/{schema}/{VOLUME}/{EMISSIONS_CSV}"
    print(f"Uploading to {remote} …")
    client.files.upload(remote, io.BytesIO(payload), overwrite=True)

    print(f"Building {table} …")
    sql(
        client,
        warehouse_id,
        f"""
        CREATE OR REPLACE TABLE {table} AS
        -- Same exclusion as every other loader here: read_files adds _rescued_data when
        -- it infers a schema, and every column ends up in front of Genie.
        SELECT * EXCEPT (_rescued_data) FROM read_files(
            '{remote}', format => 'csv', header => true, inferSchema => true
        )
        """,
    )
    sql(client, warehouse_id, f"COMMENT ON TABLE {table} IS {sql_literal(EMISSIONS_TABLE_COMMENT)}")
    for column, comment in EMISSIONS_COLUMN_COMMENTS.items():
        sql(
            client,
            warehouse_id,
            f"ALTER TABLE {table} ALTER COLUMN {column} COMMENT {sql_literal(comment)}",
        )
    return table


def verify_emissions(client, warehouse_id: str, table: str) -> bool:
    """The denominator case needs the same country to be first by total and not by head."""
    print("\nVerifying the flip …")
    result = sql(
        client,
        warehouse_id,
        f"""
        WITH latest AS (SELECT MAX(year) AS y FROM {table})
        SELECT 'total' AS by, country, ROUND(co2, 1) AS value FROM {table}, latest
         WHERE year = latest.y ORDER BY co2 DESC LIMIT 3
        """,
    )
    top_total = getattr(getattr(result, "result", None), "data_array", None) or []
    result = sql(
        client,
        warehouse_id,
        f"""
        WITH latest AS (SELECT MAX(year) AS y FROM {table})
        SELECT 'per person' AS by, country, ROUND(co2_per_capita, 2) AS value
          FROM {table}, latest WHERE year = latest.y ORDER BY co2_per_capita DESC LIMIT 3
        """,
    )
    top_head = getattr(getattr(result, "result", None), "data_array", None) or []
    for row in top_total + top_head:
        print(f"  {row}")

    if not top_total or not top_head:
        print("  ! no rows — the table is empty or the year filter found nothing")
        return False
    if top_total[0][1] == top_head[0][1]:
        print("  ! the same country leads both — there is no flip to teach")
        return False
    print(f"  by total: {top_total[0][1]}; per person: {top_head[0][1]} — the flip holds")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove It — load the case tables")
    parser.add_argument("--catalog", default=CATALOG)
    parser.add_argument("--schema", default=SCHEMA)
    parser.add_argument("--warehouse", default=None, help="warehouse id or name")
    parser.add_argument("--profile", default=None, help="~/.databrickscfg profile")
    parser.add_argument(
        "--emissions-csv",
        default=None,
        help="path to OWID's owid-co2-data.csv. Omit to load Berkeley only.",
    )
    args = parser.parse_args()

    emissions_csv = Path(args.emissions_csv) if args.emissions_csv else None
    if emissions_csv and not emissions_csv.is_file():
        raise SystemExit(f"--emissions-csv: no such file: {emissions_csv}")

    from databricks.sdk import WorkspaceClient

    client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
    print(f"Authenticated as {client.current_user.me().user_name}")

    warehouse_id = pick_warehouse(client, args.warehouse)
    catalog = identifier(args.catalog, "catalog")
    schema = identifier(args.schema, "schema")
    fq_schema = f"{catalog}.{schema}"

    sql(client, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {fq_schema}")
    sql(client, warehouse_id, f"CREATE VOLUME IF NOT EXISTS {fq_schema}.{VOLUME}")

    healthy = verify_berkeley(client, warehouse_id, load_berkeley(client, warehouse_id, fq_schema))

    if emissions_csv:
        table = load_emissions(client, warehouse_id, fq_schema, catalog, schema, emissions_csv)
        healthy = verify_emissions(client, warehouse_id, table) and healthy
    else:
        print("\nNo --emissions-csv given; the denominator case has no table.")

    print(
        "\nNext: add the new tables to the Genie space, then run\n"
        "  python scripts/probe_cases.py --space-id <id>"
    )
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
