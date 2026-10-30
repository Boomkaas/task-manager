from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.user import UserRead


def check_deadline_in_future(deadline: datetime | None) -> datetime | None:
    if deadline is None:
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    if deadline <= datetime.now(UTC):
        raise ValueError("Deadline must be in the future")
    return deadline


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: int | None = None
    deadline: datetime | None = None

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, deadline: datetime | None) -> datetime | None:
        return check_deadline_in_future(deadline)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority | None = None
    assignee_id: int | None = None
    deadline: datetime | None = None

    @field_validator("title", "description", "priority")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, deadline: datetime | None) -> datetime | None:
        return check_deadline_in_future(deadline)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    deadline: datetime | None
    author: UserRead
    assignee: UserRead | None
    created_at: datetime
    updated_at: datetime
