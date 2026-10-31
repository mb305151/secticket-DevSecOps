from datetime import datetime, timezone

from flask_login import UserMixin

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        index=True
    )

    email = db.Column(
        db.String(254),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default="user",
        server_default="user"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    tickets = db.relationship(
        "Ticket",
        back_populates="owner",
        passive_deletes=True
    )

    comments = db.relationship(
        "Comment",
        back_populates="author",
        passive_deletes=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('user', 'technician')",
            name="ck_users_role"
        ),
    )


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default="medium",
        server_default="medium"
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="open",
        server_default="open"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now
    )

    owner = db.relationship(
        "User",
        back_populates="tickets"
    )

    comments = db.relationship(
        "Comment",
        back_populates="ticket",
        passive_deletes=True
    )

    __table_args__ = (
        db.CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_tickets_priority"
        ),
        db.CheckConstraint(
            "status IN ('open', 'in_progress', 'closed')",
            name="ck_tickets_status"
        ),
    )


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now
    )

    ticket = db.relationship(
        "Ticket",
        back_populates="comments"
    )

    author = db.relationship(
        "User",
        back_populates="comments"
    )


class RateLimitBucket(db.Model):
    __tablename__ = "rate_limit_buckets"

    scope = db.Column(
        db.String(32),
        primary_key=True
    )

    identifier = db.Column(
        db.String(64),
        primary_key=True
    )

    attempts = db.Column(
        db.Integer,
        nullable=False
    )

    reset_at = db.Column(
        db.Integer,
        nullable=False
    )

    __table_args__ = (
        db.CheckConstraint(
            "attempts >= 1",
            name="ck_rate_limit_attempts"
        ),
    )


class SecurityEvent(db.Model):
    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(
        db.String(50), nullable=False, index=True
    )
    created_at = db.Column(
        db.Integer, nullable=False, index=True
    )

    actor_user_id = db.Column(db.Integer)
    target_user_id = db.Column(db.Integer)
    ticket_id = db.Column(db.Integer)

    ip_hash = db.Column(db.String(64))
    identity_hash = db.Column(db.String(64))

    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
