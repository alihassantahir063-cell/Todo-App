# Daymark frontend

React + Vite single-page frontend for the Todo Management API. All user, task, and administrator data is loaded from the configured backend; the frontend does not ship mock accounts or sample statistics. Authentication remains in the backend's HttpOnly cookie—this app never stores an access token.

## Requirements

- Node.js 20.19+ or 22.12+
- npm
- The FastAPI backend and PostgreSQL database from project phases 1 and 2

## Install and run

From this `frontend` directory:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open <http://localhost:5173>. By default, Vite proxies `/api` requests to `http://localhost:8000`, avoiding cross-origin cookie issues in development. For a backend listening on a different local port, set the Vite process variable `VITE_API_PROXY_TARGET` (for example, `http://localhost:8001`). Change `VITE_API_URL` in `.env` only when the backend is hosted at another API base URL. Do not put credentials or tokens in Vite variables.

Useful commands:

```powershell
npm run build
npm run preview
```

The production build is written to `dist/`. Deploy it behind HTTPS and configure the API URL and backend CORS/cookie settings for the deployed origins.

## Full project startup order

1. Install PostgreSQL, start its service, and create the development database/user as described in the database section of the backend README.
2. In `backend`, create and activate a Python virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and set `DATABASE_URL`, a development `SECRET_KEY`, and `FRONTEND_ORIGIN=http://localhost:5173`.
3. From `backend`, apply migrations with `alembic upgrade head`. Create the first administrator with `python scripts/create_admin.py` after setting the `ADMIN_*` values in the backend `.env`.
4. Start the API from `backend`: `uvicorn app.main:app --reload`. API base URL: <http://localhost:8000/api>; Swagger UI: <http://localhost:8000/docs>.
5. In `frontend`, install packages and start Vite with `npm install` and `npm run dev`. Frontend URL: <http://localhost:5173>.

Development browser requests use the Vite proxy, but the backend must still allow credentialed requests from the frontend origin if you set `VITE_API_URL` to an absolute URL. Production deployments must use HTTPS when backend `COOKIE_SECURE=true`.

## Manual verification checklist

Use a fresh browser profile for the second user so the task ownership check is meaningful.

### User flow

- [ ] Register a first account at `/register`, then sign in at `/login`.
- [ ] Create a task, edit its title/details, and delete it after confirming the dialog.
- [ ] Complete a task with its checkbox, reopen it, reload the page, and confirm the persisted status.
- [ ] Search tasks; filter by status and priority; sort by creation date, due date, and priority; move between pages.
- [ ] Update the profile name/email, then change the password using the current password.
- [ ] Request a password reset from the sign-in page, use the email link within 30 minutes, and confirm it cannot be reused. The same flow works for administrator accounts.
- [ ] In profile settings, generate a recovery code with the current password, save it securely, sign out, and verify that the recovery-code option resets the password without email. Confirm a code cannot be reused or used after generating a replacement.
- [ ] Allow browser notifications in profile settings, create a task with a due date, and verify a reminder is shown at 9:00 AM local time. Test a custom reminder time, completion before the reminder, and that the same scheduled reminder is not shown twice.
- [ ] Sign out. Confirm you return to the login page and a protected route sends you back to login.
- [ ] Create/sign in as a second user and confirm that user's task list does not contain the first user's task.

### Administrator flow

- [ ] Sign in with the administrator bootstrapped by the backend's `create_admin.py`.
- [ ] Confirm the dashboard totals and latest records reflect real database data.
- [ ] Find a user and deactivate them. Confirm the user is no longer able to authenticate; reactivate them as needed for subsequent testing.
- [ ] Delete a task in Admin → All tasks.
- [ ] Sign in as a regular user and visit `/admin`; confirm the Access Denied screen appears.

The backend remains the security boundary: client-side route guards are for navigation only.

## AI assistant configuration

The floating assistant is available from both authenticated workspaces. It uses OpenRouter's OpenAI-compatible tool-calling API; the browser only calls `/api/chat/message` and never receives provider credentials.

- Configure `AI_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, `AI_MODEL` (default `openrouter/free`), `AI_TIMEOUT_SECONDS`, and `DEFAULT_TIMEZONE` in `backend/.env`. The backend accepts the free router or a specific model ID ending in `:free`; paid model IDs are rejected. The free router does not fall back to paid models, and model availability/rate limits can vary.
- Install `backend/requirements.txt` and run `alembic upgrade head` from `backend` to create the conversation tables.
- If `OPENROUTER_API_KEY` is absent, the API reports a configuration error; no fake responses are generated.
- User tools are scoped to the signed-in account. Admin tools are available only to administrators and follow the same role policy as the admin API. Deletions and sensitive admin changes require a separate yes/no confirmation tied to the conversation and selected record.
- Conversations belong to the signed-in account, retain at most 24 recent messages, expire after 30 days, and are capped at 20 per account. Clearing the chat deletes its server-side conversation. Pending confirmations expire after 10 minutes.
- The backend limits chat calls to 20 per minute. `DEFAULT_TIMEZONE` defaults to `Asia/Karachi` and must be a valid IANA timezone. Configure provider-side budgets and monitor usage.

## Troubleshooting

- **Cookie not saved:** use the Vite `/api` proxy in development, keep Axios `withCredentials` enabled, and verify the backend sets `SameSite=Lax`, `Path=/`, and `Secure=false` for local HTTP. In production, use HTTPS and set `COOKIE_SECURE=true`.
- **CORS error:** use the development proxy, or set the backend `FRONTEND_ORIGIN` to the exact frontend origin (including scheme and port). Credentialed CORS cannot use a wildcard origin.
- **401 loop / unexpected sign-out:** confirm the backend cookie is present in browser storage, the API URL points at the same backend that issued it, and the backend signing key has not changed. Login's own 401 response is intentionally shown as a form error.
- **Proxy not working:** start the API on `http://localhost:8000`, restart Vite after changing `vite.config.js`, and inspect the browser Network panel for `/api/...` requests.
- **Blank page:** inspect the browser console, verify Node/npm versions, run `npm install` and `npm run build`, and confirm the backend endpoints return the documented response shapes.
