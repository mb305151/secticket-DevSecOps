import re
import time

from sqlalchemy import select

from app.audit import cleanup_expired_audit_events
from app.extensions import db
from app.models import SecurityEvent, Ticket, User
from app.security import hash_password


PASSWORD = "BezpieczneHaslo123!"


def csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )

    assert match is not None
    return match.group(1)


def test_login_audit_without_secrets(client, app):
    with app.app_context():
        db.session.add(User(
            username="alice",
            email="alice@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        ))
        db.session.commit()

    token = csrf(client, "/login")

    wrong = client.post(
        "/login",
        data={
            "identifier": "alice",
            "password": "BledneHaslo123!",
            "csrf_token": token,
        },
    )
    assert wrong.status_code == 200

    correct = client.post(
        "/login",
        data={
            "identifier": "alice",
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert correct.status_code == 302

    with app.app_context():
        events = db.session.scalars(
            select(SecurityEvent).order_by(SecurityEvent.id)
        ).all()

        assert [event.event_type for event in events] == [
            "auth.login_failed",
            "auth.login_success",
        ]

        assert events[0].identity_hash is not None
        assert len(events[0].identity_hash) == 64
        assert events[0].identity_hash != "alice"
        assert events[0].ip_hash != "127.0.0.1"

        assert events[1].actor_user_id is not None


def test_role_and_password_audit(app):
    with app.app_context():
        db.session.add(User(
            username="technik",
            email="technik@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        ))
        db.session.commit()

    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["grant-technician", "technik"]
    )
    assert result.exit_code == 0, result.output

    new_password = "NoweBezpieczne123!"

    result = runner.invoke(
        args=["reset-password", "technik"],
        input=f"{new_password}\n{new_password}\n",
    )
    assert result.exit_code == 0, result.output

    with app.app_context():
        events = db.session.scalars(
            select(SecurityEvent).order_by(SecurityEvent.id)
        ).all()

        assert [event.event_type for event in events] == [
            "account.role_granted",
            "account.password_reset",
        ]

        assert events[0].target_user_id is not None
        assert events[1].target_user_id is not None


def test_ticket_status_audit(client, app):
    with app.app_context():
        owner = User(
            username="alice",
            email="alice@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        )
        technician = User(
            username="technik",
            email="technik@example.com",
            password_hash=hash_password(PASSWORD),
            role="technician",
        )

        db.session.add_all([owner, technician])
        db.session.flush()

        ticket = Ticket(
            user_id=owner.id,
            title="Awaria serwera",
            description="Serwer nie odpowiada od rana.",
            priority="high",
            status="open",
        )

        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    token = csrf(client, "/login")

    response = client.post(
        "/login",
        data={
            "identifier": "technik",
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302

    token = csrf(client, f"/tickets/{ticket_id}")

    response = client.post(
        f"/tickets/{ticket_id}/status",
        data={
            "status": "in_progress",
            "csrf_token": token,
        },
    )

    assert response.status_code == 303

    with app.app_context():
        event = db.session.scalar(
            select(SecurityEvent).where(
                SecurityEvent.event_type
                == "ticket.status_changed"
            )
        )

        assert event is not None
        assert event.ticket_id == ticket_id
        assert event.old_status == "open"
        assert event.new_status == "in_progress"


def test_audit_retention(app):
    now = int(time.time())

    with app.app_context():
        db.session.add_all([
            SecurityEvent(
                event_type="auth.login_failed",
                created_at=now - 31 * 86400,
            ),
            SecurityEvent(
                event_type="auth.login_success",
                created_at=now,
            ),
        ])
        db.session.commit()

        assert cleanup_expired_audit_events() == 1

        remaining = db.session.scalars(
            select(SecurityEvent)
        ).all()

        assert len(remaining) == 1
        assert remaining[0].event_type == "auth.login_success"
