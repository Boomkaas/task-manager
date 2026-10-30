from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import get_future_deadline

pytestmark = pytest.mark.e2e


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_request_without_token(client: AsyncClient) -> None:
    response = await client.get("/tasks")

    assert response.status_code == 401


async def test_task_goes_from_backlog_to_done(
    client: AsyncClient,
    assignee: dict,
    author_headers: dict[str, str],
    assignee_headers: dict[str, str],
) -> None:
    title = f"Release {uuid4().hex[:8]}"
    response = await client.post(
        "/tasks",
        json={
            "title": title,
            "priority": "high",
            "assignee_id": assignee["id"],
            "deadline": get_future_deadline(),
        },
        headers=author_headers,
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    response = await client.get(
        "/tasks", params={"search": title}, headers=assignee_headers
    )
    assert [task["id"] for task in response.json()["items"]] == [task_id]

    for status in ["in_progress", "review", "done"]:
        response = await client.patch(
            f"/tasks/{task_id}/status",
            json={"status": status},
            headers=assignee_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == status

    response = await client.patch(
        f"/tasks/{task_id}", json={"title": "Too late"}, headers=author_headers
    )
    assert response.status_code == 409
    assert response.json()["code"] == "task_closed"


async def test_comment_on_task(
    client: AsyncClient,
    assignee: dict,
    author_headers: dict[str, str],
    assignee_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/tasks", json={"title": "Review code"}, headers=author_headers
    )
    task_id = response.json()["id"]

    response = await client.post(
        f"/tasks/{task_id}/comments",
        json={"text": "Please add tests"},
        headers=assignee_headers,
    )
    assert response.status_code == 201

    response = await client.get(f"/tasks/{task_id}/comments", headers=author_headers)
    assert response.status_code == 200
    comments = response.json()["items"]
    assert [comment["text"] for comment in comments] == ["Please add tests"]
    assert comments[0]["author"]["id"] == assignee["id"]


async def test_cancel_and_delete_task(
    client: AsyncClient, author_headers: dict[str, str]
) -> None:
    response = await client.post(
        "/tasks", json={"title": "Old idea"}, headers=author_headers
    )
    task_id = response.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}/status",
        json={"status": "cancelled"},
        headers=author_headers,
    )
    assert response.status_code == 200

    response = await client.delete(f"/tasks/{task_id}", headers=author_headers)
    assert response.status_code == 204

    response = await client.get(f"/tasks/{task_id}", headers=author_headers)
    assert response.status_code == 404


async def test_get_stats(client: AsyncClient, author_headers: dict[str, str]) -> None:
    await client.post("/tasks", json={"title": "Count me"}, headers=author_headers)

    response = await client.get("/tasks/stats", headers=author_headers)

    assert response.status_code == 200
    stats = response.json()
    assert stats["total"] >= 1
    assert stats["by_status"]["backlog"] >= 1
