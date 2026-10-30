from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.models import Task
from app.schemas.error import get_error_responses
from app.schemas.pagination import Page
from app.schemas.stats import StatsRead
from app.schemas.task import (
    TaskCreate,
    TaskListParams,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    responses=get_error_responses(404),
)
async def create_task(
    task_data: TaskCreate, session: DbSession, current_user: CurrentUser
) -> Task:
    return await TaskService(session).create_task(task_data, current_user)


@router.get(
    "",
    dependencies=[Depends(get_current_user)],
    description="Default sorting: priority from high to low, then nearest deadline.",
)
async def get_tasks(
    params: Annotated[TaskListParams, Query()], session: DbSession
) -> Page[TaskRead]:
    return await TaskService(session).get_tasks(params)


@router.get(
    "/overdue",
    dependencies=[Depends(get_current_user)],
    description="Tasks with passed deadline that are not done or cancelled.",
)
async def get_overdue_tasks(
    session: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Page[TaskRead]:
    return await TaskService(session).get_overdue_tasks(page, size)


@router.get("/stats", dependencies=[Depends(get_current_user)])
async def get_stats(session: DbSession) -> StatsRead:
    return await TaskService(session).get_stats()


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    dependencies=[Depends(get_current_user)],
    responses=get_error_responses(404),
)
async def get_task(task_id: int, session: DbSession) -> Task:
    return await TaskService(session).get_task(task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    responses=get_error_responses(403, 404, 409),
    description="Only the author can edit. Done and cancelled tasks are closed.",
)
async def update_task(
    task_id: int, task_data: TaskUpdate, session: DbSession, current_user: CurrentUser
) -> Task:
    return await TaskService(session).update_task(task_id, task_data, current_user)


@router.patch(
    "/{task_id}/status",
    response_model=TaskRead,
    responses=get_error_responses(403, 404, 409),
    description=(
        "Allowed: backlog -> in_progress, backlog -> cancelled, "
        "in_progress -> review, in_progress -> cancelled, review -> done."
    ),
)
async def change_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    session: DbSession,
    current_user: CurrentUser,
) -> Task:
    return await TaskService(session).change_status(
        task_id, status_data.status, current_user
    )


@router.delete(
    "/{task_id}",
    status_code=204,
    responses=get_error_responses(403, 404, 409),
    description="Tasks in progress or review cannot be deleted.",
)
async def delete_task(
    task_id: int, session: DbSession, current_user: CurrentUser
) -> None:
    await TaskService(session).delete_task(task_id, current_user)
