import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "first_name": "New",
            "last_name": "User"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "New"
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: dict):
    """Test that duplicate email registration fails."""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/register",
        json={
            "email": test_user["email"],
            "password": "password123",
            "first_name": "Duplicate",
            "last_name": "User"
        }
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    """Test successful login."""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user: dict):
    """Test login with wrong password."""
    response = await client.post(
        f"{settings.API_V1_PREFIX}/auth/login",
        data={
            "username": test_user["email"],
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_token: str):
    """Test getting current user info."""
    response = await client.get(
        f"{settings.API_V1_PREFIX}/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test that unauthorized requests are rejected."""
    response = await client.get(f"{settings.API_V1_PREFIX}/auth/me")

    assert response.status_code == 401
