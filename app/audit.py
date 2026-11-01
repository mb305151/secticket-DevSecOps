import time
from datetime import datetime, timezone

import click
from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from .extensions import db
from .models import SecurityEvent
from .rate_limit import fingerprint


RETENTION_DAYS = 30

EVENT_TYPES = {
    "auth.login_failed",
    "auth.login_success",
    "auth.login_rate_limited",
    "auth.register_rate_limited",
    "account.role_granted",
    "account.password_reset",
    "account.profile_updated",
    "account.password_changed",
    "account.admin_granted",
    "ticket.status_changed",
}

VALID_STATUSES = {"open", "in_progress", "closed"}


def add_event(
    event_type,
    *,
    actor_user_id=None,
    target_user_id=None,
    ticket_id=None,
    identity=None,
    old_status=None,
    new_status=None,
):
    if event_type not in EVENT_TYPES:
        raise ValueError("Nieznany typ zdarzenia")

    for status in (old_status, new_status):
        if status is not None and status not in VALID_STATUSES:
            raise ValueError("Nieznany status")

    ip_hash = None

    if has_request_context():
        ip_hash = fingerprint(
            "audit_ip",
            request.remote_addr or "unknown",
        )

    identity_hash = None

    if identity is not None:
        identity_hash = fingerprint(
            "audit_identity",
            str(identity).strip().lower()[:254],
        )

    event = SecurityEvent(
        event_type=event_type,
        created_at=int(time.time()),
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        ticket_id=ticket_id,
        ip_hash=ip_hash,
        identity_hash=identity_hash,
        old_status=old_status,
        new_status=new_status,
    )

    db.session.add(event)
    return event


def cleanup_expired_audit_events():
    cutoff = int(time.time()) - RETENTION_DAYS * 86400

    result = db.session.execute(
        delete(SecurityEvent).where(
            SecurityEvent.created_at < cutoff
        )
    )

    db.session.commit()
    return result.rowcount


def register_audit_logging(app):

    @app.after_request
    def audit_authentication(response):
        if request.method != "POST":
            return response

        endpoint = request.endpoint
        event_type = None

        if endpoint == "auth.login":
            if response.status_code == 200:
                event_type = "auth.login_failed"
            elif response.status_code == 429:
                event_type = "auth.login_rate_limited"
            elif (
                response.status_code in (302, 303)
                and current_user.is_authenticated
            ):
                event_type = "auth.login_success"

        elif endpoint == "auth.register":
            if response.status_code == 429:
                event_type = "auth.register_rate_limited"

        if event_type is None:
            return response

        actor_id = None

        if (
            event_type == "auth.login_success"
            and current_user.is_authenticated
        ):
            actor_id = current_user.id

        identity = (
            request.form.get("identifier", "")
            if endpoint == "auth.login"
            else None
        )

        try:
            add_event(
                event_type,
                actor_user_id=actor_id,
                identity=identity,
            )
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            app.logger.error(
                "Nie udalo sie zapisac zdarzenia audytu"
            )

        return response

    @app.cli.command("audit-recent")
    @click.option(
        "--limit",
        default=20,
        type=click.IntRange(1, 100),
    )
    def audit_recent(limit):
        with app.app_context():
            events = db.session.scalars(
                select(SecurityEvent)
                .order_by(SecurityEvent.id.desc())
                .limit(limit)
            ).all()

            if not events:
                click.echo("Brak zdarzen.")
                return

            for event in events:
                timestamp = datetime.fromtimestamp(
                    event.created_at,
                    tz=timezone.utc,
                ).strftime("%Y-%m-%d %H:%M:%S UTC")

                click.echo(
                    f"{timestamp} | "
                    f"{event.event_type} | "
                    f"actor={event.actor_user_id} | "
                    f"target={event.target_user_id} | "
                    f"ticket={event.ticket_id} | "
                    f"status={event.old_status}->{event.new_status}"
                )
