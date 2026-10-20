import json
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.chat import ChatConversation
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.admin_service import dashboard, list_users, user_details
from app.services.pagination import paginate
from app.services.task_service import (
    admin_task_query,
    create_task,
    list_tasks,
    owned_task,
    task_stats,
    update_task,
)


class ToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskListArgs(ToolArgs):
    status: Literal["all", "pending", "completed"] = "all"
    priority: TaskPriority | None = None
    due_date_from: date | None = None
    due_date_to: date | None = None
    search: str | None = Field(default=None, max_length=160)
    limit: int = Field(default=10, ge=1, le=20)


class TaskIdArgs(ToolArgs):
    task_id: int = Field(gt=0)


class CreateTaskArgs(ToolArgs):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None


class UpdateTaskArgs(TaskIdArgs):
    match_query: str = Field(min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: TaskPriority | None = None
    due_date: date | None = None


class SetStatusArgs(TaskIdArgs):
    match_query: str = Field(min_length=1, max_length=160)
    status: Literal["pending", "completed"]


class TaskStatsArgs(ToolArgs):
    date_from: date | None = None
    date_to: date | None = None


class SearchUsersArgs(ToolArgs):
    search: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None
    role: Literal["admin", "user"] | None = None
    limit: int = Field(default=10, ge=1, le=20)


class UserIdArgs(ToolArgs):
    user_id: int = Field(gt=0)


class AdminTasksArgs(ToolArgs):
    user_id: int | None = Field(default=None, gt=0)
    status: Literal["pending", "completed"] | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = Field(default=None, max_length=160)
    limit: int = Field(default=10, ge=1, le=20)


class UserStatusArgs(UserIdArgs):
    match_query: str = Field(min_length=1, max_length=160)
    is_active: bool


class AdminDeleteTaskArgs(TaskIdArgs):
    match_query: str = Field(min_length=1, max_length=160)


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": _object(properties, required),
        },
    }


TASK_LIST_PROPERTIES = {
    "status": {"type": "string", "enum": ["all", "pending", "completed"]},
    "priority": {"type": ["string", "null"], "enum": ["low", "medium", "high", None]},
    "due_date_from": {"type": ["string", "null"], "format": "date"},
    "due_date_to": {"type": ["string", "null"], "format": "date"},
    "search": {"type": ["string", "null"]},
    "limit": {"type": "integer"},
}

USER_TOOLS = [
    _tool("create_my_task", "Create a task for the authenticated user.", {
        "title": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high"]},
        "due_date": {"type": ["string", "null"], "format": "date"},
    }, ["title"]),
    _tool("list_my_tasks", "List or search the authenticated user's own tasks.", TASK_LIST_PROPERTIES),
    _tool("get_my_task_details", "Get one of the authenticated user's tasks by its ID.", {
        "task_id": {"type": "integer"},
    }, ["task_id"]),
    _tool("update_my_task", "Update permitted fields of one of the authenticated user's tasks.", {
        "task_id": {"type": "integer"},
        "match_query": {"type": "string"},
        "title": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "priority": {"type": ["string", "null"], "enum": ["low", "medium", "high", None]},
        "due_date": {"type": ["string", "null"], "format": "date"},
    }, ["task_id", "match_query"]),
    _tool("set_my_task_status", "Set a task to pending or completed for the authenticated user.", {
        "task_id": {"type": "integer"},
        "match_query": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "completed"]},
    }, ["task_id", "match_query", "status"]),
    _tool("request_delete_my_task", "Ask for explicit confirmation before deleting one of the user's tasks.", {
        "task_id": {"type": "integer"},
        "match_query": {"type": "string"},
    }, ["task_id", "match_query"]),
    _tool("get_my_task_statistics", "Get task totals, completion, overdue and optional completion-range statistics.", {
        "date_from": {"type": ["string", "null"], "format": "date"},
        "date_to": {"type": ["string", "null"], "format": "date"},
    }),
]

