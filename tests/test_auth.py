import re
import time

from sqlalchemy import select

from app.extensions import db
from app.models import User, RateLimitBucket
from app.rate_limit import (
    cleanup_expired_buckets,
    fingerprint,
)
from app.security import (
    hash_password,
    password_checks,
    verify_password,
)


PASSWORD = "BezpieczneHaslo123!"


def token(client, path):
    response = client.get(path)
    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )

    assert match is not None
    return match.group(1)


def create_user(app):
    with app.app_context():
        db.session.add(User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        ))
        db.session.commit()


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_password_policy():
    assert all(password_checks(PASSWORD).values())

    assert not all(
        password_checks("slabehaslo").values()
    )

    stored = hash_password(PASSWORD)

    assert stored.startswith("$argon2id$")
    assert verify_password(stored, PASSWORD)
    assert not verify_password(stored, "BledneHaslo123!")


def test_registration_login_logout(client, app):
    csrf = token(client, "/register")

    response = client.post(
        "/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "csrf_token": csrf,
        },
    )

    assert response.status_code == 302

    with app.app_context():
        user = db.session.scalar(
            select(User).where(
                User.username == "alice"
            )
        )

        assert user is not None
        assert user.role == "user"
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")

    csrf = token(client, "/login")

    response = client.post(
        "/login",
        data={
            "identifier": "alice",
            "password": PASSWORD,
            "csrf_token": csrf,
        },
    )

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

    response = client.get("/dashboard")
    assert response.status_code == 200

    csrf = token(client, "/dashboard")

    response = client.post(
        "/logout",
        data={"csrf_token": csrf},
    )

    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_csrf_protection(client):
    assert client.post(
        "/login",
        data={
            "identifier": "testuser",
            "password": PASSWORD,
        },
    ).status_code == 400

    assert client.post(
        "/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        },
    ).status_code == 400


def test_login_account_limit(client, app):
    create_user(app)
    csrf = token(client, "/login")

    for index in range(5):
        identifier = (
            "testuser" if index < 2
            else "test@example.com"
        )

        response = client.post(
            "/login",
            data={
                "identifier": identifier,
                "password": "Niepoprawne123!",
                "csrf_token": csrf,
            },
            environ_overrides={
                "REMOTE_ADDR": f"10.0.1.{index + 1}"
            },
        )

        assert response.status_code == (
            429 if index == 4 else 200
        )

    response = client.post(
        "/login",
        data={
            "identifier": "testuser",
            "password": PASSWORD,
            "csrf_token": csrf,
        },
        environ_overrides={
            "REMOTE_ADDR": "10.0.1.99"
        },
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_registration_ip_limit(client):
    csrf = token(client, "/register")

    for index in range(6):
        response = client.post(
            "/register",
            data={
                "username": "x",
                "email": "invalid",
                "password": "bad",
                "confirm_password": "bad",
                "csrf_token": csrf,
            },
            environ_overrides={
                "REMOTE_ADDR": "10.0.2.1"
            },
        )

        assert response.status_code == (
            429 if index == 5 else 200
        )


def test_expired_bucket_cleanup(app):
    with app.app_context():
        now = int(time.time())

        expired_key = fingerprint("test", "expired")
        active_key = fingerprint("test", "active")

        db.session.add_all([
            RateLimitBucket(
                scope="test",
                identifier=expired_key,
                attempts=5,
                reset_at=now - 100,
            ),
            RateLimitBucket(
                scope="test",
                identifier=active_key,
                attempts=2,
                reset_at=now + 900,
            ),
        ])
        db.session.commit()

        assert cleanup_expired_buckets() == 1

        assert db.session.get(
            RateLimitBucket,
            ("test", expired_key),
        ) is None

        assert db.session.get(
            RateLimitBucket,
            ("test", active_key),
        ) is not None


def test_no_public_account_enumeration(client):
    response = client.post(
        "/auth/check-availability"
    )

    assert response.status_code == 404
