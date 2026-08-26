"""Give the app's service principal the access it needs to answer anything.

A Databricks App does not run as you. It runs as its own service principal, and that
principal starts with no access to your data and no access to your warehouse — which
produces two failures that look nothing like a permissions problem from the front end:

**Cases silently disappear.** The docket is built from tables the app can see, so a table
the service principal cannot read is a case that never appears. The app shows three cases
instead of five and says nothing about the other two.

**Genie "cannot be reached".** Every Genie query runs on a SQL warehouse as the caller. A
service principal with no CAN_USE on the warehouse cannot run anything at all, so every
case ends in "can't tell — Genie could not be reached", which reads like an outage and is
actually an ACL.

Both are one-time grants. Run this after `databricks apps create`, or any time the app
starts insisting the data is unreachable.

    python scripts/grant_app_access.py --app prove-it --profile DEFAULT
    python scripts/grant_app_access.py --app prove-it --dry-run

Idempotent: granting a privilege that is already held is not an error, and this prints
what it found before it changes anything.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from databricks.sdk import WorkspaceClient  # noqa: E402
from databricks.sdk.service.catalog import PermissionsChange, Privilege  # noqa: E402
from databricks.sdk.service.sql import (  # noqa: E402
    WarehouseAccessControlRequest,
    WarehousePermissionLevel,
)

from prove_it.genie.space import TABLES  # noqa: E402

# This SDK build wants the securable type as a plain string; passing `SecurableType.TABLE`
# fails with "SECURABLETYPE.TABLE is not a valid securable type", which is the enum's
# `str()` reaching the wire.
_TABLE = "TABLE"


def app_principal(client: WorkspaceClient, app_name: str) -> str:
    app = client.apps.get(app_name)
    principal = app.service_principal_client_id
    if not principal:
        raise SystemExit(f"app {app_name} reports no service principal — is it deployed?")
    return principal


def warehouse_id(client: WorkspaceClient) -> str | None:
    """The warehouse Genie will actually run on. Free Edition gives exactly one."""
    warehouses = list(client.warehouses.list())
    return warehouses[0].id if warehouses else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant the app's SP access to its own data")
    parser.add_argument("--app", default="prove-it")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
    principal = app_principal(client, args.app)
    print(f"app {args.app} runs as service principal {principal}\n")

    # -- the tables -------------------------------------------------------------------
    missing: list[str] = []
    for table in TABLES:
        try:
            grants = client.grants.get(_TABLE, table)
        except Exception as exc:  # noqa: BLE001 - reported; the other tables still get checked
            print(f"  {table}: could not read grants ({exc})")
            continue
        held = {
            str(p)
            for a in (grants.privilege_assignments or [])
            if a.principal == principal
            for p in (a.privileges or [])
        }
        if any("SELECT" in p for p in held):
            print(f"  {table}: already SELECT")
        else:
            print(f"  {table}: MISSING SELECT")
            missing.append(table)

    # -- the warehouse ----------------------------------------------------------------
    wid = warehouse_id(client)
    warehouse_ok = False
    if wid:
        acl = client.warehouses.get_permissions(wid)
        for entry in acl.access_control_list or []:
            if entry.service_principal_name == principal:
                warehouse_ok = True
        print(f"\n  warehouse {wid}: {'already CAN_USE' if warehouse_ok else 'NO ACCESS'}")

    if args.dry_run:
        print("\ndry run — nothing changed")
        return 0

    for table in missing:
        client.grants.update(
            _TABLE,
            table,
            changes=[PermissionsChange(add=[Privilege.SELECT], principal=principal)],
        )
        print(f"granted SELECT on {table}")

    if wid and not warehouse_ok:
        client.warehouses.set_permissions(
            warehouse_id=wid,
            access_control_list=[
                WarehouseAccessControlRequest(
                    service_principal_name=principal,
                    permission_level=WarehousePermissionLevel.CAN_USE,
                )
            ],
        )
        print(f"granted CAN_USE on warehouse {wid}")

    if not missing and warehouse_ok:
        print("\nnothing to do — the app already has everything it needs")
    else:
        print("\ndone. Restart the app or reload it; the next Genie call should succeed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
