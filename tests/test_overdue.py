from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task
from app.workers.overdue import cancel_overdue_tasks
from tests.conftest import (
    DeadlineMover,
    StatusChanger,
    TaskFactory,
    get_future_deadline,
)


async def test_overdue_tasks(
    client: AsyncClient,
    auth_headers: dict,
    task_factory: TaskFactory,
    move_deadline_to_past: DeadlineMover,
) -> None:
    overdue_task = await task_factory(title="Late", deadline=get_future_deadline())
    await task_factory(title="On time", deadline=get_future_deadline())
    await move_deadline_to_past(overdue_task["id"])

    response = await client.get("/tasks/overdue", headers=auth_headers)

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["items"]] == ["Late"]


async def test_stats(
    client: AsyncClient,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
    move_deadline_to_past: DeadlineMover,
) -> None:
    overdue_task = await task_factory(priority="high", deadline=get_future_deadline())
    active_task = await task_factory()
    cancelled_task = await task_factory(priority="low")
    await move_deadline_to_past(overdue_task["id"])
    await change_status(active_task["id"], "in_progress")
    await change_status(cancelled_task["id"], "cancelled")

    response = await client.get("/tasks/stats", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "total": 3,
        "by_status": {
            "backlog": 1,
            "in_progress": 1,
            "review": 0,
            "done": 0,
            "cancelled": 1,
        },
        "by_priority": {"low": 1, "medium": 1, "high": 1},
        "overdue": 1,
        "active": 1,
    }


async def test_cancel_overdue_tasks(
    session: AsyncSession,
    user: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
    move_deadline_to_past: DeadlineMover,
) -> None:
    overdue_task = await task_factory(deadline=get_future_deadline())
    done_task = await task_factory(
        assignee_id=user["id"], deadline=get_future_deadline()
    )
    for status in ["in_progress", "review", "done"]:
        await change_status(done_task["id"], status)
    await move_deadline_to_past(overdue_task["id"])
    await move_deadline_to_past(done_task["id"])

    cancelled_count = await cancel_overdue_tasks(session)

    assert cancelled_count == 1
    assert (await session.get(Task, overdue_task["id"])).status == "cancelled"
    assert (await session.get(Task, done_task["id"])).status == "done"
