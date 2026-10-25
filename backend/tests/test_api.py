import hashlib
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import select

from app.core.security import hash_password
from app.models.password_reset import PasswordResetToken
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


def test_forgot_and_reset_password_works_for_user_and_admin(client, monkeypatch):
    import app.api.auth as auth_api

    test_client, session_factory = client
    sent_emails = []
    monkeypatch.setattr(auth_api, "smtp_is_configured", lambda: True)
    monkeypatch.setattr(auth_api, "send_password_reset_email", lambda email, url: sent_emails.append((email, url)))

    register(test_client, "Regular", "reset-user@example.com")
    admin_token(test_client, session_factory, email="reset-admin@example.com")

    for email, previous_password in (
        ("reset-user@example.com", "secure-pass123"),
        ("reset-admin@example.com", "admin-pass123"),
    ):
        response = test_client.post("/api/auth/forgot-password", json={"email": email})
        assert response.status_code == 200
        assert response.json()["message"] == auth_api.PASSWORD_RESET_MESSAGE
        sent_email, reset_url = sent_emails[-1]
        assert sent_email == email

        token = parse_qs(urlsplit(reset_url).fragment)["token"][0]
        with session_factory() as db:
            user_id = db.scalar(select(User.id).where(User.email == email))
            saved_token = db.get(
                PasswordResetToken,
                db.scalar(
                    select(PasswordResetToken.token_hash).where(PasswordResetToken.user_id == user_id)
                ),
            )
            assert saved_token is not None
            assert token not in saved_token.token_hash

        reset = test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "reset-new-pass456"},
        )
        assert reset.status_code == 204
        assert test_client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "reset-again-pass789"},
        ).status_code == 400
        assert test_client.post(
            "/api/auth/login",
            json={"email": email, "password": previous_password},
        ).status_code == 401
        assert test_client.post(
            "/api/auth/login",
            json={"email": email, "password": "reset-new-pass456"},
        ).status_code == 200
        test_client.post("/api/auth/logout")


