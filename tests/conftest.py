import os
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import get_session
from app.main import app
from app.models import Base, Task

TaskFactory = Callable[..., Awaitable[dict]]
StatusChanger = Callable[[int, str], Awaitable[Response]]
DeadlineMover = Callable[[int], Awaitable[None]]

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/task_manager_test",
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def get_test_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def register_user(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "secret123",
        },
    )
    assert response.status_code == 201
    return response.json()


async def login_user(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/auth/login", data={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def user(client: AsyncClient) -> dict:
    return await register_user(client, "anna")


@pytest.fixture
async def auth_headers(client: AsyncClient, user: dict) -> dict[str, str]:
    return await login_user(client, "anna")


@pytest.fixture
async def second_user(client: AsyncClient) -> dict:
    return await register_user(client, "bob")


@pytest.fixture
async def second_auth_headers(client: AsyncClient, second_user: dict) -> dict[str, str]:
    return await login_user(client, "bob")


@pytest.fixture
def task_factory(client: AsyncClient, auth_headers: dict[str, str]) -> TaskFactory:
    async def create_task(**fields: object) -> dict:
        response = await client.post(
            "/tasks", json={"title": "Test task", **fields}, headers=auth_headers
        )
        assert response.status_code == 201
        return response.json()

    return create_task


@pytest.fixture
def change_status(client: AsyncClient, auth_headers: dict[str, str]) -> StatusChanger:
    async def send_status(task_id: int, status: str) -> Response:
        return await client.patch(
            f"/tasks/{task_id}/status", json={"status": status}, headers=auth_headers
        )

    return send_status


@pytest.fixture
def move_deadline_to_past(
    session: AsyncSession,
) -> DeadlineMover:
    async def update_deadline(task_id: int) -> None:
        past_deadline = datetime.now(UTC) - timedelta(days=1)
        await session.execute(
            update(Task).where(Task.id == task_id).values(deadline=past_deadline)
        )
        await session.commit()

    return update_deadline


def get_future_deadline() -> str:
    return (datetime.now(UTC) + timedelta(days=3)).isoformat()
