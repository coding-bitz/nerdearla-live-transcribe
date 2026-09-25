#!/usr/bin/env python3
"""CLI utility to generate an Argon2id password hash for Nerdearla operator setup.

Prompts for password securely without echoing to terminal.
Outputs the resulting Argon2id hash for Secret Manager or .env configuration.
Never writes password to disk or logs.
"""

import getpass
import sys
from app.auth.hashing import hash_password


def main() -> None:
    print("Nerdearla Live Subtitles — Password Hash Generator", file=sys.stderr)
    print("Enter operator password to generate Argon2id hash:", file=sys.stderr)

    pw1 = getpass.getpass("Password: ")
    if not pw1:
        print("Error: Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    pw2 = getpass.getpass("Confirm Password: ")
    if pw1 != pw2:
        print("Error: Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    argon2_hash = hash_password(pw1)
    print("\nGenerated Argon2id Hash (store in Secret Manager or AUTH_PASSWORD_HASH):", file=sys.stderr)
    print(argon2_hash)


if __name__ == "__main__":
    main()
