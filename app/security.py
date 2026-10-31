from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
)


def hash_password(password):
    if not 12 <= len(password) <= 128:
        raise ValueError(
            "Haslo musi miec od 12 do 128 znakow."
        )

    return password_hasher.hash(password)


def verify_password(stored_hash, password):
    try:
        return password_hasher.verify(
            stored_hash, password
        )
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    ):
        return False