ADMIN_TOOLS = [
    _tool("get_system_statistics", "Get aggregate user and task statistics for the system.", {}),
    _tool("search_users", "Search registered users using bounded, permitted account fields.", {
        "search": {"type": ["string", "null"]},
        "is_active": {"type": ["boolean", "null"]},
        "role": {"type": ["string", "null"], "enum": ["admin", "user", None]},
        "limit": {"type": "integer"},
    }),
    _tool("get_user_details", "Get permitted details and task counts for one user.", {
        "user_id": {"type": "integer"},
    }, ["user_id"]),
    _tool("get_user_task_statistics", "Get bounded task totals for one selected user; administrator only.", {
        "user_id": {"type": "integer"},
    }, ["user_id"]),
    _tool("list_tasks_across_users", "Search system tasks with bounded results; only for administrators.", {
        "user_id": {"type": ["integer", "null"]},
        "status": {"type": ["string", "null"], "enum": ["pending", "completed", None]},
        "date_from": {"type": ["string", "null"], "format": "date"},
        "date_to": {"type": ["string", "null"], "format": "date"},
        "search": {"type": ["string", "null"]},
        "limit": {"type": "integer"},
    }),
    _tool("request_user_status_change", "Stage a user account status change, which always requires explicit confirmation.", {
        "user_id": {"type": "integer"},
        "match_query": {"type": "string"},
        "is_active": {"type": "boolean"},
    }, ["user_id", "match_query", "is_active"]),
    _tool("request_delete_task_as_admin", "Stage an administrator task deletion, which always requires explicit confirmation.", {
        "task_id": {"type": "integer"},
        "match_query": {"type": "string"},
    }, ["task_id", "match_query"]),
]


def serialize_task(
    task: Task,
    include_owner: bool = False,
    include_description: bool = False,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": task.id,
        "title": task.title,
        "description": task.description[:500] if include_description and task.description else None,
        "status": task.status.value,
        "priority": task.priority.value,
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }
    if include_owner:
        data["owner"] = {
            "id": task.owner.id,
            "name": task.owner.name,
            "email": task.owner.email,
        }
    return data


def _success(action: dict[str, Any], message: str) -> dict[str, Any]:
    return {"ok": True, "message": message, "action": action}


def _stage_pending_action(conversation: ChatConversation, action: dict[str, Any]) -> None:
    action["requested_at"] = datetime.now(timezone.utc).isoformat()
    conversation.pending_action = action


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise PermissionError("Administrator access is required.")


def _task_id_set(messages: list[dict[str, Any]]) -> set[int]:
    ids: set[int] = set()
    for message in messages:
        if message.get("role") != "tool" or not message.get("content"):
            continue
        try:
            payload = json.loads(message["content"])
        except (TypeError, json.JSONDecodeError):
            continue
        action = payload.get("action", {})
        if action.get("type") not in {
            "task_list", "admin_task_list", "task_details", "task_created",
            "task_updated", "task_status",
        }:
            continue
        for item in action.get("items", []):
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                ids.add(item["id"])
        item = action.get("data")
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            ids.add(item["id"])
    return ids


def _resolve_unique_owned_task(db: Session, user_id: int, task_id: int, query: str) -> Task | None:
    if not query.strip():
        return None
    pattern = f"%{query.strip()}%"
    matches = list(
        db.scalars(
            select(Task).where(
                Task.user_id == user_id,
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern)),
            ).limit(2)
        ).all()
    )
    if len(matches) != 1 or matches[0].id != task_id:
        return None
    return matches[0]


