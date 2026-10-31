from sqlalchemy import select

from app.extensions import db
from app.models import User
from app.security import hash_password, verify_password


def test_reset_password_cli(app):
    old_password = "StareHaslo123!"
    new_password = "NoweBezpieczne123!"

    with app.app_context():
        db.session.add(User(
            username="technikdemo",
            email="technikdemo@example.com",
            password_hash=hash_password(old_password),
            role="technician",
        ))
        db.session.commit()

    result = app.test_cli_runner().invoke(
        args=["reset-password", "technikdemo"],
        input=f"{new_password}\n{new_password}\n",
    )

    assert result.exit_code == 0, result.output

    with app.app_context():
        user = db.session.scalar(
            select(User).where(
                User.username == "technikdemo"
            )
        )

        assert verify_password(
            user.password_hash, new_password
        )
        assert not verify_password(
            user.password_hash, old_password
        )
