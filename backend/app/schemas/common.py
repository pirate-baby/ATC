from enum import Enum


class PlanTaskStatus(str, Enum):
    """Unified status enumeration for Plans and Tasks."""

    BACKLOG = "backlog"
    BLOCKED = "blocked"
    CODING = "coding"
    REVIEW = "review"
    APPROVED = "approved"
    CICD = "cicd"
    MERGED = "merged"
    CLOSED = "closed"
