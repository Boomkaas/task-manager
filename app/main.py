import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, comments, tasks, users
from app.core.config import settings
from app.core.exceptions import AppError, handle_app_error
from app.workers.overdue import run_overdue_check_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not settings.overdue_check_enabled:
        yield
        return

    overdue_check_task = asyncio.create_task(
        run_overdue_check_loop(settings.overdue_check_interval_seconds)
    )
    yield
    overdue_check_task.cancel()


app = FastAPI(title="Task Management API", lifespan=lifespan)

app.add_exception_handler(AppError, handle_app_error)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(comments.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
