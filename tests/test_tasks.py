from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.conftest import StatusChanger, TaskFactory, get_future_deadline


async def test_create_task(client: AsyncClient, user: dict, auth_headers: dict) -> None:
    response = await client.post(
        "/tasks",
        json={
            "title": "Write README",
            "priority": "high",
            "assignee_id": user["id"],
            "deadline": get_future_deadline(),
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "backlog"
    assert task["priority"] == "high"
    assert task["author"]["id"] == user["id"]
    assert task["assignee"]["id"] == user["id"]


async def test_create_task_with_past_deadline(
    client: AsyncClient, auth_headers: dict
) -> None:
    past_deadline = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    response = await client.post(
        "/tasks",
        json={"title": "Old task", "deadline": past_deadline},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_update_task(
    client: AsyncClient, auth_headers: dict, task_factory: TaskFactory
) -> None:
    task = await task_factory()

    response = await client.patch(
        f"/tasks/{task['id']}", json={"title": "New title"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "New title"


async def test_update_task_by_not_author(
    client: AsyncClient, second_auth_headers: dict, task_factory: TaskFactory
) -> None:
    task = await task_factory()

    response = await client.patch(
        f"/tasks/{task['id']}", json={"title": "New title"}, headers=second_auth_headers
    )

    assert response.status_code == 403


async def test_update_done_task(
    client: AsyncClient,
    user: dict,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
) -> None:
    task = await task_factory(assignee_id=user["id"])
    for status in ["in_progress", "review", "done"]:
        await change_status(task["id"], status)

    response = await client.patch(
        f"/tasks/{task['id']}", json={"title": "New title"}, headers=auth_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "task_closed"


async def test_change_assignee_in_review(
    client: AsyncClient,
    user: dict,
    second_user: dict,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
) -> None:
    task = await task_factory(assignee_id=user["id"])
    for status in ["in_progress", "review"]:
        await change_status(task["id"], status)

    response = await client.patch(
        f"/tasks/{task['id']}",
        json={"assignee_id": second_user["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "assignee_locked"


async def test_delete_task_in_progress(
    client: AsyncClient,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
) -> None:
    task = await task_factory()
    await change_status(task["id"], "in_progress")

    response = await client.delete(f"/tasks/{task['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "task_not_deletable"


async def test_delete_cancelled_task(
    client: AsyncClient,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
) -> None:
    task = await task_factory()
    await change_status(task["id"], "cancelled")

    response = await client.delete(f"/tasks/{task['id']}", headers=auth_headers)

    assert response.status_code == 204
    response = await client.get(f"/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 404
