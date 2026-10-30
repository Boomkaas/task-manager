from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import Comment, User
from app.repositories.comment_repository import CommentRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.pagination import Page


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.comment_repository = CommentRepository(session)
        self.task_repository = TaskRepository(session)

    async def create_comment(
        self, task_id: int, comment_data: CommentCreate, author: User
    ) -> Comment:
        await self._check_task_exists(task_id)

        comment = Comment(task_id=task_id, author_id=author.id, text=comment_data.text)
        return await self.comment_repository.add(comment)

    async def get_comments(
        self, task_id: int, page: int, size: int
    ) -> Page[CommentRead]:
        await self._check_task_exists(task_id)

        comments = await self.comment_repository.get_by_task(
            task_id, offset=(page - 1) * size, limit=size
        )
        total = await self.comment_repository.count_by_task(task_id)
        return Page[CommentRead].create(comments, total, page, size)

    async def _check_task_exists(self, task_id: int) -> None:
        task = await self.task_repository.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Task not found", "task_not_found")
