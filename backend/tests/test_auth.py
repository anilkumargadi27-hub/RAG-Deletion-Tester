import pytest
from backend.app.core.security import hash_password, verify_password

def test_password_hashing():
    raw = "SecureP@ssw0rd2026!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

def test_login_flow(client, admin_user):
    resp = client.post("/api/auth/login", json={
        "username": "admin_test",
        "password": "AdminPass123!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == "admin_test"
    assert data["user"]["role"] == "admin"
    assert "forgetcheck_session" in resp.cookies
    assert "forgetcheck_csrf" in resp.cookies

def test_login_invalid_credentials(client):
    resp = client.post("/api/auth/login", json={
        "username": "non_existent_user",
        "password": "BadPassword123!"
    })
    assert resp.status_code == 401

def test_current_user_me(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin_test"

def test_role_restriction(client, member_auth_headers):
    # Member should be denied access to admin-only user creation
    resp = client.post("/api/auth/users", json={
        "username": "new_auditor",
        "email": "auditor@test.local",
        "password": "TestPass123!",
        "role": "auditor"
    }, headers=member_auth_headers)
    assert resp.status_code == 403

def test_admin_user_creation(client, auth_headers):
    resp = client.post("/api/auth/users", json={
        "username": "test_auditor_user",
        "email": "test_auditor@example.com",
        "password": "TestPass123!",
        "role": "auditor"
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "auditor"
