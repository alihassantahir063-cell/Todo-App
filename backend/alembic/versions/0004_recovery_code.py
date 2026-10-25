"""Add hashed account recovery codes.

Revision ID: 0004_recovery_code
Revises: 0003_password_reset
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_recovery_code"
down_revision = "0003_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("recovery_code_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "recovery_code_hash")
