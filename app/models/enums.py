from enum import StrEnum


class TaskStatus(StrEnum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ACTIVE_STATUSES = {TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}
CLOSED_STATUSES = {TaskStatus.DONE, TaskStatus.CANCELLED}