def test_password_reset_request_does_not_disclose_unknown_accounts(client, monkeypatch):
    import app.api.auth as auth_api

    test_client, _ = client
    sent_emails = []
    monkeypatch.setattr(auth_api, "smtp_is_configured", lambda: True)
    monkeypatch.setattr(auth_api, "send_password_reset_email", lambda email, url: sent_emails.append(email))

    register(test_client, "Known", "known-reset@example.com")
    known = test_client.post("/api/auth/forgot-password", json={"email": "known-reset@example.com"})
    unknown = test_client.post("/api/auth/forgot-password", json={"email": "unknown-reset@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert sent_emails == ["known-reset@example.com"]


def test_password_reset_email_delivery_failure_keeps_generic_response(client, monkeypatch):
    import app.api.auth as auth_api

    test_client, _ = client
    monkeypatch.setattr(auth_api, "smtp_is_configured", lambda: True)

    def fail_delivery(email, url):
        raise OSError("SMTP unavailable")

    monkeypatch.setattr(auth_api, "send_password_reset_email", fail_delivery)
    register(test_client, "Known", "delivery-failure@example.com")

    known = test_client.post("/api/auth/forgot-password", json={"email": "delivery-failure@example.com"})
    unknown = test_client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_password_reset_requires_configured_smtp(client, monkeypatch):
    import app.api.auth as auth_api

    test_client, _ = client
    monkeypatch.setattr(auth_api, "smtp_is_configured", lambda: False)
    response = test_client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
    assert response.status_code == 503


def test_password_reset_rejects_invalid_token_and_weak_password(client):
    test_client, _ = client
    invalid = test_client.post(
        "/api/auth/reset-password",
        json={"token": "x" * 32, "new_password": "valid-pass123"},
    )
    weak = test_client.post(
        "/api/auth/reset-password",
        json={"token": "x" * 32, "new_password": "onlyletters"},
    )
    assert invalid.status_code == 400
    assert weak.status_code == 422


def test_recovery_code_resets_password_for_users_and_admins_once(client):
    test_client, session_factory = client
    user = register(test_client, "Recovery User", "recovery-user@example.com")
    admin_token(test_client, session_factory, email="recovery-admin@example.com")

    for email, old_password in (
        (user["email"], "secure-pass123"),
        ("recovery-admin@example.com", "admin-pass123"),
    ):
        login_response = test_client.post("/api/auth/login", json={"email": email, "password": old_password})
        assert login_response.status_code == 200
        rejected = test_client.post("/api/auth/recovery-code", json={"current_password": "incorrect-pass123"})
        assert rejected.status_code == 400

        created = test_client.post("/api/auth/recovery-code", json={"current_password": old_password})
        assert created.status_code == 200
        recovery_code = created.json()["recovery_code"]
        with session_factory() as db:
            account = db.scalar(select(User).where(User.email == email))
            assert account.recovery_code_hash == hashlib.sha256(recovery_code.encode()).hexdigest()
            assert recovery_code not in account.recovery_code_hash

        test_client.post("/api/auth/logout")
        reset = test_client.post(
            "/api/auth/reset-with-recovery-code",
            json={
                "email": email,
                "recovery_code": recovery_code,
                "new_password": "recovered-pass456",
            },
        )
        assert reset.status_code == 204
        reused = test_client.post(
            "/api/auth/reset-with-recovery-code",
            json={
                "email": email,
                "recovery_code": recovery_code,
                "new_password": "recovered-again789",
            },
        )
        assert reused.status_code == 400
        assert test_client.post("/api/auth/login", json={"email": email, "password": old_password}).status_code == 401
        assert test_client.post(
            "/api/auth/login",
            json={"email": email, "password": "recovered-pass456"},
        ).status_code == 200
        test_client.post("/api/auth/logout")


def test_recovery_code_rotation_invalidates_previous_code(client):
    test_client, _ = client
    user = register(test_client, "Recovery Rotation", "rotation@example.com")
    test_client.post("/api/auth/login", json={"email": user["email"], "password": "secure-pass123"})

    first_code = test_client.post(
        "/api/auth/recovery-code",
        json={"current_password": "secure-pass123"},
    ).json()["recovery_code"]
    second_code = test_client.post(
        "/api/auth/recovery-code",
        json={"current_password": "secure-pass123"},
    ).json()["recovery_code"]

    old_code_response = test_client.post(
        "/api/auth/reset-with-recovery-code",
        json={"email": user["email"], "recovery_code": first_code, "new_password": "rotated-pass456"},
    )
    assert old_code_response.status_code == 400

    test_client.post("/api/auth/logout")
    current_code_response = test_client.post(
        "/api/auth/reset-with-recovery-code",
        json={"email": user["email"], "recovery_code": second_code, "new_password": "rotated-pass456"},
    )
    assert current_code_response.status_code == 204


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


def test_due_reminders_are_timezone_aware_pending_and_user_scoped(client):
    test_client, _ = client
    assert test_client.get("/api/tasks/reminders/due").status_code == 401

    register(test_client, "Reminder Owner", "reminder-owner@example.com")
    test_client.post("/api/auth/login", json={"email": "reminder-owner@example.com", "password": "secure-pass123"})
    reminder_at = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    due = test_client.post(
        "/api/tasks",
        json={"title": "Send reminder", "due_date": date.today().isoformat(), "reminder_at": reminder_at},
    )
    assert due.status_code == 201, due.text
    assert due.json()["reminder_at"] is not None

    without_reminder = test_client.post(
        "/api/tasks",
        json={"title": "No reminder", "due_date": date.today().isoformat()},
    )
    assert without_reminder.status_code == 201, without_reminder.text
    invalid_timezone = test_client.post(
        "/api/tasks",
        json={"title": "Naive reminder", "reminder_at": "2026-10-22T09:00:00"},
    )
    assert invalid_timezone.status_code == 422

    completed = test_client.post(
        "/api/tasks",
        json={"title": "Completed reminder", "reminder_at": reminder_at},
    )
    assert completed.status_code == 201
    assert test_client.patch(f"/api/tasks/{completed.json()['id']}/toggle").status_code == 200

    reminders = test_client.get("/api/tasks/reminders/due")
    assert reminders.status_code == 200
    assert [task["id"] for task in reminders.json()] == [due.json()["id"]]

    test_client.post("/api/auth/logout")
    register(test_client, "Other Owner", "reminder-other@example.com")
    test_client.post("/api/auth/login", json={"email": "reminder-other@example.com", "password": "secure-pass123"})
    other_due = test_client.post(
        "/api/tasks",
        json={"title": "Other user's reminder", "reminder_at": reminder_at},
    )
    assert other_due.status_code == 201
    assert [task["id"] for task in test_client.get("/api/tasks/reminders/due").json()] == [other_due.json()["id"]]


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
