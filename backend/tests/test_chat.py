import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from openai import APIConnectionError

from app.chat.provider import (
    FREE_MODEL_ROUTER,
    OPENROUTER_BASE_URL,
    ChatProviderError,
    OpenRouterProvider,
    get_ai_provider,
)
from app.core.config import settings
from app.models.chat import ChatConversation
from app.models.task import Task
from app.core.security import hash_password
from app.models.user import User, UserRole
from tests.conftest import login, register


class StubProvider:
    def __init__(self, *responses):
        self.responses = list(responses)

    def complete(self, messages, tools):
        assert tools
        if not self.responses:
            raise AssertionError("Unexpected additional provider request")
        return self.responses.pop(0)


def tool_call(name, arguments, call_id="call_1"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)},
        }],
    }


def use_provider(client, provider):
    from app.api.chat import get_ai_provider as provider_dependency
    from app.main import app

    app.dependency_overrides[provider_dependency] = lambda: provider


def test_chat_requires_authentication(client):
    test_client, _ = client
    response = test_client.post("/api/chat/message", json={"message": "Show my tasks"})
    assert response.status_code == 401


def test_tool_arguments_cannot_mass_assign_or_request_sql(client):
    test_client, session_factory = client
    register(test_client, "Malicious Input", "malicious-chat@example.com")
    login(test_client, "malicious-chat@example.com")
    use_provider(test_client, StubProvider(
        tool_call("create_my_task", {
            "title": "Injected task",
            "role": "admin",
            "user_id": 999,
        }),
        {"role": "assistant", "content": "I couldn't perform that operation."},
    ))

    response = test_client.post("/api/chat/message", json={"message": "Create a task"})
    assert response.status_code == 200, response.text
    assert response.json()["actions"] == []
    with session_factory() as db:
        assert db.query(Task).filter_by(title="Injected task").count() == 0


