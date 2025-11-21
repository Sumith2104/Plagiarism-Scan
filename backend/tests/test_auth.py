from fastapi.testclient import TestClient
from app.core import auth

def test_register_user(client):
    response = client.post(
        "/api/v1/auth/register",
        params={"email": "test@example.com", "password": "password123", "full_name": "Test User"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_login_user(client):
    # Register first
    client.post(
        "/api/v1/auth/register",
        params={"email": "login@example.com", "password": "password123"}
    )
    
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_access_protected_route(client):
    # Register and Login
    client.post(
        "/api/v1/auth/register",
        params={"email": "protected@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "protected@example.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    
    # Access protected route (e.g., upload document)
    # We mock the file upload part, just checking auth
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/documents/", headers=headers)
    assert response.status_code == 200
