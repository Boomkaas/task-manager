from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.models.enums import ACTIVE_STATUSES, CLOSED_STATUSES, TaskPriority, TaskStatus
from app.schemas.task import SortOrder, TaskListParams, TaskSortField

PRIORITY_RANK = case(
    (Task.priority == TaskPriority.HIGH, 3),
    (Task.priority == TaskPriority.MEDIUM, 2),
    else_=1,
)

SORT_COLUMNS = {
    TaskSortField.CREATED_AT: Task.created_at,
    TaskSortField.DEADLINE: Task.deadline,
    TaskSortField.PRIORITY: PRIORITY_RANK,
}


def overdue_condition() -> ColumnElement[bool]:
    return and_(Task.deadline < func.now(), Task.status.not_in(CLOSED_STATUSES))


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def get_list(self, params: TaskListParams) -> list[Task]:
        query = (
            self._apply_filters(select(Task), params)
            .order_by(*self._get_ordering(params))
            .offset((params.page - 1) * params.size)
            .limit(params.size)
        )
        tasks = await self.session.scalars(query)
        return list(tasks)

    async def count(self, params: TaskListParams) -> int:
        query = self._apply_filters(select(func.count()).select_from(Task), params)
        return await self.session.scalar(query)

    async def get_overdue(self, offset: int, limit: int) -> list[Task]:
        tasks = await self.session.scalars(
            select(Task)
            .where(overdue_condition())
            .order_by(Task.deadline, Task.id)
            .offset(offset)
            .limit(limit)
        )
        return list(tasks)

    async def count_all(self) -> int:
        return await self._count()

    async def count_overdue(self) -> int:
        return await self._count(overdue_condition())

    async def count_active(self) -> int:
        return await self._count(Task.status.in_(ACTIVE_STATUSES))

    async def count_active_by_assignee(self, assignee_id: int) -> int:
        return await self._count(
            Task.assignee_id == assignee_id, Task.status.in_(ACTIVE_STATUSES)
        )

    async def count_by_status(self) -> dict[TaskStatus, int]:
        rows = await self.session.execute(
            select(Task.status, func.count()).group_by(Task.status)
        )
        return dict(rows.tuples().all())

    async def count_by_priority(self) -> dict[TaskPriority, int]:
        rows = await self.session.execute(
            select(Task.priority, func.count()).group_by(Task.priority)
        )
        return dict(rows.tuples().all())

    async def add(self, task: Task) -> Task:
        self.session.add(task)
        return await self.save(task)

    async def save(self, task: Task) -> Task:
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def cancel_overdue(self) -> int:
        result = await self.session.execute(
            update(Task).where(overdue_condition()).values(status=TaskStatus.CANCELLED)
        )
        await self.session.commit()
        return result.rowcount

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.commit()

    async def _count(self, *conditions: ColumnElement[bool]) -> int:
        query = select(func.count()).select_from(Task).where(*conditions)
        return await self.session.scalar(query)

    def _apply_filters(self, query: Select, params: TaskListParams) -> Select:
        if params.search:
            pattern = f"%{params.search}%"
            query = query.where(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )
        if params.status:
            query = query.where(Task.status.in_(params.status))
        if params.priority:
            query = query.where(Task.priority.in_(params.priority))
        if params.assignee_id:
            query = query.where(Task.assignee_id.in_(params.assignee_id))
        if params.deadline_from:
            query = query.where(Task.deadline >= params.deadline_from)
        if params.deadline_to:
            query = query.where(Task.deadline <= params.deadline_to)
        return query

    def _get_ordering(self, params: TaskListParams) -> list[ColumnElement]:
        if params.sort_by is None:
            return [PRIORITY_RANK.desc(), Task.deadline.asc().nulls_last(), Task.id]

        column = SORT_COLUMNS[params.sort_by]
        if params.order == SortOrder.DESC:
            return [column.desc().nulls_last(), Task.id]
        return [column.asc().nulls_last(), Task.id]