def test_chat_creates_task_through_validated_tool_and_persists(client):
    test_client, session_factory = client
    register(test_client, "Chat User", "chat-user@example.com")
    login(test_client, "chat-user@example.com")
    use_provider(test_client, StubProvider(
        tool_call("create_my_task", {
            "title": "Finish project",
            "description": None,
            "priority": "high",
            "due_date": None,
        }),
        {"role": "assistant", "content": "Created your task: Finish project."},
    ))

    response = test_client.post("/api/chat/message", json={"message": "Create a high priority task to finish project"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "Created your task: Finish project."
    assert body["actions"][0]["type"] == "task_created"
    assert body["actions"][0]["data"]["title"] == "Finish project"
    with session_factory() as db:
        task = db.query(Task).filter_by(title="Finish project").one()
        assert task.priority.value == "high"
        assert db.query(ChatConversation).count() == 1


def test_delete_requires_next_turn_confirmation(client):
    test_client, session_factory = client
    register(test_client, "Delete User", "delete-user@example.com")
    login(test_client, "delete-user@example.com")
    created = test_client.post("/api/tasks", json={"title": "Old assignment"}).json()
    use_provider(test_client, StubProvider(
        tool_call("list_my_tasks", {"search": "Old assignment"}, "call_list"),
        tool_call("request_delete_my_task", {
            "task_id": created["id"],
            "match_query": "Old assignment",
        }, "call_delete"),
        {"role": "assistant", "content": "Please confirm deleting Old assignment."},
    ))

    staged = test_client.post("/api/chat/message", json={"message": "Delete my old assignment"})
    assert staged.status_code == 200, staged.text
    conversation_id = staged.json()["conversation_id"]
    assert staged.json()["actions"][-1]["type"] == "confirmation_required"
    with session_factory() as db:
        assert db.get(Task, created["id"]) is not None
        conversation = db.get(ChatConversation, conversation_id)
        assert conversation.pending_action["task_id"] == created["id"]

    confirmed = test_client.post("/api/chat/message", json={
        "message": "yes",
        "conversation_id": conversation_id,
    })
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["actions"][0]["type"] == "task_deleted"
    with session_factory() as db:
        assert db.get(Task, created["id"]) is None
        assert db.get(ChatConversation, conversation_id).pending_action is None


def test_chat_completes_a_unique_task_match(client):
    test_client, session_factory = client
    register(test_client, "Update User", "update-chat@example.com")
    login(test_client, "update-chat@example.com")
    task = test_client.post("/api/tasks", json={"title": "Python assignment"}).json()
    use_provider(test_client, StubProvider(
        tool_call("list_my_tasks", {"search": "Python assignment"}, "call_search"),
        tool_call("set_my_task_status", {
            "task_id": task["id"],
            "match_query": "Python assignment",
            "status": "completed",
        }, "call_status"),
        {"role": "assistant", "content": "Marked Python assignment completed."},
    ))

    response = test_client.post("/api/chat/message", json={"message": "Mark my Python assignment completed"})
    assert response.status_code == 200, response.text
    assert response.json()["actions"][-1]["type"] == "task_status"
    with session_factory() as db:
        assert db.get(Task, task["id"]).status.value == "completed"


def test_admin_account_change_requires_confirmation(client):
    test_client, session_factory = client
    target = register(test_client, "Target User", "target-chat@example.com")
    with session_factory() as db:
        db.add(User(
            name="Chat Admin",
            email="chat-admin@example.com",
            hashed_password=hash_password("admin-pass123"),
            role=UserRole.ADMIN,
            is_active=True,
        ))
        db.commit()
    login(test_client, "chat-admin@example.com", "admin-pass123")
    use_provider(test_client, StubProvider(
        tool_call("search_users", {"search": "Target User"}, "call_users"),
        tool_call("request_user_status_change", {
            "user_id": target["id"],
            "match_query": "Target User",
            "is_active": False,
        }, "call_deactivate"),
        {"role": "assistant", "content": "Please confirm deactivation of Target User."},
    ))

    staged = test_client.post("/api/chat/message", json={"message": "Deactivate Target User"})
    assert staged.status_code == 200, staged.text
    assert staged.json()["actions"][-1]["type"] == "confirmation_required"
    with session_factory() as db:
        assert db.get(User, target["id"]).is_active is True

    confirmed = test_client.post("/api/chat/message", json={
        "message": "yes",
        "conversation_id": staged.json()["conversation_id"],
    })
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["actions"][0]["type"] == "user_status"
    with session_factory() as db:
        assert db.get(User, target["id"]).is_active is False


def test_user_cannot_read_another_users_task_through_chat(client):
    test_client, _ = client
    owner = register(test_client, "Owner", "owner-chat@example.com")
    login(test_client, "owner-chat@example.com")
    private_task = test_client.post("/api/tasks", json={"title": "Secret task"}).json()
    test_client.post("/api/auth/logout")
    other = register(test_client, "Other", "other-chat@example.com")
    login(test_client, "other-chat@example.com")
    use_provider(test_client, StubProvider(
        tool_call("get_my_task_details", {"task_id": private_task["id"]}),
        {"role": "assistant", "content": "I couldn't find that task in your account."},
    ))

    response = test_client.post("/api/chat/message", json={"message": "Show task details"})
    assert response.status_code == 200, response.text
    assert response.json()["actions"] == []
    assert owner["id"] != other["id"]
    assert private_task["user_id"] == owner["id"]


def test_ambiguous_task_match_does_not_update_any_record(client):
    test_client, session_factory = client
    register(test_client, "Ambiguous User", "ambiguous-chat@example.com")
    login(test_client, "ambiguous-chat@example.com")
    first = test_client.post("/api/tasks", json={"title": "University assignment"}).json()
    second = test_client.post("/api/tasks", json={"title": "History assignment"}).json()
    use_provider(test_client, StubProvider(
        tool_call("list_my_tasks", {"search": "assignment"}, "call_search"),
        tool_call("set_my_task_status", {
            "task_id": first["id"],
            "match_query": "assignment",
            "status": "completed",
        }, "call_status"),
        {"role": "assistant", "content": "Which assignment do you mean?"},
    ))

    response = test_client.post("/api/chat/message", json={"message": "Complete my assignment"})
    assert response.status_code == 200, response.text
    assert response.json()["reply"] == "Which assignment do you mean?"
    assert [action["type"] for action in response.json()["actions"]] == ["task_list"]
    with session_factory() as db:
        assert db.get(Task, first["id"]).status.value == "pending"
        assert db.get(Task, second["id"]).status.value == "pending"


def test_provider_failure_is_returned_without_stack_details(client):
    test_client, _ = client
    register(test_client, "Provider User", "provider-chat@example.com")
    login(test_client, "provider-chat@example.com")

    class FailingProvider:
        def complete(self, messages, tools):
            raise ChatProviderError("Provider timeout.")

    use_provider(test_client, FailingProvider())
    response = test_client.post("/api/chat/message", json={"message": "Show my tasks"})
    assert response.status_code == 502
    assert response.json()["detail"] == "The AI provider is temporarily unavailable."


def test_conversation_history_is_not_shared_between_users(client):
    test_client, _ = client
    register(test_client, "Conversation Owner", "conversation-owner@example.com")
    login(test_client, "conversation-owner@example.com")
    use_provider(test_client, StubProvider({"role": "assistant", "content": "Hello."}))
    original = test_client.post("/api/chat/message", json={"message": "Hello"})
    assert original.status_code == 200

    test_client.post("/api/auth/logout")
    register(test_client, "Conversation Other", "conversation-other@example.com")
    login(test_client, "conversation-other@example.com")
    response = test_client.post("/api/chat/message", json={
        "message": "Continue",
        "conversation_id": original.json()["conversation_id"],
    })
    assert response.status_code == 404


def test_admin_tool_is_not_exposed_to_regular_user(client):
    test_client, _ = client
    register(test_client, "Regular", "regular-chat@example.com")
    login(test_client, "regular-chat@example.com")
    use_provider(test_client, StubProvider(
        tool_call("get_system_statistics", {}),
        {"role": "assistant", "content": "System-wide statistics are only available to administrators."},
    ))

    response = test_client.post("/api/chat/message", json={"message": "How many users are registered?"})
    assert response.status_code == 200, response.text
    assert response.json()["actions"] == []
    assert "only available" in response.json()["reply"]


def test_provider_without_key_returns_clear_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    get_ai_provider.cache_clear()
    try:
        with pytest.raises(HTTPException) as error:
            get_ai_provider()
        assert error.value.status_code == 503
        assert "OPENROUTER_API_KEY" in error.value.detail
    finally:
        get_ai_provider.cache_clear()


def test_openrouter_provider_uses_free_router_and_openai_tool_calls():
    class FakeCompletions:
        def __init__(self):
            self.request = None

        def create(self, **request):
            self.request = request
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                model_dump=lambda exclude_none: {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "list_my_tasks", "arguments": "{\"status\":\"pending\"}"},
                    }],
                },
            ))])

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    provider = OpenRouterProvider(api_key="test-key", model=FREE_MODEL_ROUTER, timeout=5)
    provider.client = FakeClient()
    tools = [{"type": "function", "function": {"name": "list_my_tasks"}}]
    messages = [{"role": "user", "content": "Show pending tasks."}]

    response = provider.complete(messages, tools)

    request = provider.client.chat.completions.request
    assert request["model"] == "openrouter/free"
    assert request["messages"] == messages
    assert request["tools"] == tools
    assert request["tool_choice"] == "auto"
    assert request["max_tokens"] == 700
    assert json.loads(response["tool_calls"][0]["function"]["arguments"]) == {"status": "pending"}


def test_openrouter_provider_reports_api_errors_safely():
    provider = OpenRouterProvider(api_key="test-key", model=FREE_MODEL_ROUTER, timeout=5)

    class FailingCompletions:
        def create(self, **request):
            raise APIConnectionError(request={"method": "POST", "url": OPENROUTER_BASE_URL})

    provider.client.chat.completions = FailingCompletions()
    with pytest.raises(ChatProviderError):
        provider.complete([{"role": "user", "content": "Hello"}], [])


def test_paid_openrouter_models_are_rejected():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite://",
            secret_key="test-secret-key-at-least-32-characters",
            ai_model="openai/gpt-4o",
        )
