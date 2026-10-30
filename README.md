# Task Management API

REST API for managing tasks, built with FastAPI and PostgreSQL.

Users can register, create tasks, assign them to other users, move them through statuses, leave comments and search the task list. Overdue tasks are cancelled automatically by a background check.

Stack: FastAPI, SQLAlchemy (async), PostgreSQL, Alembic, Pydantic, Docker Compose, Pytest.

## Run

```bash
cp .env.example .env
docker compose up --build
```

Migrations run on start. The API is available at http://localhost:8000, Swagger at http://localhost:8000/docs.

To try the endpoints in Swagger, register a user with `POST /auth/register`, then press **Authorize** and log in with the username and password.

## Tests

Tests use a separate database from the `test_db` service.

```bash
docker compose up -d test_db
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Lint and format:

```bash
ruff check .
ruff format .
```

## Endpoints

| Method | URL | Description |
|---|---|---|
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Get a JWT access token |
| GET | `/users/me` | Current user |
| GET | `/users` | All users |
| POST | `/tasks` | Create a task |
| GET | `/tasks` | Task list with search, filters, sorting and pagination |
| GET | `/tasks/overdue` | Overdue tasks |
| GET | `/tasks/stats` | Task statistics |
| GET | `/tasks/{task_id}` | Get a task |
| PATCH | `/tasks/{task_id}` | Edit a task |
| PATCH | `/tasks/{task_id}/status` | Change task status |
| DELETE | `/tasks/{task_id}` | Delete a task |
| POST | `/tasks/{task_id}/comments` | Add a comment |
| GET | `/tasks/{task_id}/comments` | Comments of a task |

All endpoints except register, login and `/health` need a token.

`GET /tasks` query parameters:

- `search` - text in title or description
- `status`, `priority`, `assignee_id` - can be passed several times, for example `?status=backlog&status=review`
- `deadline_from`, `deadline_to` - deadline range
- `sort_by` - `created_at`, `deadline` or `priority`, with `order` - `asc` or `desc`
- `page`, `size` - pagination, size from 1 to 100

Without `sort_by` tasks are sorted by priority (high, medium, low), then by nearest deadline.

Errors have the same format:

```json
{"detail": "Task is closed for editing", "code": "task_closed"}
```

## Status transitions

```
backlog -> in_progress -> review -> done
backlog -> cancelled
in_progress -> cancelled
```

Any other change, including going back, returns 409.

## Assumptions

Some points in the task are not fully defined, so I made these decisions:

- **Active tasks.** The task mentions a Todo status that is not in the list of statuses. Active statuses are In Progress and Review.
- **Active tasks limit.** The limit of 10 active tasks is counted for the assignee. It is checked when a task moves to an active status and when an active task gets a new assignee. The assignee row is locked with `SELECT ... FOR UPDATE` so parallel requests cannot go over the limit.
- **Review -> Cancelled.** Not allowed for users, because it is not in the list of allowed transitions.
- **Background task and Review.** The background check is a system action, so it cancels overdue tasks in Backlog, In Progress and Review.
- **Permissions.** Only the author can edit or delete a task. The author or the assignee can change the status. Any logged in user can view tasks and comments and add comments.
- **Deadline.** Optional. If set, it must be in the future. A deadline without timezone is treated as UTC.
- **Login.** By username, because the OAuth2 password form uses the `username` field.

## Background task

The overdue check runs as an asyncio task started in the app lifespan. Every `OVERDUE_CHECK_INTERVAL_SECONDS` it moves tasks with a passed deadline that are not done or cancelled to Cancelled. It can be turned off with `OVERDUE_CHECK_ENABLED=false`.

FastAPI `BackgroundTasks` run once after a response, so they cannot be used for a periodic check.

The check runs inside the app process. If the app is started with several workers, each worker runs its own check. The update is safe to run twice, but to run it only once a `pg_try_advisory_lock` can be added around it.

## Configuration

| Variable | Description |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Database for the `db` service |
| `DATABASE_URL` | Connection string for the app |
| `JWT_SECRET` | Secret for signing tokens |
| `JWT_EXPIRE_MINUTES` | Token lifetime |
| `OVERDUE_CHECK_ENABLED` | Turn the overdue check on or off |
| `OVERDUE_CHECK_INTERVAL_SECONDS` | How often the overdue check runs |
| `TEST_DATABASE_URL` | Test database, defaults to the `test_db` service |
