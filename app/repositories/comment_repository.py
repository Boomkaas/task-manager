from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_task(self, task_id: int, offset: int, limit: int) -> list[Comment]:
        comments = await self.session.scalars(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at, Comment.id)
            .offset(offset)
            .limit(limit)
        )
        return list(comments)

    async def count_by_task(self, task_id: int) -> int:
        return await self.session.scalar(
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )

    async def add(self, comment: Comment) -> Comment:
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment
