# Daymark Todo Management

Daymark is a full-stack task management application with separate workspaces for regular users and administrators. The React app communicates with a FastAPI API backed by PostgreSQL; user, task, and dashboard data comes from the database rather than demo records.

## Features

### User workspace

- Register, sign in, sign out, and restore a session using an HttpOnly authentication cookie.
- View a dashboard with task totals, pending/completed/overdue counts, completion progress, and recent tasks.
- Create, edit, delete, complete, and reopen tasks.
- Add an optional description, low/medium/high priority, due date, and reminder.
- Search tasks; filter by status and priority; sort by creation date, due date, or priority; and paginate results.
- Update profile name and email, change a password, and create a one-time password recovery code.
- Receive browser reminders while the app is open. Due-date reminders default to 9:00 AM local time; a custom reminder time is optional.
- Switch between light and dark themes.

### Administrator workspace

- View live user and task totals plus recent users and tasks.
- Search, filter, and paginate users by role and account status; inspect account details and task counts.
- Activate or deactivate accounts. An administrator cannot deactivate their own account.
- Search and filter tasks across accounts by owner, status, creation date, and title; permanently delete a task after confirmation.
- Use the same profile, password recovery, theme, and AI assistant features available to users.

### AI task assistant

- Authenticated users can ask about, create, update, complete/reopen, and request deletion of their own tasks; they can also ask for task statistics.
- Administrators additionally have permission-checked tools for system statistics, user search/details, and workspace task management.
- Destructive task deletion and sensitive administrator changes require an explicit follow-up confirmation. The assistant uses bounded backend tools, not generated SQL or arbitrary database access.
- Chat requires an OpenRouter API key. Without one, the API returns a configuration error rather than a fabricated response.

### Account recovery and reminders

- Email password-reset links are optional and require SMTP configuration. Links expire after 30 minutes and are single-use.
- A one-time recovery code can reset a password without email. It is shown only when created, and generating a replacement invalidates the previous code.
- Browser reminders require notification permission and the app to remain open; they are not push notifications and cannot be delivered while the app is closed.

## Technology

| Area | Stack |
|---|---|
| Frontend | React 18, React Router, Vite, Axios, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Database and migrations | PostgreSQL, Alembic |
| Authentication | Argon2 password hashing, JWT in an HttpOnly cookie |
| AI integration | OpenRouter through its OpenAI-compatible API |
| Tests | Pytest; backend tests use an isolated in-memory SQLite database by default |

## Requirements

- PostgreSQL
- Python 3.14 and pip (see the backend setup guide for Windows-specific installation notes)
- Node.js 20.19+ or 22.12+, and npm

## Run locally

Use three terminals from the repository root.

### 1. Set up PostgreSQL

Install and start PostgreSQL. Create a development role and database, replacing the placeholder with a local password:

```sql
CREATE USER todo_app WITH PASSWORD 'YOUR_LOCAL_PASSWORD';
CREATE DATABASE todo_app OWNER todo_app;
```

### 2. Configure and start the backend

```powershell
Set-Location backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` before starting the API:

- Set `DATABASE_URL` to the PostgreSQL role and database you created.
- Set `SECRET_KEY` to a long, random value (at least 32 characters).
- Set `ADMIN_NAME`, `ADMIN_EMAIL`, and a strong `ADMIN_PASSWORD` for the initial administrator.
- Keep `FRONTEND_ORIGIN=http://localhost:5173` for local development.
- Keep `COOKIE_SECURE=false` only for local HTTP; production deployments should use HTTPS and `COOKIE_SECURE=true`.

Then run:

```powershell
alembic upgrade head
python scripts/create_admin.py
uvicorn app.main:app --reload
```

The API is available at <http://localhost:8000>, with Swagger UI at <http://localhost:8000/docs>.

### 3. Configure and start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `http://localhost:8000` by default. To proxy to a different local backend port, set `VITE_API_PROXY_TARGET`; to use a different API base URL, set `VITE_API_URL`. Do not put secrets or provider credentials in frontend environment variables.

### Optional: email password resets

