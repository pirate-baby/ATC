"""Add session fields to tasks table

Revision ID: 006
Revises: 005
Create Date: 2025-01-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("session_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("session_ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("session_output_log", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "session_output_log")
    op.drop_column("tasks", "session_ended_at")
    op.drop_column("tasks", "session_started_at")
