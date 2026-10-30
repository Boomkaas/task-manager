from httpx import AsyncClient

from tests.conftest import StatusChanger, TaskFactory


async def test_filter_by_status(
    client: AsyncClient,
    auth_headers: dict,
    task_factory: TaskFactory,
    change_status: StatusChanger,
) -> None:
    task = await task_factory(title="Started")
    await task_factory(title="Not started")
    await change_status(task["id"], "in_progress")

    response = await client.get(
        "/tasks", params={"status": "in_progress"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert [task["title"] for task in response.json()["items"]] == ["Started"]


async def test_search_in_title_and_description(
    client: AsyncClient, auth_headers: dict, task_factory: TaskFactory
) -> None:
    await task_factory(title="Login page")
    await task_factory(title="Bug", description="Fix the login form")
    await task_factory(title="Other")

    response = await client.get(
        "/tasks", params={"search": "LOGIN"}, headers=auth_headers
    )

    titles = {task["title"] for task in response.json()["items"]}
    assert titles == {"Login page", "Bug"}


async def test_default_sorting_by_priority(
    client: AsyncClient, auth_headers: dict, task_factory: TaskFactory
) -> None:
    await task_factory(title="Low", priority="low")
    await task_factory(title="High", priority="high")
    await task_factory(title="Medium", priority="medium")

    response = await client.get("/tasks", headers=auth_headers)

    titles = [task["title"] for task in response.json()["items"]]
    assert titles == ["High", "Medium", "Low"]


async def test_pagination(
    client: AsyncClient, auth_headers: dict, task_factory: TaskFactory
) -> None:
    for number in range(3):
        await task_factory(title=f"Task {number}")

    response = await client.get(
        "/tasks", params={"page": 2, "size": 2}, headers=auth_headers
    )

    page = response.json()
    assert len(page["items"]) == 1
    assert page["total"] == 3
    assert page["pages"] == 2
