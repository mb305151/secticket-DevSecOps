import re

from sqlalchemy import select

from app.extensions import db
from app.models import Ticket, User
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


def seed(app):
    with app.app_context():
        alice = User(
            username="alice",
            email="alice@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        )
        bob = User(
            username="bob",
            email="bob@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        )
        db.session.add_all([alice, bob])
        db.session.flush()

        ticket = Ticket(
            user_id=alice.id,
            title="Awaria laptopa",
            description="Laptop nie uruchamia sie prawidlowo.",
            priority="high",
            status="open",
        )
        db.session.add(ticket)
        db.session.commit()

        return ticket.id, bob.id


def login(client, username):
    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={
            "identifier": username,
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302


def test_tickets_require_login(client):
    assert client.get("/tickets/").status_code == 302
    assert client.get("/tickets/new").status_code == 302


def test_owner_can_create_edit_delete(client, app):
    seed(app)
    login(client, "alice")

    token = csrf(client, "/tickets/new")

    response = client.post(
        "/tickets/new",
        data={
            "title": "Nowa awaria",
            "description": "W pomieszczeniu nie dziala siec.",
            "priority": "medium",
            "user_id": "999999",
            "csrf_token": token,
        },
    )

    assert response.status_code == 303

    with app.app_context():
        ticket = db.session.scalar(
            select(Ticket).where(
                Ticket.title == "Nowa awaria"
            )
        )
        assert ticket is not None
        assert ticket.owner.username == "alice"
        ticket_id = ticket.id

    token = csrf(client, f"/tickets/{ticket_id}/edit")

    response = client.post(
        f"/tickets/{ticket_id}/edit",
        data={
            "title": "Zmieniony tytul",
            "description": "Zaktualizowany opis problemu.",
            "priority": "high",
            "csrf_token": token,
        },
    )

    assert response.status_code == 303

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        assert ticket.title == "Zmieniony tytul"
        assert ticket.priority == "high"

    token = csrf(client, f"/tickets/{ticket_id}")

    response = client.post(
        f"/tickets/{ticket_id}/delete",
        data={"csrf_token": token},
    )

    assert response.status_code == 303

    with app.app_context():
        assert db.session.get(Ticket, ticket_id) is None


def test_idor_blocks_other_user(client, app):
    ticket_id, _ = seed(app)
    login(client, "bob")

    assert client.get(
        f"/tickets/{ticket_id}"
    ).status_code == 404

    assert client.get(
        f"/tickets/{ticket_id}/edit"
    ).status_code == 404

    token = csrf(client, "/tickets/new")

    response = client.post(
        f"/tickets/{ticket_id}/edit",
        data={
            "title": "Nieautoryzowana zmiana",
            "description": "Proba modyfikacji cudzych danych.",
            "priority": "low",
            "csrf_token": token,
        },
    )
    assert response.status_code == 404

    response = client.post(
        f"/tickets/{ticket_id}/delete",
        data={"csrf_token": token},
    )
    assert response.status_code == 404

    with app.app_context():
        ticket = db.session.get(Ticket, ticket_id)
        assert ticket is not None
        assert ticket.title == "Awaria laptopa"


def test_search_does_not_expose_other_tickets(client, app):
    seed(app)
    login(client, "bob")

    response = client.get(
        "/tickets/",
        query_string={"q": "Awaria"},
    )
    assert response.status_code == 200
    assert b"Awaria laptopa" not in response.data

    response = client.get(
        "/tickets/",
        query_string={"q": "' OR 1=1 --"},
    )
    assert response.status_code == 200
    assert b"Awaria laptopa" not in response.data


def test_delete_requires_csrf(client, app):
    ticket_id, _ = seed(app)
    login(client, "alice")

    response = client.post(
        f"/tickets/{ticket_id}/delete"
    )
    assert response.status_code == 400

    with app.app_context():
        assert db.session.get(Ticket, ticket_id) is not None


def test_ticket_content_is_escaped(client, app):
    with app.app_context():
        alice = User(
            username="alice",
            email="alice@example.com",
            password_hash=hash_password(PASSWORD),
            role="user",
        )
        db.session.add(alice)
        db.session.flush()

        ticket = Ticket(
            user_id=alice.id,
            title="<script>alert(1)</script>",
            description="Opis z <script>alert(1)</script>.",
            priority="low",
            status="open",
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

    login(client, "alice")

    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    assert b"&lt;script&gt;" in response.data
    assert b"<script>alert(1)</script>" not in response.data
