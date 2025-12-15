"""Remove type column from hats table

Revision ID: 002
Revises: 001
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("hats", "type")


def downgrade() -> None:
    op.add_column(
        "hats",
        sa.Column("type", sa.String(50), nullable=False, server_default="skill"),
    )
    op.alter_column("hats", "type", server_default=None)
