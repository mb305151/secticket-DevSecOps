"""add contact profiles, administrative permission and session version

Revision ID: a65f1c2e940b
Revises: 60b02fdc0a34
"""
from alembic import op
import sqlalchemy as sa

revision = "a65f1c2e940b"
down_revision = "60b02fdc0a34"
branch_labels = None
depends_on = None


def upgrade():
    # Simple ADD COLUMN operations: no SQLite table recreation and no data loss.
    op.add_column("users", sa.Column("full_name", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("organization", sa.String(120), nullable=True))
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "auth_version")
    op.drop_column("users", "is_admin")
    op.drop_column("users", "organization")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
