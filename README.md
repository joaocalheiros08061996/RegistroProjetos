# Project Registry App

A FastAPI web application for managing projects, project tasks, routine activities, and dashboard metrics. The backend serves the API and the static frontend from the same service, while Supabase provides authentication and PostgreSQL storage.

## Features

- Email and password authentication through Supabase Auth.
- Project management with tasks, time tracking, priorities, complexity, and cost fields.
- Routine activity tracking with start and finish controls.
- Dashboard endpoints for project and routine activity metrics.
- Static frontend served by FastAPI under `/app`.
- Supabase import scripts for historical project data.
- Dockerfile ready for Render deployment.

## Requirements

- Python 3.12 or newer is recommended.
- A Supabase project with PostgreSQL and Auth enabled.
- A local `.env` file for development.
- Docker if you plan to run the app in a container or deploy it to Render with the included Dockerfile.

## Environment Variables

Create a `.env` file in the project root for local development. Never commit real credentials to GitHub.

```env
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_JWT_SECRET=<supabase-jwt-secret>
SUPABASE_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
```

Use the same Supabase project for all of these values. The `<project-ref>` in `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_ISSUER` must match.

### Why `SUPABASE_ISSUER` Matters

The app has two separate authentication steps:

1. `/auth/login` sends the email and password to Supabase using `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
2. Protected API routes validate the returned access token using `SUPABASE_ISSUER`, `SUPABASE_AUDIENCE`, and `SUPABASE_JWT_SECRET`.

If `SUPABASE_URL` points to one Supabase project but `SUPABASE_ISSUER` points to another project, login can still return `200 OK`, but protected routes such as `/projects/` and `/routine-activities/current` will return `401 Unauthorized`. The frontend handles `401` by clearing the token and redirecting to the login page, which looks like the app logs in and immediately sends the user back to login.

To avoid that issue, always set:

```env
SUPABASE_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
```

`SUPABASE_AUDIENCE` defaults to `authenticated` in the backend, but setting it explicitly in local and production environments makes deployment safer and easier to debug.

## Database Setup

Run the SQL schema files against your Supabase PostgreSQL database before using the app:

```text
infra/database/schema.sql
infra/database/schema_routine_activities.sql
```

You can execute them in the Supabase SQL editor or through any PostgreSQL client connected with `DATABASE_URL`.

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
uvicorn api.main:app --reload
```

If you use `uv`, you can run:

```bash
uv run uvicorn api.main:app --reload
```

Open the app:

```text
http://127.0.0.1:8000/app
```

Useful URLs:

```text
Frontend:       http://127.0.0.1:8000/app
Login page:     http://127.0.0.1:8000/app/login.html
API docs:       http://127.0.0.1:8000/docs
Root redirect:  http://127.0.0.1:8000/
```

## Application Flow

1. Create a user in the app or directly in Supabase Auth.
2. Log in with the user email and password.
3. Select one of the available modules:
   - Projects
   - Routine Activities
   - Dashboard
4. Data shown in the projects and routine activity modules is scoped by the logged-in Supabase user id.

## API Overview

Authentication:

```text
POST /auth/login
POST /auth/signup
```

Projects:

```text
GET    /projects/
POST   /projects/
GET    /projects/{project_id}
GET    /projects/{project_id}/detail
DELETE /projects/{project_id}
```

Tasks:

```text
GET    /projects/{project_id}/tasks/
POST   /projects/{project_id}/tasks/
GET    /projects/{project_id}/tasks/{task_name}
POST   /projects/{project_id}/tasks/{task_name}/start
POST   /projects/{project_id}/tasks/{task_name}/stop
POST   /projects/{project_id}/tasks/{task_name}/complete
DELETE /projects/{project_id}/tasks/{task_name}
GET    /projects/{project_id}/tasks/{task_name}/time-entries
```

Routine activities:

```text
POST /routine-activities/start
GET  /routine-activities/current
POST /routine-activities/finish-current
```

Dashboard:

```text
GET /dashboard/avg-real-days-by-project-type
GET /dashboard/avg-planned-vs-real-days-by-project-type
GET /dashboard/routine-total-days-by-month
GET /dashboard/project-monthly-kpis
```

All business endpoints require a valid Supabase access token in the `Authorization` header:

```text
Authorization: Bearer <access-token>
```

The frontend adds this header automatically after login.

## Tests

Run the full test suite:

```bash
pytest -q
```

