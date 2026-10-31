import unicodedata

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


def password_checks(password):
    categories = [
        unicodedata.category(char)
        for char in password
    ]

    return {
        "length": 12 <= len(password) <= 128,
        "lower": "Ll" in categories,
        "upper": "Lu" in categories,
        "digit": "Nd" in categories,
        "special": any(
            category.startswith(("P", "S"))
            for category in categories
        ),
    }


def hash_password(password):
    checks = password_checks(password)

    if not all(checks.values()):
        raise ValueError(
            "Haslo nie spelnia wymagan bezpieczenstwa."
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


# Hash pomocniczy dla prob logowania na nieistniejace konto.
# Nie jest przypisany do zadnego uzytkownika.
DUMMY_PASSWORD_HASH = password_hasher.hash(
    "SecTicket-Dummy-Password-2026!"
)