def execute_tool(
    name: str,
    raw_arguments: str,
    *,
    db: Session,
    user: User,
    conversation: ChatConversation,
    previous_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(raw_arguments) > 8000:
        return {"ok": False, "error": "The tool arguments exceed the supported size."}
    if user.role == UserRole.ADMIN:
        allowed_tools = {tool["function"]["name"] for tool in ADMIN_TOOLS + USER_TOOLS}
    else:
        allowed_tools = {tool["function"]["name"] for tool in USER_TOOLS}
    if name not in allowed_tools:
        return {"ok": False, "error": "This operation is not authorized for this account."}

    try:
        args: dict[str, Any] = json.loads(raw_arguments)
        if not isinstance(args, dict):
            raise ValueError("Arguments must be a JSON object.")
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "error": "The tool arguments were not valid JSON."}

    try:
        if name == "create_my_task":
            parsed = CreateTaskArgs.model_validate(args)
            task = create_task(
                db,
                user,
                TaskCreate(
                    title=parsed.title,
                    description=parsed.description,
                    priority=parsed.priority,
                    due_date=parsed.due_date,
                ),
            )
            data = serialize_task(task)
            return _success({"type": "task_created", "data": data}, f"Created task '{task.title}'.")

        if name == "list_my_tasks":
            parsed = TaskListArgs.model_validate(args)
            if parsed.due_date_from and parsed.due_date_to and parsed.due_date_from > parsed.due_date_to:
                return {"ok": False, "error": "The due date range is invalid."}
            result = list_tasks(
                db,
                user.id,
                search=parsed.search,
                status_filter=parsed.status,
                priority=parsed.priority,
                sort_by="due_date",
                order="asc",
                page=1,
                page_size=parsed.limit,
                due_date_from=parsed.due_date_from,
                due_date_to=parsed.due_date_to,
            )
            items = [serialize_task(task) for task in result["items"]]
            return _success(
                {"type": "task_list", "items": items, "total": result["total"]},
                f"Found {result['total']} matching task(s).",
            )

        if name == "get_my_task_details":
            parsed = TaskIdArgs.model_validate(args)
            task = owned_task(db, parsed.task_id, user.id)
            if task is None:
                return {"ok": False, "error": "Task not found."}
            return _success(
                {"type": "task_details", "data": serialize_task(task, include_description=True)},
                "Task details retrieved.",
            )

        if name == "update_my_task":
            parsed = UpdateTaskArgs.model_validate(args)
            if parsed.task_id not in _task_id_set(previous_messages):
                return {"ok": False, "error": "Find the task using your authorized task list or details before updating it."}
            changes = parsed.model_dump(exclude={"task_id"}, exclude_unset=True)
            changes.pop("match_query", None)
            if not changes:
                return {"ok": False, "error": "Specify at least one task field to update."}
            task = _resolve_unique_owned_task(db, user.id, parsed.task_id, parsed.match_query)
            if task is None:
                return {"ok": False, "error": "That task match is ambiguous or does not match. Ask the user to clarify."}
            updated = update_task(db, task, TaskUpdate(**changes))
            return _success({"type": "task_updated", "data": serialize_task(updated)}, f"Updated task '{updated.title}'.")

        if name == "set_my_task_status":
            parsed = SetStatusArgs.model_validate(args)
            if parsed.task_id not in _task_id_set(previous_messages):
                return {"ok": False, "error": "Find the task using your authorized task list or details before changing it."}
            task = _resolve_unique_owned_task(db, user.id, parsed.task_id, parsed.match_query)
            if task is None:
                return {"ok": False, "error": "That task match is ambiguous or does not match. Ask the user to clarify."}
            target = TaskStatus(parsed.status)
            if task.status != target:
                task.status = target
                task.completed_at = datetime.now(timezone.utc) if target == TaskStatus.COMPLETED else None
                task.updated_at = datetime.now(timezone.utc)
                db.flush()
            return _success(
                {"type": "task_status", "data": serialize_task(task)},
                f"Set '{task.title}' to {task.status.value}.",
            )

        if name == "request_delete_my_task":
            parsed = AdminDeleteTaskArgs.model_validate(args)
            if parsed.task_id not in _task_id_set(previous_messages):
                return {"ok": False, "error": "Find the task using your authorized task list or details before requesting deletion."}
            task = _resolve_unique_owned_task(db, user.id, parsed.task_id, parsed.match_query)
            if task is None:
                return {"ok": False, "error": "That task match is ambiguous or does not match. Ask the user to clarify."}
            _stage_pending_action(
                conversation,
                {"type": "delete_my_task", "task_id": task.id, "title": task.title},
            )
            db.flush()
            return _success(
                {"type": "confirmation_required", "data": {"task_id": task.id, "title": task.title}},
                f"Please confirm deleting '{task.title}'. Reply yes to delete it, or no to cancel.",
            )

        if name == "get_my_task_statistics":
            parsed = TaskStatsArgs.model_validate(args)
            if parsed.date_from and parsed.date_to and parsed.date_from > parsed.date_to:
                return {"ok": False, "error": "The date range is invalid."}
            if parsed.date_to == date.max:
                return {"ok": False, "error": "The requested end date is outside the supported range."}
            from zoneinfo import ZoneInfo

            from app.core.config import settings

            stats = task_stats(db, user.id, today=datetime.now(ZoneInfo(settings.default_timezone)).date())
            completed_query = select(func.count(Task.id)).where(
                Task.user_id == user.id,
                Task.status == TaskStatus.COMPLETED,
            )
            if parsed.date_from:
                local_start = datetime.combine(
                    parsed.date_from, time.min, tzinfo=ZoneInfo(settings.default_timezone)
                ).astimezone(timezone.utc)
                completed_query = completed_query.where(
                    Task.completed_at >= local_start
                )
            if parsed.date_to:
                local_end = datetime.combine(
                    parsed.date_to + timedelta(days=1),
                    time.min,
                    tzinfo=ZoneInfo(settings.default_timezone),
                ).astimezone(timezone.utc)
                completed_query = completed_query.where(
                    Task.completed_at < local_end
                )
            stats["completed_in_range"] = db.scalar(completed_query) or 0
            return _success({"type": "task_statistics", "data": stats}, "Task statistics retrieved.")

        if name == "get_system_statistics":
            _require_admin(user)
            ToolArgs.model_validate(args)
            values = dashboard(db)
            data = {key: values[key] for key in (
                "total_users", "active_users", "inactive_users", "total_tasks",
                "completed_tasks", "pending_tasks",
            )}
            return _success({"type": "system_statistics", "data": data}, "System statistics retrieved.")

        if name == "search_users":
            _require_admin(user)
            parsed = SearchUsersArgs.model_validate(args)
            result = list_users(
                db,
                search=parsed.search,
                role=UserRole(parsed.role) if parsed.role else None,
                is_active=parsed.is_active,
                page=1,
                page_size=parsed.limit,
            )
            items = [{
                "id": item.id,
                "name": item.name,
                "email": item.email,
                "role": item.role.value,
                "is_active": item.is_active,
            } for item in result["items"]]
            return _success({"type": "user_list", "items": items, "total": result["total"]}, "User search completed.")

        if name == "get_user_details":
            _require_admin(user)
            parsed = UserIdArgs.model_validate(args)
            data = user_details(db, parsed.user_id)
            if data is None:
                return {"ok": False, "error": "User not found."}
            safe_data = {
                key: (value.value if isinstance(value, UserRole) else value.isoformat() if isinstance(value, datetime) else value)
                for key, value in data.items()
            }
            return _success({"type": "user_details", "data": safe_data}, "Permitted user details retrieved.")

        if name == "get_user_task_statistics":
            _require_admin(user)
            parsed = UserIdArgs.model_validate(args)
            if db.get(User, parsed.user_id) is None:
                return {"ok": False, "error": "User not found."}
            from zoneinfo import ZoneInfo

            from app.core.config import settings

            today = datetime.now(ZoneInfo(settings.default_timezone)).date()
            counts = db.execute(
                select(
                    func.count(Task.id),
                    func.count(Task.id).filter(Task.status == TaskStatus.PENDING),
                    func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED),
                    func.count(Task.id).filter(
                        Task.status == TaskStatus.PENDING,
                        Task.due_date < today,
                    ),
                ).where(Task.user_id == parsed.user_id)
            ).one()
            data = {
                "total": counts[0],
                "pending": counts[1],
                "completed": counts[2],
                "overdue": counts[3],
            }
            return _success({"type": "user_task_statistics", "data": data}, "User task statistics retrieved.")

        if name == "list_tasks_across_users":
            _require_admin(user)
            parsed = AdminTasksArgs.model_validate(args)
            if parsed.date_from and parsed.date_to and parsed.date_from > parsed.date_to:
                return {"ok": False, "error": "The date range is invalid."}
            statement = admin_task_query(
                user_id=parsed.user_id,
                status_filter=parsed.status,
                date_from=parsed.date_from,
                date_to=parsed.date_to,
                search=parsed.search,
            ).options(joinedload(Task.owner))
            result = paginate(db, statement, page=1, page_size=parsed.limit)
            items = [serialize_task(task, include_owner=True) for task in result["items"]]
            return _success({"type": "admin_task_list", "items": items, "total": result["total"]}, "System task search completed.")

        if name == "request_user_status_change":
            _require_admin(user)
            parsed = UserStatusArgs.model_validate(args)
            if not parsed.match_query.strip():
                return {"ok": False, "error": "Identify the target account before changing its status."}
            target = db.get(User, parsed.user_id)
            if target is None:
                return {"ok": False, "error": "User not found."}
            pattern = f"%{parsed.match_query.strip()}%"
            user_matches = list(db.scalars(
                select(User).where(or_(User.name.ilike(pattern), User.email.ilike(pattern))).limit(2)
            ).all())
            if len(user_matches) != 1 or user_matches[0].id != target.id:
                return {"ok": False, "error": "That user match is ambiguous or does not match. Ask the administrator to clarify."}
            if target.id == user.id and not parsed.is_active:
                return {"ok": False, "error": "You cannot deactivate your own account."}
            if target.is_active == parsed.is_active:
                return _success(
                    {"type": "user_status", "data": {"id": target.id, "is_active": target.is_active}},
                    "That account already has the requested status.",
                )
            _stage_pending_action(
                conversation,
                {
                    "type": "set_user_status",
                    "user_id": target.id,
                    "name": target.name,
                    "is_active": parsed.is_active,
                },
            )
            db.flush()
            verb = "activate" if parsed.is_active else "deactivate"
            return _success(
                {"type": "confirmation_required", "data": {"user_id": target.id, "name": target.name}},
                f"Please confirm you want to {verb} {target.name}'s account. Reply yes to confirm, or no to cancel.",
            )

        if name == "request_delete_task_as_admin":
            _require_admin(user)
            parsed = AdminDeleteTaskArgs.model_validate(args)
            if not parsed.match_query.strip():
                return {"ok": False, "error": "Identify the target task before requesting deletion."}
            if parsed.task_id not in _task_id_set(previous_messages):
                return {"ok": False, "error": "Find the task using the system task search before requesting deletion."}
            pattern = f"%{parsed.match_query.strip()}%"
            matches = list(db.scalars(
                select(Task).where(
                    or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
                ).limit(2)
            ).all())
            if len(matches) != 1 or matches[0].id != parsed.task_id:
                return {"ok": False, "error": "That task match is ambiguous or does not match. Ask the administrator to clarify."}
            task = matches[0]
            _stage_pending_action(
                conversation,
                {
                    "type": "delete_task_as_admin",
                    "task_id": task.id,
                    "title": task.title,
                    "owner_id": task.user_id,
                },
            )
            db.flush()
            return _success(
                {
                    "type": "confirmation_required",
                    "data": {"task_id": task.id, "title": task.title, "owner_id": task.user_id},
                },
                f"Please confirm deleting '{task.title}' belonging to user {task.user_id}. Reply yes to confirm, or no to cancel.",
            )

        return {"ok": False, "error": "Unknown operation."}
    except ValidationError as exc:
        details = "; ".join(error["msg"] for error in exc.errors()[:3])
        return {"ok": False, "error": f"Invalid tool arguments: {details}"}
    except PermissionError as exc:
        return {"ok": False, "error": str(exc)}


