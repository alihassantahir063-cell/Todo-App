from datetime import date, timedelta

from app.core.security import hash_password
from app.models.task import Task
from app.models.user import User, UserRole
from tests.conftest import register
from app.main import app


def create_task(client, title="Write tests", **fields):
    response = client.post("/api/tasks", json={"title": title, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def admin_token(client, session_factory, email="admin@example.com"):
    with session_factory() as db:
        user = User(
            name="Admin",
            email=email,
            hashed_password=hash_password("admin-pass123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
    response = client.post("/api/auth/login", json={"email": email, "password": "admin-pass123"})
    assert response.status_code == 200
    return response.json()["user"]


def test_register_normalizes_email_and_ignores_mass_assignment(client):
    test_client, _ = client
    response = test_client.post(
        "/api/auth/register",
        json={"name": "  Test User ", "email": "TEST@example.com", "password": "secure-pass123", "role": "admin", "is_active": False},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert response.json()["name"] == "Test User"
    assert response.json()["role"] == "user"
    assert response.json()["is_active"] is True
    assert "hashed_password" not in response.json()


def test_duplicate_email_and_weak_password(client):
    test_client, _ = client
    register(test_client, "Person", "same@example.com")
    duplicate = test_client.post("/api/auth/register", json={"name": "Other", "email": "SAME@example.com", "password": "secure-pass123"})
    weak = test_client.post("/api/auth/register", json={"name": "Weak", "email": "weak@example.com", "password": "onlyletters"})
    assert duplicate.status_code == 409
    assert weak.status_code == 422


def test_auth_rate_limit_returns_documented_error_shape(client):
    test_client, _ = client
    app.state.limiter.enabled = True
    try:
        responses = [
            test_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "bad-password1"})
            for _ in range(9)
        ]
    finally:
        app.state.limiter.enabled = False
    limited = next(response for response in responses if response.status_code == 429)
    assert limited.json()["detail"]


def test_login_success_wrong_password_and_inactive_user_blocked(client):
    test_client, session_factory = client
    user = register(test_client, "Login User", "login@example.com")
    valid = test_client.post("/api/auth/login", json={"email": user["email"], "password": "secure-pass123"})
    assert valid.status_code == 200
    assert valid.json()["user"]["id"] == user["id"]
    assert valid.headers["set-cookie"].startswith("access_token=")
    assert "httponly" in valid.headers["set-cookie"].lower()
    assert "hashed_password" not in valid.json()["user"]
    wrong = test_client.post("/api/auth/login", json={"email": user["email"], "password": "wrong-pass123"})
    assert wrong.status_code == 401
    with session_factory() as db:
        db.get(User, user["id"]).is_active = False
        db.commit()
    inactive = test_client.post("/api/auth/login", json={"email": user["email"], "password": "secure-pass123"})
    assert inactive.status_code == 401


def test_me_requires_auth_and_supports_cookie_and_bearer(client):
    test_client, _ = client
    missing = test_client.get("/api/auth/me")
    assert missing.status_code == 401
    user = register(test_client, "Me", "me@example.com")
    login_response = test_client.post("/api/auth/login", json={"email": user["email"], "password": "secure-pass123"})
    cookie_me = test_client.get("/api/auth/me")
    assert cookie_me.status_code == 200
    assert cookie_me.json()["id"] == user["id"]
    test_client.post("/api/auth/logout")
    bearer_me = test_client.get("/api/auth/me", headers={"Authorization": f"Bearer {login_response.cookies['access_token']}"})
    assert bearer_me.status_code == 200


def test_auth_profile_change_and_logout(client):
    test_client, _ = client
    register(test_client, "Profile", "profile@example.com")
    test_client.post("/api/auth/login", json={"email": "profile@example.com", "password": "secure-pass123"})
    updated = test_client.patch("/api/auth/me", json={"name": "New Name", "email": "NEW@example.com"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "New Name"
    assert updated.json()["email"] == "new@example.com"
    password = test_client.post(
        "/api/auth/change-password",
        json={"current_password": "secure-pass123", "new_password": "new-secure-pass456"},
    )
    assert password.status_code == 204
    logged_out = test_client.post("/api/auth/logout")
    assert logged_out.status_code == 204
    test_client.cookies.clear()
    assert test_client.post("/api/auth/login", json={"email": "new@example.com", "password": "secure-pass123"}).status_code == 401
    assert test_client.post("/api/auth/login", json={"email": "new@example.com", "password": "new-secure-pass456"}).status_code == 200


def test_admin_can_change_password_from_authenticated_account(client):
    test_client, _ = client
    admin_token(test_client, _)
    changed = test_client.post(
        "/api/auth/change-password",
        json={"current_password": "admin-pass123", "new_password": "admin-new-pass456"},
    )
    assert changed.status_code == 204

    test_client.post("/api/auth/logout")
    test_client.cookies.clear()
    assert test_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-pass123"},
    ).status_code == 401
    assert test_client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "admin-new-pass456"},
    ).status_code == 200


def test_task_crud_toggle_stats_search_filter_sort_and_pagination(client):
    test_client, _ = client
    register(test_client, "Task Owner", "tasks@example.com")
    test_client.post("/api/auth/login", json={"email": "tasks@example.com", "password": "secure-pass123"})
    one = create_task(test_client, "Alpha plan", priority="high", due_date=(date.today() - timedelta(days=1)).isoformat())
    create_task(test_client, "Beta note", priority="low")
    result = test_client.get("/api/tasks", params={"search": "alpha", "status": "pending", "sort_by": "created_at", "order": "desc", "page": 1, "page_size": 1})
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["title"] == "Alpha plan"
    assert result.json()["pages"] == 1
    low = test_client.get("/api/tasks", params={"priority": "low"})
    assert low.json()["total"] == 1
    first_page = test_client.get("/api/tasks", params={"sort_by": "priority", "order": "asc", "page": 1, "page_size": 1}).json()
    second_page = test_client.get("/api/tasks", params={"sort_by": "priority", "order": "asc", "page": 2, "page_size": 1}).json()
    assert first_page["total"] == 2
    assert first_page["pages"] == 2
    assert first_page["items"][0]["priority"] == "low"
    assert second_page["items"][0]["priority"] == "high"
    toggled = test_client.patch(f"/api/tasks/{one['id']}/toggle")
    assert toggled.json()["status"] == "completed"
    assert toggled.json()["completed_at"] is not None
    reopened = test_client.patch(f"/api/tasks/{one['id']}/toggle")
    assert reopened.json()["status"] == "pending"
    assert reopened.json()["completed_at"] is None
    stats = test_client.get("/api/tasks/stats").json()
    assert stats == {"total": 2, "pending": 2, "completed": 0, "overdue": 1, "completion_percentage": 0.0}
    updated = test_client.patch(f"/api/tasks/{one['id']}", json={"title": "  Revised plan ", "description": "Updated"})
    assert updated.json()["title"] == "Revised plan"
    assert test_client.patch(f"/api/tasks/{one['id']}", json={"title": None}).status_code == 422
    assert test_client.get(f"/api/tasks/{one['id']}").status_code == 200
    assert test_client.delete(f"/api/tasks/{one['id']}").status_code == 204
    assert test_client.get(f"/api/tasks/{one['id']}").status_code == 404


def test_task_ownership_hides_another_users_task_for_all_mutations(client):
    test_client, _ = client
    register(test_client, "Owner A", "owner-a@example.com")
    test_client.post("/api/auth/login", json={"email": "owner-a@example.com", "password": "secure-pass123"})
    task = create_task(test_client, "Private task")
    test_client.post("/api/auth/logout")
    register(test_client, "Owner B", "owner-b@example.com")
    test_client.post("/api/auth/login", json={"email": "owner-b@example.com", "password": "secure-pass123"})
    task_id = task["id"]
    assert test_client.get(f"/api/tasks/{task_id}").status_code == 404
    assert test_client.patch(f"/api/tasks/{task_id}", json={"title": "Stolen"}).status_code == 404
    assert test_client.patch(f"/api/tasks/{task_id}/toggle").status_code == 404
    assert test_client.delete(f"/api/tasks/{task_id}").status_code == 404


def test_admin_routes_require_auth_and_admin_and_dashboard_data_is_real(client):
    test_client, session_factory = client
    assert test_client.get("/api/admin/dashboard").status_code == 401
    register(test_client, "Regular", "regular@example.com")
    test_client.post("/api/auth/login", json={"email": "regular@example.com", "password": "secure-pass123"})
    assert test_client.get("/api/admin/dashboard").status_code == 403
    test_client.post("/api/auth/logout")
    admin_token(test_client, session_factory)
    test_client.post("/api/auth/logout")
    register(test_client, "Dashboard User", "dashboard@example.com")
    test_client.post("/api/auth/login", json={"email": "dashboard@example.com", "password": "secure-pass123"})
    create_task(test_client, "Dashboard pending")
    test_client.post("/api/auth/logout")
    admin_token(test_client, session_factory, email="admin2@example.com")
    dashboard = test_client.get("/api/admin/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["total_users"] == 4
    assert dashboard.json()["active_users"] == 4
    assert dashboard.json()["total_tasks"] == 1
    assert dashboard.json()["pending_tasks"] == 1
    assert dashboard.json()["recent_tasks"][0]["title"] == "Dashboard pending"


def test_admin_can_deactivate_user_then_user_is_blocked_and_delete_task(client):
    test_client, session_factory = client
    register(test_client, "To Disable", "disable@example.com")
    user_id = test_client.post("/api/auth/login", json={"email": "disable@example.com", "password": "secure-pass123"}).json()["user"]["id"]
    task = create_task(test_client, "Remove via admin")
    test_client.post("/api/auth/logout")
    admin_token(test_client, session_factory)
    deactivated = test_client.patch(f"/api/admin/users/{user_id}/status", json={"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert test_client.post("/api/auth/logout").status_code == 204
    assert test_client.post("/api/auth/login", json={"email": "disable@example.com", "password": "secure-pass123"}).status_code == 401
    assert test_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin-pass123"}).status_code == 200
    assert test_client.delete(f"/api/admin/tasks/{task['id']}").status_code == 204
    assert test_client.get(f"/api/admin/tasks?user_id={user_id}").json()["total"] == 0


def test_profile_email_duplicate_and_admin_self_deactivation_rejected(client):
    test_client, session_factory = client
    register(test_client, "First", "first@example.com")
    register(test_client, "Second", "second@example.com")
    test_client.post("/api/auth/login", json={"email": "first@example.com", "password": "secure-pass123"})
    conflict = test_client.patch("/api/auth/me", json={"email": "second@example.com"})
    assert conflict.status_code == 409
    assert test_client.patch("/api/auth/me", json={"name": None}).status_code == 422
    test_client.post("/api/auth/logout")
    admin_token(test_client, session_factory)
    current = test_client.get("/api/auth/me").json()
    self_deactivate = test_client.patch(f"/api/admin/users/{current['id']}/status", json={"is_active": False})
    assert self_deactivate.status_code == 400


def test_user_delete_cascades_tasks(client):
    test_client, session_factory = client
    user = register(test_client, "Cascade", "cascade@example.com")
    test_client.post("/api/auth/login", json={"email": "cascade@example.com", "password": "secure-pass123"})
    task = create_task(test_client, "Child task")
    test_client.post("/api/auth/logout")
    with session_factory() as db:
        db.delete(db.get(User, user["id"]))
        db.commit()
        assert db.get(Task, task["id"]) is None
