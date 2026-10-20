"""Create initial users and tasks tables.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("admin", "user", name="user_role")
task_status = sa.Enum("pending", "completed", name="task_status")
task_priority = sa.Enum("low", "medium", "high", name="task_priority")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, server_default="user", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", task_status, server_default="pending", nullable=False),
        sa.Column("priority", task_priority, server_default="medium", nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_tasks_title_not_empty"),
        sa.CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) OR "
            "(status = 'pending' AND completed_at IS NULL)",
            name="ck_tasks_completion_timestamp_matches_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)
    op.create_index("ix_tasks_user_id_status", "tasks", ["user_id", "status"], unique=False)
    op.create_index("ix_tasks_user_id_created_at", "tasks", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_user_id_created_at", table_name="tasks")
    op.drop_index("ix_tasks_user_id_status", table_name="tasks")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_users_role_active", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS task_priority")
        op.execute("DROP TYPE IF EXISTS task_status")
        op.execute("DROP TYPE IF EXISTS user_role")
