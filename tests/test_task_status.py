from httpx import AsyncClient

from tests.conftest import (
    DeadlineMover,
    StatusChanger,
    TaskFactory,
    get_future_deadline,
)


async def test_full_status_flow(
    user: dict, task_factory: TaskFactory, change_status: StatusChanger
) -> None:
    task = await task_factory(assignee_id=user["id"])

    for status in ["in_progress", "review", "done"]:
        response = await change_status(task["id"], status)
        assert response.status_code == 200
        assert response.json()["status"] == status


async def test_return_to_previous_status(
    task_factory: TaskFactory, change_status: StatusChanger
) -> None:
    task = await task_factory()
    await change_status(task["id"], "in_progress")

    response = await change_status(task["id"], "backlog")

    assert response.status_code == 409
    assert response.json()["code"] == "invalid_transition"


async def test_done_without_assignee(
    task_factory: TaskFactory, change_status: StatusChanger
) -> None:
    task = await task_factory()
    for status in ["in_progress", "review"]:
        await change_status(task["id"], status)

    response = await change_status(task["id"], "done")

    assert response.status_code == 409
    assert response.json()["code"] == "no_assignee"


async def test_done_with_passed_deadline(
    user: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
    move_deadline_to_past: DeadlineMover,
) -> None:
    task = await task_factory(assignee_id=user["id"], deadline=get_future_deadline())
    for status in ["in_progress", "review"]:
        await change_status(task["id"], status)
    await move_deadline_to_past(task["id"])

    response = await change_status(task["id"], "done")

    assert response.status_code == 409
    assert response.json()["code"] == "deadline_passed"


async def test_status_change_by_other_user(
    client: AsyncClient, second_auth_headers: dict, task_factory: TaskFactory
) -> None:
    task = await task_factory()

    response = await client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "in_progress"},
        headers=second_auth_headers,
    )

    assert response.status_code == 403


async def test_active_tasks_limit(
    second_user: dict, task_factory: TaskFactory, change_status: StatusChanger
) -> None:
    tasks = [await task_factory(assignee_id=second_user["id"]) for _ in range(11)]
    for task in tasks[:10]:
        response = await change_status(task["id"], "in_progress")
        assert response.status_code == 200

    response = await change_status(tasks[10]["id"], "in_progress")

    assert response.status_code == 409
    assert response.json()["code"] == "active_tasks_limit"
