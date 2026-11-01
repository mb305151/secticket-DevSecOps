import re

from sqlalchemy import select

from app.extensions import db
from app.models import SecurityEvent, User
from app.security import hash_password, verify_password

PASS = "BezpieczneHaslo123!"
NEW_PASS = "BardzoMocneHaslo456!"


def csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.status_code
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def users_fixture(app):
    with app.app_context():
        db.session.add_all([
            User(username="alice", email="alice@example.com", password_hash=hash_password(PASS), role="user"),
            User(username="bob", email="bob@example.com", password_hash=hash_password(PASS), role="user"),
            User(username="tech", email="tech@example.com", password_hash=hash_password(PASS), role="technician"),
            User(username="boss", email="boss@example.com", password_hash=hash_password(PASS), role="technician", is_admin=True),
        ])
        db.session.commit()


def log_in(client, username):
    token = csrf(client, "/login")
    response = client.post("/login", data={
        "csrf_token": token, "identifier": username, "password": PASS,
    })
    assert response.status_code == 302


def test_profile_requires_authentication(client):
    assert client.get("/profile").status_code == 302
    assert client.get("/profile/password").status_code == 302
    assert client.get("/users").status_code == 302


def test_owner_edits_contact_but_must_confirm_email(client, app):
    users_fixture(app)
    log_in(client, "alice")
    token = csrf(client, "/profile")
    response = client.post("/profile", data={
        "csrf_token": token, "email": "alice@example.com",
        "full_name": "Alice Example", "phone": "+48 501 502 503",
        "organization": "Serwis",
    })
    assert response.status_code == 303
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user.full_name == "Alice Example"
        assert user.phone == "+48 501 502 503"

    response = client.post("/profile", data={
        "csrf_token": token, "email": "alice2@example.com",
        "current_password": "Nieprawidlowe123!",
    })
    assert response.status_code == 422
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user.email == "alice@example.com"

    response = client.post("/profile", data={
        "csrf_token": token, "email": "alice2@example.com",
        "current_password": PASS,
    })
    assert response.status_code == 303
    assert client.get("/profile").status_code == 200
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user.email == "alice2@example.com"
        assert user.auth_version == 2
        assert db.session.scalar(select(SecurityEvent).where(
            SecurityEvent.event_type == "account.profile_updated"
        )) is not None


def test_email_must_be_unique_and_contact_valid(client, app):
    users_fixture(app)
    log_in(client, "alice")
    token = csrf(client, "/profile")
    assert client.post("/profile", data={
        "csrf_token": token, "email": "bob@example.com",
    }).status_code == 422
    assert client.post("/profile", data={
        "csrf_token": token, "email": "alice@example.com",
        "phone": "<script>alert(1)</script>",
    }).status_code == 422


def test_password_change_needs_old_password_and_expires_sessions(client, app):
    users_fixture(app)
    log_in(client, "alice")
    csrf_token = csrf(client, "/profile/password")
    other_client = app.test_client()
    log_in(other_client, "alice")
    invalid = client.post("/profile/password", data={
        "csrf_token": csrf_token, "current_password": "bad",
        "new_password": NEW_PASS, "confirm_password": NEW_PASS,
    })
    assert invalid.status_code == 422
    result = client.post("/profile/password", data={
        "csrf_token": csrf_token, "current_password": PASS,
        "new_password": NEW_PASS, "confirm_password": NEW_PASS,
    })
    assert result.status_code == 303
    assert client.get("/profile").status_code == 200
    assert other_client.get("/profile").status_code == 302
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert verify_password(user.password_hash, NEW_PASS)
        assert user.auth_version == 2


def test_csrf_required_for_profile_and_reset(client, app):
    users_fixture(app)
    log_in(client, "alice")
    assert client.post("/profile", data={"email": "test@example.com"}).status_code == 400
    assert client.post("/profile/password", data={"current_password": PASS}).status_code == 400


def test_users_admin_is_not_same_as_technician(client, app):
    users_fixture(app)
    log_in(client, "tech")
    assert client.get("/users").status_code == 403
    assert client.get("/users/1").status_code == 403
    assert client.post("/users/1/reset-password", data={"admin_password": PASS}).status_code == 400


def test_regular_user_cannot_manage_others(client, app):
    users_fixture(app)
    log_in(client, "alice")
    assert client.get("/users").status_code == 403
    assert client.get("/users/2").status_code == 403


def test_admin_edits_user_with_reauthentication(client, app):
    users_fixture(app)
    log_in(client, "boss")
    assert client.get("/users").status_code == 200
    token = csrf(client, "/users/1")
    assert client.post("/users/1", data={
        "csrf_token": token, "full_name": "Updated",
        "email": "alice-new@example.com", "admin_password": "bad",
    }).status_code == 422
    assert client.post("/users/1", data={
        "csrf_token": token, "full_name": "Updated",
        "email": "alice-new@example.com", "admin_password": PASS,
        "phone": "123456789", "organization": "IT",
    }).status_code == 303
    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "alice"))
        assert user.full_name == "Updated"
        assert user.email == "alice-new@example.com"
        assert user.auth_version == 2
    with app.app_context():
        admin = db.session.scalar(select(User).where(User.username == "boss"))
        assert client.get(f"/users/{admin.id}").status_code == 303


def test_admin_resets_others_password_once_with_forced_rotation(client, app):
    users_fixture(app)
    log_in(client, "boss")
    token = csrf(client, "/users/1")
    before = client.post("/users/1/reset-password", data={
        "csrf_token": token, "admin_password": "bad",
    })
    assert before.status_code == 303
    result = client.post("/users/1/reset-password", data={
        "csrf_token": token, "admin_password": PASS,
    })
    assert result.status_code == 200
    assert result.headers["Cache-Control"] == "no-store"
    with app.app_context():
        target = db.session.scalar(select(User).where(User.username == "alice"))
        assert target.must_change_password
        assert target.auth_version == 2
        temp = re.search(r'id="one-time-password"[^>]+value="([^"]+)"', result.get_data(as_text=True))
        assert temp is not None
        temp_password = temp.group(1)
        assert verify_password(target.password_hash, temp_password)
        assert not verify_password(target.password_hash, PASS)
    client.post("/logout", data={"csrf_token": csrf(client, "/users")})
    token = csrf(client, "/login")
    assert client.post("/login", data={
        "csrf_token": token, "identifier": "alice", "password": temp_password,
    }).headers["Location"].endswith("/profile/password")
    assert client.get("/dashboard").headers["Location"].endswith("/profile/password")
    token = csrf(client, "/profile/password")
    assert client.post("/profile/password", data={
        "csrf_token": token, "current_password": temp_password,
        "new_password": NEW_PASS, "confirm_password": NEW_PASS,
    }).status_code == 303
    assert client.get("/dashboard").status_code == 200
    with app.app_context():
        target = db.session.scalar(select(User).where(User.username == "alice"))
        assert not target.must_change_password


def test_admin_cannot_modify_other_administrators(client, app):
    users_fixture(app)
    log_in(client, "boss")
    # Admin's own account redirects to self-settings.
    with app.app_context():
        admin_id = db.session.scalar(select(User.id).where(User.username == "boss"))
    assert client.get(f"/users/{admin_id}").status_code == 303
    assert client.post(f"/users/{admin_id}/reset-password", data={
        "csrf_token": csrf(client, "/users"), "admin_password": PASS,
    }).status_code == 403
