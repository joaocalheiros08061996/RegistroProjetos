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

# Recommended for signed app session cookies.
AUTH_SESSION_SIGNING_SECRET=<random-secret>
APP_ALLOWED_ORIGINS=https://<your-render-service>.onrender.com

# Optional, only needed for app-stored secrets.
DATA_ENCRYPTION_ACTIVE_KEY_ID=primary
DATA_ENCRYPTION_KEYS=primary:<fernet-key>

# Required for privacy notice acknowledgement audit.
PRIVACY_CONTROLLER_NAME=<controller-name>
PRIVACY_CONTACT_EMAIL=<privacy-contact-email>
PRIVACY_POLICY_VERSION=2026-06-01
PRIVACY_AUDIT_HASH_SECRET=<random-secret>
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
infra/database/migration_add_auth_privacy_acknowledgements.sql
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
uvicorn api.main:app --reload --no-server-header
```

If you use `uv`, you can run:

```bash
uv run uvicorn api.main:app --reload --no-server-header
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
POST /auth/refresh
POST /auth/logout
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

For a direct production-style Uvicorn start outside Docker, disable the default
stack-identifying header:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-server-header
```

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
AUTH_SESSION_SIGNING_SECRET=<random-secret>
APP_ALLOWED_ORIGINS=https://<your-render-service>.onrender.com
```

Generate `AUTH_SESSION_SIGNING_SECRET` locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Optional encryption variables for future app-stored secrets:

```env
DATA_ENCRYPTION_ACTIVE_KEY_ID=primary
DATA_ENCRYPTION_KEYS=primary:<fernet-key>
```

Generate a Fernet key locally with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Required privacy notice variables:

```env
PRIVACY_CONTROLLER_NAME=<controller-name>
PRIVACY_CONTACT_EMAIL=<privacy-contact-email>
PRIVACY_POLICY_VERSION=2026-06-01
PRIVACY_AUDIT_HASH_SECRET=<random-secret>
```

Generate `PRIVACY_AUDIT_HASH_SECRET` locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
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
- `AUTH_SESSION_SIGNING_SECRET` is configured and stored only in Render environment variables.
- `APP_ALLOWED_ORIGINS` contains the public HTTPS URL of the Render service.
- Privacy notice variables are configured, and `PRIVACY_AUDIT_HASH_SECRET` is stored only in Render environment variables.
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
- Keep `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `SUPABASE_ANON_KEY`, and `DATA_ENCRYPTION_KEYS` private.
- Do not log `Authorization`, cookies, `DATABASE_URL`, tokens, passwords, API keys, or full authentication payloads.
- Rotate Supabase keys if they were exposed.
- Production requests received through Render with `X-Forwarded-Proto: http` are redirected to HTTPS by the app. Local development remains HTTP-friendly.
- Security headers are added globally by the app, including HSTS in production, content-type protection, frame denial, referrer policy, permissions policy, and a CSP compatible with the current frontend.
- The application removes `Server` and `X-Powered-By` when they are present in app responses. Docker also starts Uvicorn with `--no-server-header`.
- Plotly remains loaded from `https://cdn.plot.ly`; the CSP permits that origin and keeps `'unsafe-eval'` only for Plotly compatibility. Application-owned JavaScript must stay in external files.

### Staging Header Checklist

After each security-header change, verify the deployed staging service before
promoting it to production:

```bash
curl -sSI https://<staging-host>/app/login.html
curl -sSI https://<staging-host>/missing-route
curl -sSI -H "X-Forwarded-Proto: http" http://<staging-host>/app/login.html
```

Confirm that HTTPS responses include `Strict-Transport-Security`,
`Content-Security-Policy`, `Permissions-Policy`, `X-Content-Type-Options`,
`X-Frame-Options`, and `Referrer-Policy`. Confirm that HTTP redirects to HTTPS
and that neither `Server` nor `X-Powered-By` is exposed. Headers added by the
Render proxy must be checked at this deployed boundary because the app cannot
remove headers appended after its response leaves the container.

Finally, open login, projects, and each Plotly dashboard in staging and check the
browser console for CSP violations.

### Sessions, Cookies, and CSRF

