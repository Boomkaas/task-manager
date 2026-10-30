from pydantic import BaseModel

from app.models.enums import TaskPriority, TaskStatus


class StatsRead(BaseModel):
    total: int
    by_status: dict[TaskStatus, int]
    by_priority: dict[TaskPriority, int]
    overdue: int
    active: int
