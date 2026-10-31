import os
import sqlite3

from pathlib import Path

from flask import Flask, jsonify, render_template
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .extensions import db, migrate


@event.listens_for(Engine, "connect")
def configure_sqlite(dbapi_connection, connection_record):
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_app():
    app = Flask(__name__)

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("Brak zmiennej SECRET_KEY")

    database_path = Path(
        os.environ.get(
            "DATABASE_PATH",
            "/app/data/secticket.db"
        )
    ).resolve()

    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"timeout": 10}
        },
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get(
            "COOKIE_SECURE", "false"
        ).lower() == "true",
    )

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    return app
