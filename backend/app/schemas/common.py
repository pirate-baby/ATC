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
