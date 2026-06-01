"""Generate config/auth.yaml with bcrypt-hashed passwords.

Usage:
    uv run python scripts/create_auth_config.py

The script prompts for username, plaintext password, and role interactively,
then writes config/auth.yaml. Never commit config/auth.yaml.
"""
import sys
from pathlib import Path

import bcrypt
import yaml


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def main() -> None:
    output = Path("config/auth.yaml")
    output.parent.mkdir(parents=True, exist_ok=True)

    credentials: dict = {"usernames": {}}

    print("Add users (blank username to stop):")
    while True:
        username = input("  Username: ").strip()
        if not username:
            break
        name = input("  Display name: ").strip()
        plaintext = input("  Password: ").strip()
        role = input("  Role (admin/manager/staff) [staff]: ").strip() or "staff"
        email = input("  Email: ").strip()

        credentials["usernames"][username] = {
            "name": name,
            "password": hash_password(plaintext),
            "email": email,
            "role": role,
        }
        print(f"  -> added '{username}' as {role}\n")

    if not credentials["usernames"]:
        print("No users added, exiting.")
        sys.exit(1)

    config = {
        "credentials": credentials,
        "cookie": {
            "name": "medcomply_session",
            "key": "change_this_secret_key_in_production",
            "expiry_days": 1,
        },
    }

    with open(output, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print(f"\nWrote {output}  ({len(credentials['usernames'])} user(s))")
    print("Add config/ to .gitignore — never commit this file.")


if __name__ == "__main__":
    main()
