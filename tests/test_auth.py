from httpx import AsyncClient


async def test_register(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "anna@example.com", "username": "anna", "password": "secret123"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "anna"
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


async def test_register_with_taken_email(client: AsyncClient, user: dict) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": user["email"], "username": "other", "password": "secret123"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_taken"


async def test_login(client: AsyncClient, user: dict) -> None:
    response = await client.post(
        "/auth/login", data={"username": "anna", "password": "secret123"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_with_wrong_password(client: AsyncClient, user: dict) -> None:
    response = await client.post(
        "/auth/login", data={"username": "anna", "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_request_without_token(client: AsyncClient) -> None:
    response = await client.get("/users/me")

    assert response.status_code == 401


async def test_get_current_user(
    client: AsyncClient, user: dict, auth_headers: dict
) -> None:
    response = await client.get("/users/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
