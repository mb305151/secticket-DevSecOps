import os
import sqlite3

from pathlib import Path

from flask import Flask, jsonify, render_template, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .extensions import (
    csrf,
    db,
    login_manager,
    migrate,
)


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
            "/app/data/secticket.db",
        )
    ).resolve()

    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1048576,
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
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = (
        "Zaloguj sie, aby uzyskac dostep."
    )
    login_manager.login_message_category = "error"

    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        try:
            pk, version = user_id.split(":", 1)
            user = db.session.get(models.User, int(pk))
            if user is not None and user.auth_version == int(version):
                return user
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .tickets import tickets_bp
    app.register_blueprint(tickets_bp)

    from .profiles import profiles_bp
    app.register_blueprint(profiles_bp)

    @app.before_request
    def require_new_password_after_reset():
        # A temporary password may only be used to set a personal password.
        if (
            current_user.is_authenticated
            and current_user.must_change_password
            and request.endpoint not in {
                "profiles.change_password", "auth.logout", "static", "health"
            }
        ):
            return redirect(url_for("profiles.change_password"))

    from .cli import register_cli
    register_cli(app)

    from .audit import register_audit_logging
    register_audit_logging(app)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        # Counts are scoped to the logged-in user unless they are a technician.
        from sqlalchemy import func, select
        from .models import Ticket

        scope = []
        if current_user.role != "technician":
            scope.append(Ticket.user_id == current_user.id)

        stats = {
            "total": db.session.scalar(
                select(func.count(Ticket.id)).where(*scope)
            ) or 0,
        }
        for status in ("open", "in_progress", "closed"):
            stats[status] = db.session.scalar(
                select(func.count(Ticket.id)).where(
                    *scope, Ticket.status == status
                )
            ) or 0

        recent_tickets = db.session.scalars(
            select(Ticket)
            .where(*scope)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(5)
        ).all()
        return render_template(
            "dashboard.html",
            user=current_user,
            stats=stats,
            recent_tickets=recent_tickets,
        )

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    return app