With `uv`:

```bash
uv run pytest -q
```

Useful focused test commands:

```bash
uv run pytest tests/test_api_auth.py -q
uv run pytest tests/test_api_projects.py -q
uv run pytest tests/test_api_tasks.py -q
uv run pytest tests/test_api_routine_activities.py -q
uv run pytest tests/test_api_dashboard.py -q
uv run pytest tests/test_local_supabase_config.py -q
```

`tests/test_local_supabase_config.py` checks local Supabase configuration and helps catch the common login-success-but-protected-routes-return-401 problem before deployment.

## Importing Historical A3 Data

The script `automacoes/importar_a3_supabase.py` imports data from:

```text
A3 - Gerenciamento de Projetos.xlsx
```

The importer uses:

```env
DATABASE_URL=<supabase-postgres-url>
SUPABASE_USER_ID=<auth.users.id-owner-of-imported-data>
```

`SUPABASE_USER_ID` must be the real Supabase Auth user UUID from `auth.users.id`. It is not the Supabase project ref and it is not a password. Imported projects and tasks are scoped by this `user_id`, so users will only see imported data when they log in with the matching account.

Run a safe dry-run first:

```bash
uv run python automacoes/importar_a3_supabase.py --user-id <auth-user-uuid>
```

Then run the real import:

```bash
uv run python automacoes/importar_a3_supabase.py --user-id <auth-user-uuid> --commit
```

The importer writes:

```text
automacoes/import_a3_report.json
automacoes/import_a3_manifest.json
```

The manifest is used to avoid duplicating rows on future runs for the same user.

## Docker

Build the image:

```bash
docker build -t project-registry-app:latest .
```

Run locally with your `.env` file:

```bash
docker run --rm -p 8000:8000 --env-file .env project-registry-app:latest
```

Open:

```text
http://127.0.0.1:8000/app
```

The container listens on port `8000`.

## Deploying to Render

This repository includes a Dockerfile, so the recommended Render setup is a Docker Web Service.

1. Push the repository to GitHub.
2. Open Render and create a new Web Service.
3. Connect the GitHub repository.
4. Select Docker as the environment.
5. Let Render use the repository Dockerfile.
6. Add the production environment variables.
7. Deploy the service.

Required Render environment variables:

```env
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<supabase-anon-key>
SUPABASE_JWT_SECRET=<supabase-jwt-secret>
SUPABASE_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
```

Optional import-only variable:

```env
SUPABASE_USER_ID=<auth-users-id>
```

You usually do not need `SUPABASE_USER_ID` in Render for the web app. It is only used by import scripts.

After editing environment variables in Render, restart or redeploy the service so the new values are loaded.

## Deployment Checklist

Before deploying or switching Supabase projects, verify:

- `DATABASE_URL` points to the same Supabase project as `SUPABASE_URL`.
- `SUPABASE_ANON_KEY` belongs to the same Supabase project as `SUPABASE_URL`.
- `SUPABASE_JWT_SECRET` belongs to that same Supabase project.
- `SUPABASE_ISSUER` is exactly `https://<project-ref>.supabase.co/auth/v1`.
- `SUPABASE_AUDIENCE` is `authenticated`.
- Database schema files have been applied.
- The Render service has been restarted after environment variable changes.

## Troubleshooting

### Login works, but entering modules returns to login

This almost always means the login configuration and token verification configuration do not point to the same Supabase project.

Check these variables:

```env
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ISSUER=https://<project-ref>.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_JWT_SECRET=<jwt-secret-from-the-same-project>
```

Then restart the backend or redeploy Render.

You can also run:

```bash
uv run pytest tests/test_local_supabase_config.py -q
```

### Imported data does not appear in the app

Check which user owns the imported rows. Projects and tasks are filtered by the logged-in Supabase user id. If data was imported with the wrong `SUPABASE_USER_ID`, it may exist in the database but not appear for the user currently logged in.

### API returns `DATABASE_URL nao definida`

Set `DATABASE_URL` in `.env` locally or in the Render environment variables.

### Supabase Auth returns success but API returns `401 Unauthorized`

Set `SUPABASE_ISSUER` explicitly. Do not rely on a fallback issuer when changing Supabase projects.

## Security Notes

- Do not commit `.env` files or real Supabase credentials.
- Use Render environment variables for production secrets.
- Keep `SUPABASE_JWT_SECRET` private.
- Rotate Supabase keys if they were exposed.
