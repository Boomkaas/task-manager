from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models import Task, User
from app.models.enums import TaskStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task import TaskCreate, TaskUpdate

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
        if assignee_id is not None:
            await self._check_user_exists(assignee_id)

    async def _check_user_exists(self, user_id: int) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Assignee not found", "assignee_not_found")

    def _check_is_author(self, task: Task, user: User) -> None:
        if task.author_id != user.id:
            raise ForbiddenError("Only the author can change this task", "not_author")
