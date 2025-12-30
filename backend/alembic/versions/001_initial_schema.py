"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-12-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types first
    op.execute(
        "CREATE TYPE comment_thread_target_type AS ENUM ('PLAN', 'TASK', 'LINE')"
    )
    op.execute(
        "CREATE TYPE comment_thread_status AS ENUM ('OPEN', 'RESOLVED', 'SUMMARIZED')"
    )
    op.execute(
        "CREATE TYPE job_status AS ENUM ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING', 'CANCELLED')"
    )
    op.execute(
        "CREATE TYPE plan_task_status AS ENUM ('BACKLOG', 'BLOCKED', 'CODING', 'REVIEW', 'APPROVED', 'CICD', 'MERGED', 'CLOSED')"
    )
    op.execute(
        "CREATE TYPE processing_status AS ENUM ('pending', 'generating', 'completed', 'failed')"
    )
    op.execute(
        "CREATE TYPE triage_provider AS ENUM ('LINEAR', 'GITHUB_ISSUES', 'JIRA', 'GITLAB_ISSUES')"
    )
    op.execute("CREATE TYPE triage_item_status AS ENUM ('PENDING', 'PLANNED', 'REJECTED')")
    op.execute("CREATE TYPE review_target_type AS ENUM ('PLAN', 'TASK')")
    op.execute("CREATE TYPE review_decision AS ENUM ('APPROVED', 'REQUEST_CHANGES')")
    op.execute(
        "CREATE TYPE claude_token_status AS ENUM ('ACTIVE', 'INVALID', 'RATE_LIMITED', 'EXPIRED')"
    )

    # Independent tables first (no FKs to other app tables)
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("git_handle", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("git_handle"),
    )

    op.create_table(
        "hats",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "triage_connections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "LINEAR",
                "GITHUB_ISSUES",
                "JIRA",
                "GITLAB_ISSUES",
                name="triage_provider",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "coding_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output_log", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_sessions_status", "coding_sessions", ["status"])
    op.create_index("ix_coding_sessions_target_id", "coding_sessions", ["target_id"])
    op.create_index("ix_coding_sessions_target_type", "coding_sessions", ["target_type"])

    op.create_table(
        "comment_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "target_type",
            postgresql.ENUM(
                "PLAN", "TASK", "LINE", name="comment_thread_target_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "OPEN",
                "RESOLVED",
                "SUMMARIZED",
                name="comment_thread_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comment_threads_target_id", "comment_threads", ["target_id"])

    op.create_table(
        "job_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "QUEUED",
                "RUNNING",
                "COMPLETED",
                "FAILED",
                "RETRYING",
                "CANCELLED",
                name="job_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_executions_job_id", "job_executions", ["job_id"])
    op.create_index("ix_job_executions_job_type", "job_executions", ["job_type"])
    op.create_index("ix_job_executions_status", "job_executions", ["status"])
    op.create_index("ix_job_executions_target_id", "job_executions", ["target_id"])

    # Projects (depends on triage_connections)
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("git_url", sa.String(length=2048), nullable=False),
        sa.Column("main_branch", sa.String(length=255), nullable=False),
        sa.Column("triage_connection_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["triage_connection_id"], ["triage_connections.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Plans and Tasks - create without circular FKs first
    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "BACKLOG",
                "BLOCKED",
                "CODING",
                "REVIEW",
                "APPROVED",
                "CICD",
                "MERGED",
                "CLOSED",
                name="plan_task_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("parent_task_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "processing_status",
            postgresql.ENUM(
                "pending",
                "generating",
                "completed",
                "failed",
                name="processing_status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "BACKLOG",
                "BLOCKED",
                "CODING",
                "REVIEW",
                "APPROVED",
                "CICD",
                "MERGED",
                "CLOSED",
                name="plan_task_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("branch_name", sa.String(length=255), nullable=True),
        sa.Column("worktree_path", sa.String(length=1024), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("session_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_output_log", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add the circular FK from plans to tasks
    op.create_foreign_key(
        "fk_plans_parent_task_id",
        "plans",
        "tasks",
        ["parent_task_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Claude tokens (depends on users)
    op.create_table(
        "claude_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "INVALID",
                "RATE_LIMITED",
                "EXPIRED",
                name="claude_token_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Comments (depends on comment_threads, users)
    op.create_table(
        "comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("parent_comment_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["thread_id"], ["comment_threads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"], ["comments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Reviews (depends on users)
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "target_type",
            postgresql.ENUM("PLAN", "TASK", name="review_target_type", create_type=False),
            nullable=False,
        ),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column(
            "decision",
            postgresql.ENUM(
                "APPROVED", "REQUEST_CHANGES", name="review_decision", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reviews_target_id", "reviews", ["target_id"])

    # Task blocking (depends on tasks)
    op.create_table(
        "task_blocking",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("blocked_by_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_by_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "blocked_by_id"),
    )

    # Task images (depends on tasks)
    op.create_table(
        "task_images",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Triage items (depends on triage_connections, plans)
    op.create_table(
        "triage_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("connection_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("external_url", sa.String(length=2048), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "PLANNED", "REJECTED", name="triage_item_status", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["triage_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Project settings (depends on projects)
    op.create_table(
        "project_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("required_approvals_plan", sa.Integer(), nullable=False),
        sa.Column("required_approvals_task", sa.Integer(), nullable=False),
        sa.Column("auto_approve_main_updates", sa.Boolean(), nullable=False),
        sa.Column("assigned_hats", postgresql.ARRAY(sa.UUID()), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("project_settings")
    op.drop_table("triage_items")
    op.drop_table("task_images")
    op.drop_table("task_blocking")
    op.drop_index("ix_reviews_target_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_table("comments")
    op.drop_table("claude_tokens")
    op.drop_constraint("fk_plans_parent_task_id", "plans", type_="foreignkey")
    op.drop_table("tasks")
    op.drop_table("plans")
    op.drop_table("projects")
    op.drop_index("ix_job_executions_target_id", table_name="job_executions")
    op.drop_index("ix_job_executions_status", table_name="job_executions")
    op.drop_index("ix_job_executions_job_type", table_name="job_executions")
    op.drop_index("ix_job_executions_job_id", table_name="job_executions")
    op.drop_table("job_executions")
    op.drop_index("ix_comment_threads_target_id", table_name="comment_threads")
    op.drop_table("comment_threads")
    op.drop_index("ix_coding_sessions_target_type", table_name="coding_sessions")
    op.drop_index("ix_coding_sessions_target_id", table_name="coding_sessions")
    op.drop_index("ix_coding_sessions_status", table_name="coding_sessions")
    op.drop_table("coding_sessions")
    op.drop_table("triage_connections")
    op.drop_table("hats")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS claude_token_status")
    op.execute("DROP TYPE IF EXISTS review_decision")
    op.execute("DROP TYPE IF EXISTS review_target_type")
    op.execute("DROP TYPE IF EXISTS triage_item_status")
    op.execute("DROP TYPE IF EXISTS triage_provider")
    op.execute("DROP TYPE IF EXISTS processing_status")
    op.execute("DROP TYPE IF EXISTS plan_task_status")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS comment_thread_status")
    op.execute("DROP TYPE IF EXISTS comment_thread_target_type")
