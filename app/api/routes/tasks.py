from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, get_current_user
from app.models import Task
from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(
    task_data: TaskCreate, session: DbSession, current_user: CurrentUser
) -> Task:
    return await TaskService(session).create_task(task_data, current_user)


@router.get(
    "/{task_id}", response_model=TaskRead, dependencies=[Depends(get_current_user)]
)
async def get_task(task_id: int, session: DbSession) -> Task:
    return await TaskService(session).get_task(task_id)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int, task_data: TaskUpdate, session: DbSession, current_user: CurrentUser
) -> Task:
    return await TaskService(session).update_task(task_id, task_data, current_user)


@router.patch("/{task_id}/status", response_model=TaskRead)
async def change_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    session: DbSession,
    current_user: CurrentUser,
) -> Task:
    return await TaskService(session).change_status(
        task_id, status_data.status, current_user
    )


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int, session: DbSession, current_user: CurrentUser
) -> None:
    await TaskService(session).delete_task(task_id, current_user)
