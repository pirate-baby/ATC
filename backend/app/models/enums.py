from enum import Enum


class PlanTaskStatus(str, Enum):
    BACKLOG = "backlog"
    BLOCKED = "blocked"
    CODING = "coding"
    REVIEW = "review"
    APPROVED = "approved"
    CICD = "cicd"
    MERGED = "merged"
    CLOSED = "closed"


class TriageProvider(str, Enum):
    LINEAR = "linear"
    GITHUB_ISSUES = "github_issues"
    JIRA = "jira"
    GITLAB_ISSUES = "gitlab_issues"


class TriageItemStatus(str, Enum):
    PENDING = "pending"
    PLANNED = "planned"
    REJECTED = "rejected"


class CommentThreadTargetType(str, Enum):
    PLAN = "plan"
    TASK = "task"
    LINE = "line"


class CommentThreadStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUMMARIZED = "summarized"


class ReviewTargetType(str, Enum):
    PLAN = "plan"
    TASK = "task"


class ReviewDecision(str, Enum):
    APPROVED = "approved"
    REQUEST_CHANGES = "request_changes"


class ProcessingStatus(str, Enum):
    """Status of AI-powered content generation."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
