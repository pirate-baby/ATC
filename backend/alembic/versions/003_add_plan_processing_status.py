"""Add processing_status and processing_error to plans table

Revision ID: 003
Revises: 002
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type
    processing_status_enum = sa.Enum(
        "pending", "generating", "completed", "failed",
        name="processing_status",
        create_type=True,
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)

    # Add the columns
    op.add_column(
        "plans",
        sa.Column(
            "processing_status",
            processing_status_enum,
            nullable=True,
        ),
    )
    op.add_column(
        "plans",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("plans", "processing_error")
    op.drop_column("plans", "processing_status")

    # Drop the enum type
    sa.Enum(name="processing_status").drop(op.get_bind(), checkfirst=True)
