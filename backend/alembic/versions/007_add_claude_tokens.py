"""Add claude_tokens table for subscription token pooling

Revision ID: 007
Revises: 006
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type for token status
    op.execute(
        "CREATE TYPE claude_token_status AS ENUM ('active', 'invalid', 'rate_limited', 'expired')"
    )

    # Create claude_tokens table
    op.create_table(
        "claude_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "invalid",
                "rate_limited",
                "expired",
                name="claude_token_status",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique index on user_id (one token per user)
    op.create_index(
        "ix_claude_tokens_user_id", "claude_tokens", ["user_id"], unique=True
    )

    # Create index on status for pool queries
    op.create_index("ix_claude_tokens_status", "claude_tokens", ["status"])

    # Create index for rotation algorithm (finding least-used tokens)
    op.create_index(
        "ix_claude_tokens_request_count", "claude_tokens", ["request_count"]
    )


def downgrade() -> None:
    op.drop_index("ix_claude_tokens_request_count", table_name="claude_tokens")
    op.drop_index("ix_claude_tokens_status", table_name="claude_tokens")
    op.drop_index("ix_claude_tokens_user_id", table_name="claude_tokens")
    op.drop_table("claude_tokens")
    op.execute("DROP TYPE claude_token_status")