- Supabase remains responsible for issuing access and refresh tokens. Business API routes use `Authorization: Bearer <access-token>`, so browser cookies are not used to authorize project, task, routine, or dashboard changes.
- Refresh tokens are stored only in an `HttpOnly`, `SameSite=Lax` cookie. In production the cookie is also `Secure`.
- The app issues a second signed `HttpOnly` cookie with an opaque session id, initial issue time, last refresh time, and a hash of the refresh token. A new id is generated after login, signup, and each successful refresh.
- `/auth/refresh` rejects missing, modified, inactive, or absolutely expired session cookies. Defaults are 8 hours of refresh inactivity and 30 days absolute lifetime. Override with `AUTH_SESSION_IDLE_TIMEOUT_SECONDS` and `AUTH_SESSION_ABSOLUTE_TIMEOUT_SECONDS`.
- Authentication POST routes reject cross-site browser requests using `Origin`, `Referer`, and `Sec-Fetch-Site` when those headers are present. Configure production origins with `APP_ALLOWED_ORIGINS`.
- `/auth/logout` clears both cookies and attempts Supabase revocation with the current access token. A stolen access token may remain valid until its short JWT expiration; use short access-token lifetime in Supabase and revoke affected sessions in Supabase after password changes or suspected compromise.

### Input Validation and Output Encoding

- JSON write endpoints use Pydantic DTOs with unknown fields rejected, trimmed text fields, bounded lengths, non-negative costs, and bounded integer FTE values.
- Repository SQL remains parameterized. Names containing SQL-like text are stored and queried as data.
- Dynamic frontend values rendered through HTML templates are escaped, and dynamic URL parameters are encoded before concatenation.
- The web app has no file-upload endpoint. Local Excel, CSV, and JSON automation inputs are checked for allowed extension, existence, regular-file type, and size before opening. Override the default 50 MB limit with `AUTOMACAO_MAX_INPUT_FILE_BYTES`.
- The API does not accept XML and does not fetch user-provided URLs. XXE and SSRF are therefore outside the current web surface. File paths exist only in local CLI automation arguments, where validation occurs before opening.

### Data Encryption and Backups

Supabase provides managed PostgreSQL storage; use Supabase controls for database-level encryption, access, and backup retention. The app also includes a Fernet-based helper for secrets that may be stored by future features. Its payload format is `v1:<key_id>:<ciphertext>`, and old keys can remain in `DATA_ENCRYPTION_KEYS` while `DATA_ENCRYPTION_ACTIVE_KEY_ID` points to the new key.

Current project/task/routine operational fields are not encrypted at the application layer because dashboards filter and group by those values. If future features store tokens, API keys, integration secrets, or similar values in database tables, encrypt them with the helper before persistence.

Test backups periodically in a separate environment. At minimum, record the backup date, restore target, verification steps, and result after each monthly or quarterly restore drill.

### Privacy Notice and LGPD

- New registrations require explicit acknowledgement that the user has read the Privacy Notice at `/app/privacy.html`.
- The acknowledgement audit stores the policy version, timestamp, user id, and HMAC-SHA256 hashes of email and IP. It does not store raw email or IP in the audit table.
- Apply `infra/database/migration_add_auth_privacy_acknowledgements.sql` before deploying this feature. If the audit insert fails after Supabase creates an account, the app returns `503` and does not issue authentication cookies.
- The acknowledgement covers transparency for essential internal use. Optional future purposes must be presented separately and, when consent is the applicable legal basis, support facilitated revocation.
- This implementation supports LGPD operations but does not replace legal review or the internal process for handling data-subject requests through `PRIVACY_CONTACT_EMAIL`.
- Official references: [compiled LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) and [ANPD data-subject rights](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares).

Existing accounts can be registered honestly as legacy pending records, without fabricating retroactive acknowledgement. Prepare a local CSV with `user_id,email`, run dry-run first, then commit:

```bash
uv run python automacoes/registrar_privacidade_legado_supabase.py \
  --csv usuarios_legados.csv \
  --reason "Usuarios existentes antes da publicacao do aviso"

uv run python automacoes/registrar_privacidade_legado_supabase.py \
  --csv usuarios_legados.csv \
  --reason "Usuarios existentes antes da publicacao do aviso" \
  --commit
```
