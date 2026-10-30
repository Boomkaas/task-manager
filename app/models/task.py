from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User


def get_enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=get_enum_values),
        default=TaskStatus.BACKLOG,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", values_callable=get_enum_values),
        default=TaskPriority.MEDIUM,
        index=True,
    )
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )

    author: Mapped[User] = relationship(foreign_keys=[author_id], lazy="selectin")
    assignee: Mapped[User | None] = relationship(
        foreign_keys=[assignee_id], lazy="selectin"
    )
