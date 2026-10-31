import hashlib
import hmac
import time
import random

from flask import current_app, make_response
from sqlalchemy import case, delete
from sqlalchemy.dialects.sqlite import insert

from .extensions import db
from .models import RateLimitBucket


def fingerprint(scope, identity):
    secret = current_app.config["SECRET_KEY"].encode("utf-8")

    message = f"{scope}:{identity}".encode("utf-8")

    return hmac.new(
        secret,
        message,
        hashlib.sha256,
    ).hexdigest()


def retry_after(scope, identity, limit):
    now = int(time.time())
    key = fingerprint(scope, identity)

    bucket = db.session.get(
        RateLimitBucket,
        (scope, key),
    )

    if bucket is None:
        return 0

    if bucket.reset_at <= now:
        return 0

    if bucket.attempts < limit:
        return 0

    return max(1, bucket.reset_at - now)


def cleanup_expired_buckets():
    now = int(time.time())

    result = db.session.execute(
        delete(RateLimitBucket).where(
            RateLimitBucket.reset_at <= now
        )
    )

    db.session.commit()
    return result.rowcount


def record_attempt(scope, identity, window_seconds):
    now = int(time.time())

    # Okazjonalne usuwanie wygaslych licznikow.
    # Operacja odbywa sie w tej samej transakcji.
    if random.randrange(100) == 0:
        db.session.execute(
            delete(RateLimitBucket).where(
                RateLimitBucket.reset_at <= now
            )
        )
    deadline = now + window_seconds
    key = fingerprint(scope, identity)

    statement = insert(RateLimitBucket).values(
        scope=scope,
        identifier=key,
        attempts=1,
        reset_at=deadline,
    )

    expired = RateLimitBucket.reset_at <= now

    statement = statement.on_conflict_do_update(
        index_elements=["scope", "identifier"],
        set_={
            "attempts": case(
                (expired, 1),
                else_=RateLimitBucket.attempts + 1,
            ),
            "reset_at": case(
                (expired, deadline),
                else_=RateLimitBucket.reset_at,
            ),
        },
    ).returning(
        RateLimitBucket.attempts,
        RateLimitBucket.reset_at,
    )

    attempts, reset_at = db.session.execute(
        statement
    ).one()

    db.session.commit()

    return attempts, max(1, reset_at - now)


def clear_attempts(scope, identity):
    key = fingerprint(scope, identity)

    db.session.execute(
        delete(RateLimitBucket).where(
            RateLimitBucket.scope == scope,
            RateLimitBucket.identifier == key,
        )
    )

    db.session.commit()


def limit_response(seconds):
    response = make_response(
        "Zbyt wiele prob. Sprobuj ponownie pozniej.",
        429,
    )

    response.headers["Retry-After"] = str(
        max(1, int(seconds))
    )

    response.headers["Cache-Control"] = "no-store"

    return response
