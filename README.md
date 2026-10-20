# Daymark Todo Management

A Todo Management Web Application planned in three phases: PostgreSQL/SQLAlchemy database, FastAPI backend, and React frontend. The frontend in [`frontend/`](./frontend/) is built to the supplied Phase 2 API contract and uses real API requests only.

## Run the complete application

1. Install and start PostgreSQL. Create the development database and application role following the backend database setup documentation.
2. Set up the backend: create a Python virtual environment in `backend`, install `backend/requirements.txt`, copy `backend/.env.example` to `backend/.env`, and fill in local database/JWT/admin settings. Set `FRONTEND_ORIGIN=http://localhost:5173`.
3. Run database migrations from `backend` with `alembic upgrade head`. Create the administrator with `python scripts/create_admin.py`.
4. Start FastAPI from `backend`: `uvicorn app.main:app --reload`. The backend runs at <http://localhost:8000> and Swagger UI is at <http://localhost:8000/docs>.
5. Set up the React app from `frontend`: copy `.env.example` to `.env`, then run `npm install` and `npm run dev`. Open <http://localhost:5173>. Vite proxies `/api` to the local backend.

## AI assistant

The floating Daymark assistant is available to authenticated users and administrators. It uses OpenAI's official Python SDK and the `gpt-4o-mini` model (which supports tool calling). It can only access data through bounded, permission-checked backend tools; it does not generate SQL. Admin-only tools use the same role policy as the existing admin API. Task deletion and sensitive admin actions require a separate `yes`/`no` reply tied to the conversation and specific record.

1. In `backend/.env`, set `AI_PROVIDER=openai`, `AI_API_KEY` to a server-side OpenAI API key, and optionally change `AI_MODEL`. Never set the API key in the frontend environment.
2. Install backend dependencies with `pip install -r requirements.txt`, then run `alembic upgrade head` from `backend` to add the chat tables.
3. Start FastAPI and the frontend as described above. Without `AI_API_KEY`, chat requests return an explicit `503` configuration message; there is no keyword-matcher fallback.
4. Test with an authenticated user: open the floating assistant, ask it to list tasks, create a task, update a uniquely matched task, and request a deletion. Confirm the deletion only after the assistant identifies the task. Repeat as an administrator to test admin-only statistics and confirmations.

Conversations are owned by the authenticated account, retain at most 24 recent messages, and expire after 30 days (cleanup is lazy, when a new conversation is created). At most 20 conversations are retained per account. Destructive and sensitive actions require confirmation within 10 minutes. Requests are rate-limited to 20 per minute. Control provider costs by selecting an appropriate tool-capable model, keeping the key/project budget-limited in OpenAI, and monitoring usage. The default relative-date timezone is `Asia/Karachi`; set `DEFAULT_TIMEZONE` to an IANA timezone suitable for the deployment.

For package details, UI verification, deployment notes, and troubleshooting, see the [frontend README](./frontend/README.md). Backend commands require the Phase 1/2 files and PostgreSQL configuration to be present.
