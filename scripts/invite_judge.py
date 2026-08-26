"""Give someone outside this workspace a working link to the app.

A Databricks App cannot be made public. Databricks' own documentation is explicit that
anonymous access and bypassing SSO are not supported, so the deployed URL answers an
unauthenticated request with a 302 to an OIDC consent screen and nothing else. For a
contest entry that is a real problem: a judge who opens the link sees a sign-in page, and
the ten points for "app experience" get decided by the demo video instead.

The way through is narrower than "make it public" and wider than "nothing can be done".
An account user can be granted CAN_USE on an app **without having access to the workspace
at all**. So one email address per judge, created here and granted on the app, turns the
link into something they can actually open.

Verified on this Free Edition workspace rather than assumed: a user was created via SCIM,
granted CAN_USE on `prove-it`, the grant was accepted and listed, and both were then
removed again.

    python scripts/invite_judge.py --email someone@example.com
    python scripts/invite_judge.py --email a@x.com --email b@y.com --profile DEFAULT
    python scripts/invite_judge.py --list
    python scripts/invite_judge.py --revoke someone@example.com

**The part this script cannot do for you.** Creating the account user is not the same as
that person being able to sign in. They still have to complete whatever authentication the
account requires — an invitation email, or your identity provider. Send the link only after
you have confirmed one invited address can actually reach the app, because a link that
still shows a sign-in wall is worse than no link: it reads as a broken submission rather
than a permissions one.

The zero-friction alternative, which needs nothing from anybody, is the offline run in
README.md — every case replays a real recorded Genie conversation with no account at all.
"""

from __future__ import annotations

import argparse

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppAccessControlRequest, AppPermissionLevel

APP = "prove-it"


def current_acl(client: WorkspaceClient, app: str) -> list[AppAccessControlRequest]:
    """The existing grants, as requests that can be sent straight back.

    `set_permissions` REPLACES the whole list, so anything not resent is silently revoked —
    including the owner's own CAN_MANAGE. Rebuilding from what is already there is what
    keeps this script from locking you out of your own app.
    """
    existing = client.apps.get_permissions(app_name=app)
    out: list[AppAccessControlRequest] = []
    for entry in existing.access_control_list or []:
        levels = {p.permission_level for p in (entry.all_permissions or []) if p.permission_level}
        for level in levels:
            out.append(
                AppAccessControlRequest(
                    user_name=entry.user_name,
                    group_name=entry.group_name,
                    service_principal_name=entry.service_principal_name,
                    permission_level=level,
                )
            )
    return out


def show(client: WorkspaceClient, app: str) -> None:
    print(f"\nwho can open {app}:")
    for entry in client.apps.get_permissions(app_name=app).access_control_list or []:
        who = entry.user_name or entry.group_name or entry.service_principal_name
        levels = [
            p.permission_level.value for p in (entry.all_permissions or []) if p.permission_level
        ]
        print(f"  {who:45} {levels}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grant app access to someone outside the workspace"
    )
    parser.add_argument("--email", action="append", default=[], help="repeatable")
    parser.add_argument("--revoke", action="append", default=[], help="repeatable")
    parser.add_argument("--app", default=APP)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    client = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()

    if args.list or not (args.email or args.revoke):
        show(client, args.app)
        if not (args.email or args.revoke):
            print("\nNothing to do. Pass --email to grant, --revoke to remove.")
        return 0

    for email in args.email:
        found = list(client.users.list(filter=f'userName eq "{email}"'))
        if found:
            print(f"{email}: already an account user")
        else:
            client.users.create(user_name=email, active=True)
            print(f"{email}: created")

    acl = [entry for entry in current_acl(client, args.app) if entry.user_name not in args.revoke]
    granted = {e.user_name for e in acl if e.permission_level is AppPermissionLevel.CAN_USE}
    for email in args.email:
        if email not in granted:
            acl.append(
                AppAccessControlRequest(
                    user_name=email, permission_level=AppPermissionLevel.CAN_USE
                )
            )

    client.apps.set_permissions(app_name=args.app, access_control_list=acl)
    for email in args.revoke:
        print(f"{email}: access removed (the account user itself is left alone)")

    show(client, args.app)
    print(
        "\nBefore sending the link: have one invited address actually open it. A grant is "
        "not a sign-in, and an unopenable link reads as a broken submission."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
