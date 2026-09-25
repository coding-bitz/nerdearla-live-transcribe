from __future__ import annotations
import argon2
from argon2.exceptions import VerifyMismatchError, VerificationError

_hasher = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)


def hash_password(password: str) -> str:
    """Generates a secure Argon2id hash for the given plain password."""
    if not password:
        raise ValueError("Password cannot be empty")
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plain password against an Argon2id hash. Returns False on mismatch."""
    if not password or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False
    except Exception:
        return False
