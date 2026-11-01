"""Account settings and administrator-only profile management."""

import re
import secrets
import string

from flask import (
    Blueprint, abort, flash, make_response, redirect,
    render_template, request, url_for,
)
from flask_login import current_user, login_required, login_user
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from .audit import add_event
from .extensions import db
from .models import User
from .rate_limit import clear_attempts, limit_response, record_attempt, retry_after
from .security import hash_password, password_checks, verify_password

profiles_bp = Blueprint("profiles", __name__)

AUTH_WINDOW = 900
AUTH_LIMIT = 5


def email_is_valid(email):
    return len(email) <= 254 and bool(
        re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    )


def validate_contacts(form):
    values = {
        "full_name": form.get("full_name", "").strip(),
        "email": form.get("email", "").strip().lower(),
        "phone": form.get("phone", "").strip(),
        "organization": form.get("organization", "").strip(),
    }
    errors = []
    if not email_is_valid(values["email"]):
        errors.append("Podaj poprawny adres e-mail (maks. 254 znaki).")
    if len(values["full_name"]) > 120:
        errors.append("Imię i nazwisko mogą mieć maks. 120 znaków.")
    if len(values["organization"]) > 120:
        errors.append("Nazwa działu lub organizacji może mieć maks. 120 znaków.")
    if values["phone"] and not re.fullmatch(r"[+0-9 ()\-]{6,30}", values["phone"]):
        errors.append("Podaj poprawny numer telefonu (6–30 znaków).")
    return values, errors


def is_taken_email(email, user_id):
    return db.session.scalar(
        select(User.id).where(User.email == email, User.id != user_id)
    ) is not None


def require_password(password, identity):
    """Re-authenticate sensitive actions; throttle incorrect passwords."""
    remaining = retry_after("account_reauth", identity, AUTH_LIMIT)
    if remaining:
        return limit_response(remaining)
    if verify_password(current_user.password_hash, password):
        clear_attempts("account_reauth", identity)
        return None
    attempts, remaining = record_attempt("account_reauth", identity, AUTH_WINDOW)
    if attempts >= AUTH_LIMIT:
        return limit_response(remaining)
    return False


