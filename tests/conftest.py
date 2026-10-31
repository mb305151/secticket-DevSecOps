import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_PATH",
        str(tmp_path / "secticket-test.db")
    )
    monkeypatch.setenv(
        "SECRET_KEY",
        "secret-only-for-automated-tests"
    )

    application = create_app()
    application.config["TESTING"] = True

    with application.app_context():
        db.create_all()

    yield application

    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()
