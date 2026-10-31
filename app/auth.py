import re

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import User
from .security import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    password_checks,
    verify_password,
)
from .rate_limit import (
    clear_attempts,
    limit_response,
    record_attempt,
    retry_after,
)


auth_bp = Blueprint("auth", __name__)

LOGIN_WINDOW = 900
LOGIN_ACCOUNT_LIMIT = 5
LOGIN_IP_LIMIT = 20

REGISTER_WINDOW = 3600
REGISTER_IP_LIMIT = 5


def client_ip():
    # Nie ufamy naglowkowi X-Forwarded-For.
    return request.remote_addr or "unknown"


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        ip = client_ip()

        remaining = retry_after(
            "register_ip", ip, REGISTER_IP_LIMIT
        )
        if remaining:
            return limit_response(remaining)

        attempts, remaining = record_attempt(
            "register_ip", ip, REGISTER_WINDOW
        )

        if attempts > REGISTER_IP_LIMIT:
            return limit_response(remaining)

        username = request.form.get(
            "username", ""
        ).strip().lower()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not re.fullmatch(
            r"[a-z0-9_]{3,30}", username
        ):
            flash(
                "Login musi miec od 3 do 30 znakow.",
                "error",
            )

        elif (
            len(email) > 254
            or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                email,
            )
        ):
            flash(
                "Podaj poprawny adres e-mail.",
                "error",
            )

        elif password != confirm:
            flash(
                "Hasla nie sa identyczne.",
                "error",
            )

        elif not all(
            password_checks(password).values()
        ):
            flash(
                "Haslo nie spelnia wymagan bezpieczenstwa.",
                "error",
            )

        else:
            existing = db.session.scalar(
                select(User).where(
                    or_(
                        User.username == username,
                        User.email == email,
                    )
                )
            )

            if existing:
                flash(
                    "Nie mozna utworzyc konta z podanymi danymi.",
                    "error",
                )

            else:
                user = User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role="user",
                )

                db.session.add(user)

                try:
                    db.session.commit()

                except IntegrityError:
                    db.session.rollback()
                    flash(
                        "Nie mozna utworzyc konta z podanymi danymi.",
                        "error",
                    )

                else:
                    flash(
                        "Konto utworzone. Mozesz sie zalogowac.",
                        "success",
                    )
                    return redirect(
                        url_for("auth.login")
                    )

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        ip = client_ip()

        identifier = request.form.get(
            "identifier", ""
        ).strip().lower()

        password = request.form.get("password", "")

        # Najpierw ograniczenie globalne dla IP.
        remaining = retry_after(
            "login_ip", ip, LOGIN_IP_LIMIT
        )

        if remaining:
            return limit_response(remaining)

        # Dla istniejacego konta obie metody logowania
        # (username i e-mail) maja wspolny licznik.
        user = None

        if 0 < len(identifier) <= 254:
            user = db.session.scalar(
                select(User).where(
                    or_(
                        User.username == identifier,
                        User.email == identifier,
                    )
                )
            )

        account_identity = (
            f"user:{user.id}"
            if user
            else f"unknown:{identifier[:254]}"
        )

        remaining = retry_after(
            "login_account",
            account_identity,
            LOGIN_ACCOUNT_LIMIT,
        )

        if remaining:
            return limit_response(remaining)

        stored_hash = (
            user.password_hash
            if user
            else DUMMY_PASSWORD_HASH
        )

        password_correct = verify_password(
            stored_hash, password
        )

        if user and password_correct:
            clear_attempts(
                "login_account",
                account_identity,
            )

            login_user(user, remember=False)

            return redirect(
                url_for("dashboard")
            )

        # Bledne logowanie - aktualizujemy oba liczniki.
        ip_attempts, ip_remaining = record_attempt(
            "login_ip", ip, LOGIN_WINDOW
        )

        account_attempts, account_remaining = (
            record_attempt(
                "login_account",
                account_identity,
                LOGIN_WINDOW,
            )
        )

        if (
            ip_attempts >= LOGIN_IP_LIMIT
            or account_attempts >= LOGIN_ACCOUNT_LIMIT
        ):
            return limit_response(
                max(ip_remaining, account_remaining)
            )

        flash(
            "Nieprawidlowy login/e-mail lub haslo.",
            "error",
        )

    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()

    flash(
        "Wylogowano pomyslnie.",
        "success",
    )

    return redirect(
        url_for("auth.login")
    )