def finish_contacts(user, values, actor_id):
    email_changed = values["email"] != user.email
    for key, value in values.items():
        setattr(user, key, value if key == "email" else (value or None))
    if email_changed:
        # Expire other signed-in sessions after a change of account identifier.
        user.auth_version += 1
    add_event(
        "account.profile_updated",
        actor_user_id=actor_id,
        target_user_id=user.id,
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return False
    return True


@profiles_bp.route("/profile", methods=["GET", "POST"])
@login_required
def my_profile():
    values = {
        "full_name": current_user.full_name or "",
        "email": current_user.email,
        "phone": current_user.phone or "",
        "organization": current_user.organization or "",
    }
    if request.method == "POST":
        values, errors = validate_contacts(request.form)
        if is_taken_email(values["email"], current_user.id):
            errors.append("Ten adres e-mail jest już zajęty.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("profiles/my_profile.html", values=values), 422
        email_changed = values["email"] != current_user.email
        if email_changed:
            authenticated = require_password(
                request.form.get("current_password", ""),
                f"user:{current_user.id}",
            )
            if authenticated is not None:
                if authenticated is False:
                    flash("Nieprawidłowe aktualne hasło.", "error")
                    return render_template("profiles/my_profile.html", values=values), 422
                return authenticated
        if not finish_contacts(current_user, values, current_user.id):
            flash("Nie udało się zapisać zmian. Sprawdź adres e-mail.", "error")
            return render_template("profiles/my_profile.html", values=values), 422
        if email_changed:
            login_user(current_user, fresh=True)
        flash("Dane profilu zostały zapisane.", "success")
        return redirect(url_for("profiles.my_profile"), code=303)
    return render_template("profiles/my_profile.html", values=values)


@profiles_bp.route("/profile/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        authenticated = require_password(
            request.form.get("current_password", ""),
            f"user:{current_user.id}",
        )
        if authenticated is not None:
            if authenticated is False:
                flash("Nieprawidłowe aktualne hasło.", "error")
                return render_template("profiles/change_password.html"), 422
            return authenticated
        password = request.form.get("new_password", "")
        confirmation = request.form.get("confirm_password", "")
        if password != confirmation:
            flash("Nowe hasła nie są identyczne.", "error")
        elif not all(password_checks(password).values()):
            flash("Nowe hasło nie spełnia wymagań bezpieczeństwa.", "error")
        elif verify_password(current_user.password_hash, password):
            flash("Nowe hasło musi być inne niż dotychczasowe.", "error")
        else:
            current_user.password_hash = hash_password(password)
            current_user.auth_version += 1
            current_user.must_change_password = False
            add_event(
                "account.password_changed",
                actor_user_id=current_user.id,
                target_user_id=current_user.id,
            )
            db.session.commit()
            login_user(current_user, fresh=True)
            flash("Hasło zostało zmienione. Inne sesje zostały wylogowane.", "success")
            return redirect(url_for("profiles.my_profile"), code=303)
        return render_template("profiles/change_password.html"), 422
    return render_template("profiles/change_password.html")


def admin_required():
    if not current_user.is_admin:
        abort(403)


@profiles_bp.get("/users")
@login_required
def users():
    admin_required()
    q = request.args.get("q", "").strip()[:80]
    page = max(1, request.args.get("page", 1, type=int))
    statement = select(User)
    if q:
        statement = statement.where(or_(
            User.username.icontains(q, autoescape=True),
            User.email.icontains(q, autoescape=True),
            User.full_name.icontains(q, autoescape=True),
        ))
    users_page = db.paginate(
        statement.order_by(User.id), page=page, per_page=12, error_out=False,
    )
    return render_template("profiles/users.html", users_page=users_page, q=q)


@profiles_bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    admin_required()
    target = db.get_or_404(User, user_id)
    if target.id == current_user.id:
        return redirect(url_for("profiles.my_profile"), code=303)
    # Administrative accounts can be modified only locally, via the trusted CLI.
    if target.is_admin:
        abort(403)
    values = {
        "full_name": target.full_name or "",
        "email": target.email,
        "phone": target.phone or "",
        "organization": target.organization or "",
    }
    if request.method == "POST":
        values, errors = validate_contacts(request.form)
        if is_taken_email(values["email"], target.id):
            errors.append("Ten adres e-mail jest już zajęty.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("profiles/edit_user.html", target=target, values=values), 422
        authenticated = require_password(
            request.form.get("admin_password", ""),
            f"user:{current_user.id}",
        )
        if authenticated is not None:
            if authenticated is False:
                flash("Nieprawidłowe hasło administratora.", "error")
                return render_template("profiles/edit_user.html", target=target, values=values), 422
            return authenticated
        if not finish_contacts(target, values, current_user.id):
            flash("Nie udało się zapisać danych tego konta.", "error")
            return render_template("profiles/edit_user.html", target=target, values=values), 422
        flash("Dane użytkownika zostały zapisane.", "success")
        return redirect(url_for("profiles.edit_user", user_id=target.id), code=303)
    return render_template("profiles/edit_user.html", target=target, values=values)


def generate_temporary_password():
    alphabet = string.ascii_letters + string.digits + "!@#%_-"
    return (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
        + secrets.choice("!@#%_-")
        + "".join(secrets.choice(alphabet) for _ in range(16))
    )


@profiles_bp.post("/users/<int:user_id>/reset-password")
@login_required
def reset_user_password(user_id):
    admin_required()
    target = db.get_or_404(User, user_id)
    if target.id == current_user.id or target.is_admin:
        abort(403)
    authenticated = require_password(
        request.form.get("admin_password", ""),
        f"user:{current_user.id}",
    )
    if authenticated is not None:
        if authenticated is False:
            flash("Nieprawidłowe hasło administratora.", "error")
            return redirect(url_for("profiles.edit_user", user_id=target.id), code=303)
        return authenticated
    temporary_password = generate_temporary_password()
    target.password_hash = hash_password(temporary_password)
    target.auth_version += 1
    target.must_change_password = True
    add_event(
        "account.password_reset",
        actor_user_id=current_user.id,
        target_user_id=target.id,
    )
    db.session.commit()
    response = make_response(render_template(
        "profiles/reset_result.html", target=target,
        temporary_password=temporary_password,
    ))
    # Temporary password is displayed once, never flashed into a session cookie.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