def confirm_pending_action(db: Session, conversation: ChatConversation, user: User) -> dict[str, Any]:
    pending = conversation.pending_action
    if pending is None:
        return {"reply": "There is no pending action to confirm.", "actions": []}

    try:
        requested_at = datetime.fromisoformat(pending["requested_at"])
        if requested_at.tzinfo is None:
            requested_at = requested_at.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        conversation.pending_action = None
        return {"reply": "The pending action was invalid and has been cancelled.", "actions": []}
    if datetime.now(timezone.utc) - requested_at > timedelta(minutes=10):
        conversation.pending_action = None
        return {"reply": "That confirmation has expired. Please request the action again.", "actions": []}

    kind = pending.get("type")
    if kind == "delete_my_task":
        task = owned_task(db, pending["task_id"], user.id)
        if task is None or task.title != pending["title"]:
            conversation.pending_action = None
            return {"reply": "That task is no longer available, so nothing was deleted.", "actions": []}
        title = task.title
        db.delete(task)
        action = {"type": "task_deleted", "data": {"task_id": task.id, "title": title}}
        reply = f"Deleted '{title}'."
    elif kind == "set_user_status":
        if user.role != UserRole.ADMIN:
            conversation.pending_action = None
            return {"reply": "Administrator access is no longer available, so the action was cancelled.", "actions": []}
        target = db.get(User, pending["user_id"])
        if (
            target is None
            or target.name != pending["name"]
            or (target.id == user.id and not pending["is_active"])
        ):
            conversation.pending_action = None
            return {"reply": "That account can no longer be changed by this action.", "actions": []}
        target.is_active = pending["is_active"]
        target.updated_at = datetime.now(timezone.utc)
        action = {"type": "user_status", "data": {"id": target.id, "name": target.name, "is_active": target.is_active}}
        reply = f"{'Activated' if target.is_active else 'Deactivated'} {target.name}'s account."
    elif kind == "delete_task_as_admin":
        if user.role != UserRole.ADMIN:
            conversation.pending_action = None
            return {"reply": "Administrator access is no longer available, so the action was cancelled.", "actions": []}
        task = db.get(Task, pending["task_id"])
        if task is None or task.title != pending["title"] or task.user_id != pending["owner_id"]:
            conversation.pending_action = None
            return {"reply": "That task is no longer available, so nothing was deleted.", "actions": []}
        title = task.title
        owner_id = task.user_id
        db.delete(task)
        action = {"type": "admin_task_deleted", "data": {"task_id": pending["task_id"], "title": title, "owner_id": owner_id}}
        reply = f"Deleted '{title}' for user {owner_id}."
    else:
        conversation.pending_action = None
        return {"reply": "The pending action was invalid and has been cancelled.", "actions": []}

    conversation.pending_action = None
    db.flush()
    return {"reply": reply, "actions": [action]}


def cancel_pending_action(db: Session, conversation: ChatConversation) -> dict[str, Any]:
    pending = conversation.pending_action or {}
    conversation.pending_action = None
    db.flush()
    return {
        "reply": f"Cancelled the pending action for '{pending.get('title') or pending.get('name') or 'the selected record'}'.",
        "actions": [],
    }