To enable reset links as an alternative to recovery codes, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` in `backend/.env`. Port 587 uses STARTTLS by default; set `SMTP_USE_SSL=true` for implicit TLS, commonly on port 465. Keep SMTP credentials on the backend.

### Optional: AI assistant

1. Create an OpenRouter API key and set `OPENROUTER_API_KEY` in `backend/.env`.
2. Keep `AI_PROVIDER=openrouter` and `AI_MODEL=openrouter/free` (the default), or choose a specific free model using its `:free` model ID. The backend rejects paid model IDs; the free router does not fall back to paid models. Model availability and rate limits can vary.
3. Restart the backend. Open the floating assistant after signing in.

The API allows up to 20 chat requests per minute. Conversations belong to the signed-in user, keep up to 24 recent messages, and expire after 30 days; up to 20 conversations are retained per account. Pending sensitive-action confirmations expire after 10 minutes. `DEFAULT_TIMEZONE` defaults to `Asia/Karachi` and must be a valid IANA timezone.

## Application pages

| Route | Access | Purpose |
|---|---|---|
| `/login`, `/register` | Public | Sign in or create a user account |
| `/forgot-password`, `/reset-password` | Public | Start and complete password recovery |
| `/dashboard` | Signed-in user | Personal task overview and recent tasks |
| `/tasks` | Signed-in user | Manage, search, filter, sort, and page through tasks |
| `/profile` | Signed-in user | Profile, password, recovery code, and notification settings |
| `/admin` | Administrator | Workspace overview |
| `/admin/users` | Administrator | Find and manage user accounts |
| `/admin/tasks` | Administrator | Review and manage workspace tasks |
| `/admin/profile` | Administrator | Administrator profile and account settings |

Unknown pages show a not-found screen. Regular users visiting an administrator route are denied access; authorization is also enforced by the backend.

## API overview

All API routes start with `/api`. Protected routes accept the HttpOnly access cookie; the backend also supports bearer tokens for API clients and Swagger's Authorize control. Administrator routes require an account with the database `admin` role.

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register a regular user |
| `POST` | `/auth/login` | Public | Authenticate and set the access cookie |
| `POST` | `/auth/logout` | Public | Clear the access cookie |
| `GET`, `PATCH` | `/auth/me` | Signed in | Read or update the current profile |
| `POST` | `/auth/change-password` | Signed in | Change password after verifying the current password |
| `POST` | `/auth/recovery-code` | Signed in | Create a one-time recovery code |
| `POST` | `/auth/forgot-password` | Public | Request an email reset link (SMTP required) |
| `POST` | `/auth/reset-password` | Public | Reset with an email token |
| `POST` | `/auth/reset-with-recovery-code` | Public | Reset with a recovery code |
| `POST` | `/tasks` | Signed in | Create an owned task |
| `GET` | `/tasks` | Signed in | Search, filter, sort, and paginate owned tasks |
| `GET`, `PATCH`, `DELETE` | `/tasks/{task_id}` | Signed in | Read, update, or delete an owned task |
| `PATCH` | `/tasks/{task_id}/toggle` | Signed in | Complete or reopen an owned task |
| `GET` | `/tasks/stats` | Signed in | Get personal task statistics |
| `GET` | `/tasks/reminders/due` | Signed in | Fetch due reminders for the current user |
| `GET` | `/admin/dashboard` | Admin | Get workspace totals and recent activity |
| `GET` | `/admin/users`, `/admin/users/{user_id}` | Admin | Search/list users or inspect one account |
| `PATCH` | `/admin/users/{user_id}/status` | Admin | Activate or deactivate an account |
| `GET` | `/admin/tasks` | Admin | Search and list workspace tasks |
| `DELETE` | `/admin/tasks/{task_id}` | Admin | Delete a workspace task |
| `POST` | `/chat/message` | Signed in | Send a message to the AI assistant |
| `DELETE` | `/chat/conversations/{conversation_id}` | Signed in | Delete the current user's conversation |

Task and user lists are paginated. Task listing supports search, status/priority filters, due-date ranges, sorting, and page sizing; administrator task listing supports owner, status, creation-date range, and title search. See the [backend README](./backend/README.md) for full endpoint details, database administration, and troubleshooting.

## Verification

Run backend tests from `backend`:

```powershell
pytest -v
```

Build the frontend from `frontend`:

```powershell
npm run build
```

The frontend also has a manual user/admin verification checklist in its [README](./frontend/README.md). The backend's [README](./backend/README.md) documents migrations, database checks, API behavior, and deployment/security settings.

## Security and deployment notes

- Never commit `.env` files or expose database, SMTP, JWT, or OpenRouter credentials in frontend code.
- Use a strong `SECRET_KEY`, HTTPS, and `COOKIE_SECURE=true` in production.
- Set `FRONTEND_ORIGIN` to the exact deployed frontend origin; credentialed CORS does not allow a wildcard origin.
- Passwords are Argon2-hashed. Registration always creates a regular user; client-side route guards are not the authorization boundary.
- User task queries are scoped to the authenticated account. Administrator operations require the backend role check.
- Reminders run in the browser while the app is open; configure a separate push-notification service if background delivery is required.

For detailed backend setup, migration/reset safety, and API troubleshooting, see [backend/README.md](./backend/README.md). For frontend workflows and the manual verification checklist, see [frontend/README.md](./frontend/README.md).
