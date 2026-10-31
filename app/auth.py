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
from .security import hash_password, verify_password


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get(
            "username", ""
        ).strip().lower()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not re.fullmatch(r"[a-z0-9_]{3,30}", username):
            flash(
                "Login musi miec od 3 do 30 znakow "
                "(litery, cyfry, podkreslenie).",
                "error",
            )
        elif (
            len(email) > 254
            or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+", email
            )
        ):
            flash("Podaj poprawny adres e-mail.", "error")
        elif password != confirm:
            flash("Hasla nie sa identyczne.", "error")
        elif not 12 <= len(password) <= 128:
            flash(
                "Haslo musi miec od 12 do 128 znakow.",
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
                    "Login lub e-mail jest juz zajety.",
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
                        "Login lub e-mail jest juz zajety.",
                        "error",
                    )
                else:
                    flash(
                        "Konto utworzone. Mozesz sie zalogowac.",
                        "success",
                    )
                    return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get(
            "identifier", ""
        ).strip().lower()

        password = request.form.get("password", "")

        user = db.session.scalar(
            select(User).where(
                or_(
                    User.username == identifier,
                    User.email == identifier,
                )
            )
        )

        if user and verify_password(
            user.password_hash, password
        ):
            login_user(user, remember=False)
            return redirect(url_for("dashboard"))

        flash(
            "Nieprawidlowy login/e-mail lub haslo.",
            "error",
        )

    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Wylogowano pomyslnie.", "success")
    return redirect(url_for("auth.login"))
