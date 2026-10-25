"""Add scheduled reminders to tasks.

Revision ID: 0005_task_reminders
Revises: 0004_recovery_code
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_task_reminders"
down_revision = "0004_recovery_code"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_reminder_at", "tasks", ["reminder_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_reminder_at", table_name="tasks")
    op.drop_column("tasks", "reminder_at")
