def _register(client, email="alice@kairos.dev", org="Acme Corp"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Alice Analyst",
            "password": "supersecret123",
            "organization_name": org,
        },
    )


def test_register_creates_first_user_as_admin(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@kairos.dev"
    assert body["role"] == "admin"  # first user in a new org is Admin


def test_register_duplicate_email_rejected(client):
    _register(client)
    response = _register(client)
    assert response.status_code == 400


def test_second_user_in_org_is_viewer_by_default(client):
    _register(client, email="alice@kairos.dev")
    response = _register(client, email="bob@kairos.dev")
    assert response.status_code == 201
    assert response.json()["role"] == "viewer"


def test_login_and_access_protected_route(client):
    _register(client)
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@kairos.dev", "password": "supersecret123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@kairos.dev"


def test_login_wrong_password_rejected(client):
    _register(client)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@kairos.dev", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_protected_route_without_token_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    _register(client)
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@kairos.dev", "password": "supersecret123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


def test_access_token_rejected_at_refresh_endpoint(client):
    """An access token must not work where a refresh token is expected."""
    _register(client)
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@kairos.dev", "password": "supersecret123"},
    )
    access_token = login_response.json()["access_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": access_token}
    )
    assert refresh_response.status_code == 401
