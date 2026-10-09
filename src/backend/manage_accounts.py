"""Provision or repair privileged local accounts."""

import argparse
from getpass import getpass

from sqlalchemy import delete, select

from backend.auth import LoginInput, RegisterInput, hash_password
from backend.database import SessionLocal, init_db
from backend.models import AuthSession, User


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--role", choices=["admin", "lgu"], required=True)
    reset = commands.add_parser("reset", help="repair an existing account and grant reviewer access")
    reset.add_argument("--email", required=True)
    reset.add_argument("--name")
    reset.add_argument("--role", choices=["admin", "lgu"], required=True)
    arguments = parser.parse_args()
    password = getpass("Password (10-128 characters): ")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match")
    if arguments.command == "create":
        data = RegisterInput(name=arguments.name, email=arguments.email, password=password)
    else:
        data = LoginInput(email=arguments.email, password=password)
    init_db()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == data.email))
        if arguments.command == "create":
            if user is not None:
                parser.error("Email already registered; use the explicit reset command to repair it")
            db.add(User(name=data.name, email=data.email, password_hash=hash_password(data.password), role=arguments.role, verified=True))
            message = f"Created verified {arguments.role} account: {data.email}"
        else:
            if user is None:
                parser.error("Email is not registered; use create for a new account")
            if arguments.name:
                user.name = arguments.name.strip()
            user.password_hash = hash_password(data.password)
            user.role = arguments.role
            user.verified = True
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
            message = f"Reset verified {arguments.role} account: {data.email}"
        db.commit()
    print(message)


if __name__ == "__main__":
    main()
