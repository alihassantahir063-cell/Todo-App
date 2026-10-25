# Daymark FastAPI backend

The API is built with FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL, Alembic, Argon2 password hashing, JWT access cookies, and per-IP rate limiting. PostgreSQL is the application database. Tests use a separate SQLite database in memory and never require a running PostgreSQL server.

## 1. Install PostgreSQL and create the development database

Install PostgreSQL from <https://www.postgresql.org/download/> and start its service. On Windows, the PostgreSQL installer includes **SQL Shell (psql)**. Connect as the PostgreSQL administrator:

```powershell
psql -U postgres
```

At the `postgres=#` prompt, create a development role and database. Use your own local password in place of `PLACEHOLDER_PASSWORD`:

```sql
CREATE USER todo_app WITH PASSWORD 'PLACEHOLDER_PASSWORD';
CREATE DATABASE todo_app OWNER todo_app;
\q
```

Do not use the placeholder password in a real environment. The app connects with the `todo_app` role; never run the application as PostgreSQL's superuser.

## 2. Configure the environment

From the `backend` directory:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL` to the role/database/password created above. Replace `SECRET_KEY` with a long, random value of at least 32 characters; set a strong `ADMIN_PASSWORD`; and ensure `FRONTEND_ORIGIN` matches the frontend URL exactly. The application deliberately refuses to start without an explicit database URL and signing key rather than falling back to insecure baked-in defaults. Keep `COOKIE_SECURE=false` only for local HTTP development. Use `COOKIE_SECURE=true` behind HTTPS in production. Never commit `.env`.

Both regular users and administrators can create a password recovery code in their profile settings. Creating a code requires the current password; it is shown only once, so save it in a password manager. Creating another code invalidates the previous one. The code works without SMTP and can reset the password once; only its hash is stored in the database.

Email recovery is also available when `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` are configured. Port 587 uses STARTTLS by default; set `SMTP_USE_SSL=true` for an implicit-TLS server such as port 465. SMTP credentials must remain in the backend environment and must never be added to frontend variables. Email reset links expire after 30 minutes and can only be used once. The forgot-password endpoint returns a generic message for unknown email addresses. A password reset or authenticated password change invalidates any existing recovery code.

Task reminders are browser notifications. A task with a due date gets a default reminder at 9:00 AM in the browser's local timezone; a custom date/time can replace it. Users and administrators must grant notification permission in their profile settings. The app checks due reminders while it is open and notifies each browser once per scheduled time. This is not a push-notification service: reminders cannot arrive while the browser/app is closed. Production hosting must use HTTPS; localhost is allowed for local development.

The URL format is:

```text
postgresql+psycopg://todo_app:YOUR_PASSWORD@localhost:5432/todo_app
```

If the password has URL-reserved characters, percent-encode them in the URL.

## 3. Create a virtual environment and install requirements

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, enable script execution for the current user or invoke `.venv\Scripts\python.exe` directly rather than changing machine-wide policy.

## 4. Apply migrations and start the API

Run these commands from `backend` with the virtual environment active:

```powershell
alembic upgrade head
python scripts/create_admin.py
uvicorn app.main:app --reload
```

The API listens at <http://localhost:8000>, API paths start with `/api`, and Swagger UI is at <http://localhost:8000/docs>. The migration creates the initial `users` and `tasks` tables, PostgreSQL enums, foreign key, check constraints, and indexes. The admin CLI reads `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` from `.env`; it is safe to rerun for an existing administrator and refuses to silently promote an existing regular account.

Users and administrators can choose **Forgot your password?** on the sign-in screen and enter their saved recovery code, email address, and a new password. Alternatively, configure SMTP to send a reset link. No role-specific setup is needed.

Verify actual database connectivity and ORM relationships with:

```powershell
python scripts/check_db.py
```

### Create a future migration

After changing a SQLAlchemy model, generate and inspect a migration before applying it:

```powershell
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
```

Review generated enum operations, constraints, indexes, and both `upgrade()` and `downgrade()` before running against any shared database.

### Downgrade and safely reset development data

Undo one migration:

```powershell
alembic downgrade -1
```

Return the schema to Alembic's base revision, then reapply all migrations:

```powershell
alembic downgrade base
alembic upgrade head
```

Alternatively, from `psql -U postgres`, drop and recreate **only the local development database**:

```sql
DROP DATABASE todo_app;
CREATE DATABASE todo_app OWNER todo_app;
\q
```

Then run `alembic upgrade head` and `python scripts/create_admin.py` again. These reset operations permanently delete data. **Never use a development reset, downgrade-to-base, or drop-database command in production.** Take verified backups and follow an approved production migration/recovery procedure instead.

### Verify PostgreSQL schema

Connect to the app database:

```powershell
psql -U todo_app -d todo_app -h localhost
```

Then inspect the tables and task schema:

```sql
\dt
\d tasks
\q
```

After migrations, `\dt` should include `users`, `tasks`, and `alembic_version`; `\d tasks` should show the owner foreign key with `ON DELETE CASCADE`, status/priority/due-date/user/composite indexes, and the title/completion timestamp check constraints.

## Authentication and security notes

- Login issues a JWT in an HttpOnly cookie named `access_token`, with `SameSite=Lax`, path `/`, and `Secure` controlled by `COOKIE_SECURE`. Logout expires the cookie.
- Protected routes also accept an `Authorization: Bearer ...` header for API clients and Swagger's **Authorize** control.
- Passwords are hashed with Argon2. User response schemas intentionally omit `hashed_password`.
- Registration ignores role/status inputs and always assigns an active `user`; authorization uses the database role.
- Authenticated task queries are scoped to the current user. A foreign task ID returns 404.
- Login and registration are limited to 8 requests per minute per client IP. CORS permits only `FRONTEND_ORIGIN` and credentials.

## Run tests

Tests use a fresh in-memory SQLite database for each test function. They do not use `DATABASE_URL` or change PostgreSQL data:

```powershell
pytest -v
```

Run only API behavior coverage:

```powershell
pytest -v tests/test_api.py
```

For manual test database configuration, set `TEST_DATABASE_URL` in the test environment and point tests at a dedicated test-only database. Never use a production database as a test database.

## Endpoint reference

All paths below are prefixed by `/api`. Authenticated means a valid access cookie or bearer token. Admin endpoints additionally require a database user with the `admin` role.

| Method | Path | Auth required | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Register a regular user |
| POST | `/auth/login` | No | Sign in and set the HttpOnly access cookie |
| POST | `/auth/logout` | No | Clear the access cookie |
| POST | `/auth/forgot-password` | No | Request a password reset email (requires SMTP configuration) |
| POST | `/auth/reset-password` | No | Reset a password with a valid email token |
| POST | `/auth/reset-with-recovery-code` | No | Reset a password with a one-time recovery code |
| GET | `/auth/me` | Yes | Return the current safe user profile |
| PATCH | `/auth/me` | Yes | Update current user's name/email |
| POST | `/auth/change-password` | Yes | Change password after current-password verification |
| POST | `/auth/recovery-code` | Yes | Create or replace the account's one-time recovery code |
| POST | `/tasks` | Yes | Create a task for the current user |
| GET | `/tasks` | Yes | Search, filter, sort, and paginate current user's tasks |
| GET | `/tasks/stats` | Yes | Return real totals, overdue count, and completion percentage |
| GET | `/tasks/reminders/due` | Yes | Return pending tasks with reminders due in the last seven days |
| GET | `/tasks/{task_id}` | Yes | Read an owned task; other users' tasks return 404 |
| PATCH | `/tasks/{task_id}` | Yes | Update an owned task's editable fields |
| PATCH | `/tasks/{task_id}/toggle` | Yes | Complete/reopen an owned task |
| DELETE | `/tasks/{task_id}` | Yes | Delete an owned task |
| GET | `/admin/dashboard` | Admin | Return real user/task totals and five recent records |
| GET | `/admin/users` | Admin | Search/filter/paginate user accounts |
| GET | `/admin/users/{user_id}` | Admin | Read safe account details and task counts |
| PATCH | `/admin/users/{user_id}/status` | Admin | Activate/deactivate a user (admins cannot deactivate themselves) |
| GET | `/admin/tasks` | Admin | Filter and paginate tasks across the workspace |
| DELETE | `/admin/tasks/{task_id}` | Admin | Delete any task |
| POST | `/chat/message` | Yes | Send a message to the AI assistant (OpenRouter configuration required) |
| DELETE | `/chat/conversations/{conversation_id}` | Yes | Delete the current user's chat conversation |

Paginated endpoints return `{ "items": [], "total": 0, "page": 1, "page_size": 10, "pages": 0 }`. Error responses use `{ "detail": "message" }`; request validation errors use FastAPI's standard 422 response.

## Troubleshooting

- **Connection refused:** confirm the PostgreSQL service is running, the hostname/port in `DATABASE_URL` is correct, and local port 5432 is reachable.
- **Password authentication failed:** recheck the PostgreSQL role/password and URL-encode reserved password characters. Ensure `.env` is in the current `backend` directory and restart the process after edits.
- **Database does not exist:** create the database with `CREATE DATABASE todo_app OWNER todo_app;` and verify the database name in `DATABASE_URL`.
- **Enum already exists:** inspect the current revision with `alembic current` and tables/types with `psql`. Do not blindly drop types from a shared database. For a disposable local database only, recreate it using the reset procedure above and apply migrations once.
- **CORS error:** set `FRONTEND_ORIGIN` to the exact browser origin (for Vite, `http://localhost:5173`); credentialed CORS cannot use `*`.
- **Cookie not sent:** in local HTTP development keep `COOKIE_SECURE=false`; use the same site/host, allow credentials, and let Vite proxy `/api` to port 8000. Use HTTPS with `COOKIE_SECURE=true` in production.
- **401 after login:** inspect the login response's `Set-Cookie`, cookie path/domain, the API target, and JWT expiry. Changing `SECRET_KEY` invalidates existing cookies. The API also supports bearer tokens in Swagger and tests.
- **Argon2 install errors:** update pip in the virtual environment and install the pinned requirements on a supported Python 3.14 build. On managed Windows hosts, use a Python distribution for which argon2-cffi publishes compatible wheels rather than installing into a different interpreter.
