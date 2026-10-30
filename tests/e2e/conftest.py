import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import login_user, register_user

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(base_url=E2E_BASE_URL) as client:
        yield client


@pytest.fixture
async def author(client: AsyncClient) -> dict:
    return await register_user(client, f"author_{uuid4().hex[:8]}")


@pytest.fixture
async def author_headers(client: AsyncClient, author: dict) -> dict[str, str]:
    return await login_user(client, author["username"])


@pytest.fixture
async def assignee(client: AsyncClient) -> dict:
    return await register_user(client, f"assignee_{uuid4().hex[:8]}")


@pytest.fixture
async def assignee_headers(client: AsyncClient, assignee: dict) -> dict[str, str]:
    return await login_user(client, assignee["username"])
