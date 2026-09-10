"""Create or promote an admin user.

Usage:
  python -m app.cli.create_admin --email YOU@example.com --password "Secret123" --name "Admin"
  python -m app.cli.create_admin --email you@gmail.com --promote-existing
  python -m app.cli.create_admin --email you@gmail.com --promote-existing --reset-password --password "NewPass"
"""

from __future__ import annotations

import argparse
import sys

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User
from app.services import billing_service, user_service


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or promote a SentiTrack admin user")
    parser.add_argument("--email", required=True, help="Admin login email")
    parser.add_argument("--password", default=None, help="Plain password (bcrypt-hashed)")
    parser.add_argument("--name", default="Admin", help="Display name (default: Admin)")
    parser.add_argument(
        "--promote-existing",
        action="store_true",
        help="If the user exists, set is_admin=true instead of creating",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="With --promote-existing, also update the password",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    email = args.email.strip().lower()

    if not args.promote_existing and not args.password:
        print("error: --password is required when creating a new admin", file=sys.stderr)
        return 2
    if args.reset_password and not args.password:
        print("error: --password is required with --reset-password", file=sys.stderr)
        return 2
    if args.password is not None and not (8 <= len(args.password) <= 72):
        print("error: password must be 8–72 characters", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        existing = user_service.get_user_by_email(db, email)

        if existing is not None:
            if not args.promote_existing:
                print(
                    f"error: user {email!r} already exists; use --promote-existing",
                    file=sys.stderr,
                )
                return 1
            existing.is_admin = True
            if args.reset_password:
                existing.password_hash = hash_password(args.password)
            if args.name and args.name != "Admin":
                existing.name = args.name
            billing_service.assign_default_plan(db, existing, commit=False)
            db.commit()
            print(f"Promoted existing user to admin: id={existing.id} email={existing.email}")
            return 0

        if not args.password:
            print("error: --password is required for a new user", file=sys.stderr)
            return 2

        user = User(
            name=args.name,
            email=email,
            password_hash=hash_password(args.password),
            is_admin=True,
        )
        db.add(user)
        db.flush()
        billing_service.assign_default_plan(db, user, commit=False)
        db.commit()
        db.refresh(user)
        print(f"Created admin user: id={user.id} email={user.email}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
