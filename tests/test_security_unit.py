"""Testy jednostkowe polityki hasel i funkcji kryptograficznych.

Nie wymagaja klienta Flask ani bazy danych.
"""

import pytest

from app.security import hash_password, password_checks, verify_password


def _password_with_length(length):
    return "Aa1!" + "x" * (length - 4)


def test_valid_password_at_minimum_length():
    assert all(password_checks(_password_with_length(12)).values())


def test_valid_password_at_maximum_length():
    assert all(password_checks(_password_with_length(128)).values())


def test_rejects_password_below_minimum():
    assert password_checks(_password_with_length(11))["length"] is False


def test_rejects_password_above_maximum():
    assert password_checks(_password_with_length(129))["length"] is False


def test_requires_lowercase():
    assert password_checks("WIELKIELITERY123!")["lower"] is False


def test_requires_uppercase():
    assert password_checks("malelitery123!")["upper"] is False


def test_requires_digit():
    assert password_checks("BrakCyfryHaslo!")["digit"] is False


def test_requires_special_character():
    assert password_checks("BezSpecjalnych123")["special"] is False


def test_unicode_character_categories():
    password = "Ąą٥€" + "a" * 8
    assert all(password_checks(password).values())


def test_invalid_password_is_not_hashed():
    with pytest.raises(ValueError, match="Haslo nie spelnia"):
        hash_password("krotkie")


def test_argon2id_hash_can_be_verified():
    password = "BezpieczneHaslo123!"
    hashed = hash_password(password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, password) is True


def test_wrong_password_is_rejected():
    hashed = hash_password("BezpieczneHaslo123!")
    assert verify_password(hashed, "ZupelnieInneHaslo123!") is False


def test_invalid_hash_is_rejected():
    assert verify_password("niepoprawny-hash", "BezpieczneHaslo123!") is False
