"""Add job_executions table for task queue audit trail

Revision ID: 004
Revises: 003
Create Date: 2025-01-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type first (with create_type=False to prevent auto-creation in table)
    job_status_enum = postgresql.ENUM(
        "queued",
        "running",
        "completed",
        "failed",
        "retrying",
        "cancelled",
        name="job_status",
        create_type=False,
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "job_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", sa.String(255), nullable=False, index=True),
        sa.Column("job_type", sa.String(100), nullable=False, index=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("status", job_status_enum, nullable=False, index=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, default=1),
        sa.Column("max_retries", sa.Integer(), nullable=False, default=3),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_data", postgresql.JSONB, nullable=True),
        sa.Column("result_data", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("worker_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Add composite index for common queries
    op.create_index(
        "ix_job_executions_target",
        "job_executions",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_executions_target", table_name="job_executions")
    op.drop_table("job_executions")
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=True)
