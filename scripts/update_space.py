"""Push the repo's table list and instructions into the Genie space.

`docs/requirement.md` §4a records why creating a space is still four clicks. Updating one
is different and worth automating: the instructions decide whether every case in the
docket works, they change with each new case, and editing them by hand in the UI is how
they drift away from what the tests assert.

    python scripts/update_space.py --space-id <id>
    python scripts/update_space.py --space-id <id> --dry-run

The payload shape was learned by reading a real space back, not from documentation:
    {"version": 2,
     "data_sources": {"tables": [{"identifier": ...}, ...]},   # sorted by identifier
     "instructions": {"text_instructions": [{"id": ..., "content": [line, ...]}]}}

Two things the API will not tell you clearly. The table list must be sorted by identifier
or the update is rejected with a message that never mentions sorting. And `content` is a
list of lines, not one string with newlines in it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prove_it.genie.space import TABLES, instruction_lines  # noqa: E402

SPACE_PATH = "/api/2.0/genie/spaces"


def read_space(client, space_id: str) -> dict:
    raw = client.api_client.do(
        "GET", f"{SPACE_PATH}/{space_id}", query={"include_serialized_space": "true"}
    )
    serialized = raw.get("serialized_space")
    if not serialized:
        raise SystemExit(
            f"space {space_id} returned no serialized_space — check the id and that the "
            "token can read it"
        )
    return json.loads(serialized) if isinstance(serialized, str) else serialized


def rebuild(current: dict) -> dict:
    """The current space with our tables and instructions substituted in.

    Everything else is carried through untouched. A space carries fields this project has
    never needed (benchmarks, sample questions, join hints), and rebuilding the payload
    from scratch would silently delete whichever of them happen to be set.
    """
    updated = dict(current)
    updated["version"] = current.get("version", 2)
    updated["data_sources"] = {"tables": [{"identifier": t} for t in TABLES]}

    existing = (current.get("instructions") or {}).get("text_instructions") or []
    lines = list(instruction_lines())
    if existing:
        # Keep the id: the API treats a new id as a second instruction rather than a
        # replacement, and two sets of instructions is worse than either.
        first = dict(existing[0])
        first["content"] = lines
        kept = [first]
    else:
        kept = [{"content": lines}]
    updated["instructions"] = dict(current.get("instructions") or {})
    updated["instructions"]["text_instructions"] = kept
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove It — update the Genie space")
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--profile", default=None, help="~/.databrickscfg profile")
    parser.add_argument("--dry-run", action="store_true", help="print the payload, change nothing")
    args = parser.parse_args()

    from databricks.sdk import WorkspaceClient

    client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()

    current = read_space(client, args.space_id)
    before = [t.get("identifier") for t in current.get("data_sources", {}).get("tables", [])]
    payload = rebuild(current)

    print(f"tables before: {len(before)}")
    for t in before:
        print(f"  {t}")
    print(f"tables after:  {len(TABLES)}")
    for t in TABLES:
        print(f"  {t}{'' if t in before else '   <- new'}")
    print(f"instruction lines: {len(instruction_lines())}")

    if args.dry_run:
        print("\n--dry-run: nothing sent")
        return 0

    client.api_client.do(
        "PATCH",
        f"{SPACE_PATH}/{args.space_id}",
        body={"serialized_space": json.dumps(payload)},
    )
    print("\nUpdated. Re-read to confirm:")
    after = read_space(client, args.space_id)
    got = [t.get("identifier") for t in after.get("data_sources", {}).get("tables", [])]
    print(f"  tables now: {got}")
    if sorted(got) != sorted(TABLES):
        print("  ! the space does not match what was sent")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
