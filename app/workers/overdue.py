import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import session_factory
from app.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


async def cancel_overdue_tasks(session: AsyncSession) -> int:
    return await TaskRepository(session).cancel_overdue()


async def run_overdue_check_loop(interval_seconds: int) -> None:
    while True:
        try:
            async with session_factory() as session:
                cancelled_count = await cancel_overdue_tasks(session)
            if cancelled_count:
                logger.info("Cancelled %s overdue tasks", cancelled_count)
        except Exception:
            logger.exception("Overdue tasks check failed")
        await asyncio.sleep(interval_seconds)
