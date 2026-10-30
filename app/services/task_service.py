from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models import Task, User
from app.models.enums import ACTIVE_STATUSES, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.pagination import Page
from app.schemas.task import TaskCreate, TaskListParams, TaskRead, TaskUpdate

ALLOWED_TRANSITIONS = {
    TaskStatus.BACKLOG: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.REVIEW, TaskStatus.CANCELLED},
    TaskStatus.REVIEW: {TaskStatus.DONE},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}
MAX_ACTIVE_TASKS = 10

CLOSED_STATUSES = {TaskStatus.DONE, TaskStatus.CANCELLED}
ASSIGNEE_LOCKED_STATUSES = {TaskStatus.REVIEW, TaskStatus.DONE}
NOT_DELETABLE_STATUSES = {TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.task_repository = TaskRepository(session)
        self.user_repository = UserRepository(session)

    async def create_task(self, task_data: TaskCreate, author: User) -> Task:
        if task_data.assignee_id is not None:
            await self._check_user_exists(task_data.assignee_id)

        task = Task(**task_data.model_dump(), author_id=author.id)
        return await self.task_repository.add(task)

    async def get_tasks(self, params: TaskListParams) -> Page[TaskRead]:
        tasks = await self.task_repository.get_list(params)
        total = await self.task_repository.count(params)
        return Page[TaskRead].create(tasks, total, params.page, params.size)

    async def get_task(self, task_id: int) -> Task:
        task = await self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Task not found", "task_not_found")
        return task

    async def update_task(
        self, task_id: int, task_data: TaskUpdate, current_user: User
    ) -> Task:
        task = await self.get_task(task_id)
        self._check_is_author(task, current_user)

        if task.status in CLOSED_STATUSES:
            raise BusinessRuleError("Task is closed for editing", "task_closed")

        update_data = task_data.model_dump(exclude_unset=True)
        new_assignee_id = update_data.get("assignee_id", task.assignee_id)
        if new_assignee_id != task.assignee_id:
            await self._check_assignee_can_change(task, new_assignee_id)

        for field, value in update_data.items():
            setattr(task, field, value)
        return await self.task_repository.save(task)

    async def change_status(
        self, task_id: int, new_status: TaskStatus, current_user: User
    ) -> Task:
        task = await self.get_task(task_id)
        if current_user.id not in (task.author_id, task.assignee_id):
            raise ForbiddenError(
                "Only the author or assignee can change status",
                "not_author_or_assignee",
            )

        if new_status not in ALLOWED_TRANSITIONS[task.status]:
            raise BusinessRuleError(
                f"Cannot change status from {task.status} to {new_status}",
                "invalid_transition",
            )

        if new_status == TaskStatus.DONE:
            self._check_can_be_done(task)

        is_becoming_active = (
            new_status in ACTIVE_STATUSES and task.status not in ACTIVE_STATUSES
        )
        if is_becoming_active and task.assignee_id is not None:
            await self._check_active_tasks_limit(task.assignee_id)

        task.status = new_status
        return await self.task_repository.save(task)

    async def delete_task(self, task_id: int, current_user: User) -> None:
        task = await self.get_task(task_id)
        self._check_is_author(task, current_user)

        if task.status in NOT_DELETABLE_STATUSES:
            raise BusinessRuleError(
                "Task in progress or review cannot be deleted, "
                "move it to cancelled or done first",
                "task_not_deletable",
            )
        await self.task_repository.delete(task)

    async def _check_assignee_can_change(
        self, task: Task, assignee_id: int | None
    ) -> None:
        if task.status in ASSIGNEE_LOCKED_STATUSES:
            raise BusinessRuleError(
                "Assignee cannot be changed in review or done", "assignee_locked"
            )
        if assignee_id is None:
            return

        await self._check_user_exists(assignee_id)
        if task.status in ACTIVE_STATUSES:
            await self._check_active_tasks_limit(assignee_id)

    async def _check_active_tasks_limit(self, assignee_id: int) -> None:
        await self.user_repository.lock_by_id(assignee_id)
        active_count = await self.task_repository.count_active_by_assignee(assignee_id)
        if active_count >= MAX_ACTIVE_TASKS:
            raise BusinessRuleError(
                f"Assignee already has {MAX_ACTIVE_TASKS} active tasks",
                "active_tasks_limit",
            )

    def _check_can_be_done(self, task: Task) -> None:
        if task.assignee_id is None:
            raise BusinessRuleError(
                "Task without assignee cannot be done", "no_assignee"
            )
        if task.deadline is not None and task.deadline < datetime.now(UTC):
            raise BusinessRuleError(
                "Task with passed deadline cannot be done", "deadline_passed"
            )

    async def _check_user_exists(self, user_id: int) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Assignee not found", "assignee_not_found")

    def _check_is_author(self, task: Task, user: User) -> None:
        if task.author_id != user.id:
            raise ForbiddenError("Only the author can change this task", "not_author")
