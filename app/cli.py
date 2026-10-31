import click

from sqlalchemy import select

from .extensions import db
from .models import User
from .audit import add_event
from .security import hash_password


def register_cli(app):

    @app.cli.command("grant-technician")
    @click.argument("username")
    def grant_technician(username):
        username = username.strip().lower()

        with app.app_context():
            user = db.session.scalar(
                select(User).where(
                    User.username == username
                )
            )

            if user is None:
                raise click.ClickException(
                    "Nie znaleziono uzytkownika."
                )

            if user.role == "technician":
                click.echo(
                    "Uzytkownik ma juz role technika."
                )
                return

            user.role = "technician"

            add_event(
                "account.role_granted",
                target_user_id=user.id,
            )

            db.session.commit()

            click.echo(
                "Przyznano role technika."
            )


    @app.cli.command("reset-password")
    @click.argument("username")
    def reset_password(username):
        with app.app_context():
            user = db.session.scalar(
                select(User).where(
                    User.username == username.strip().lower()
                )
            )

            if user is None:
                raise click.ClickException(
                    "Nie znaleziono uzytkownika."
                )

            new_password = click.prompt(
                "Nowe haslo",
                hide_input=True,
                confirmation_prompt=True,
                type=str,
            )

            try:
                user.password_hash = hash_password(new_password)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc

            add_event(
                "account.password_reset",
                target_user_id=user.id,
            )

            db.session.commit()
            click.echo("Haslo zostalo zmienione.")
