# Requirements — PyMigScore API

## Overview

**PyMigScore API** is a REST API for cloud migration assessment. Users upload a
system inventory (CSV), and the service scores each system's migration
complexity, groups them into migration waves, and estimates effort. The uploaded
file is stored in AWS S3, and all results are persisted in PostgreSQL. Results
can be retrieved, listed, and deleted later.

The project is designed to demonstrate:
**Python · FastAPI · REST API design · SQLAlchemy ORM · Docker · AWS (S3) · CI/CD**.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI |
| Templating | Jinja2 (FastAPI built-in support) |
| Database | PostgreSQL 16 + SQLAlchemy ORM |
| Validation | Pydantic v2 + pydantic-settings |
| Auth | JWT (PyJWT + passlib/bcrypt) |
| File storage | AWS S3 (boto3; moto for test mocks) |
| Containerisation | Docker + docker-compose |
| Testing | pytest + httpx |
| CI/CD | GitHub Actions |
| Linting | ruff |

---

## Functional Requirements

### Authentication

- User registration with `username`, `password`, and `password_repeat`.
  Passwords must match; duplicate usernames return `409`.
- User login accepts `username` and `password` (compatible with FastAPI's
  `OAuth2PasswordRequestForm`) and returns a JWT (HS256, 1-hour expiry).
- All endpoints except registration, login, dashboard, and health check
  require a valid JWT in the `Authorization: Bearer <token>` header.

### Assessments

- **Create**: Upload an inventory CSV (required, maximum 1,000 rows) and an optional `name` field.
  The CSV is parsed and validated first; after successful scoring, the file is uploaded to S3. Only if the S3 upload succeeds is the assessment committed to the database. If the DB commit fails, a compensating action is triggered to delete the orphaned file from S3. The assessment is owned by
  the authenticated user. Returns `201` with the complete result.
- **List**: Return all assessments belonging to the current user (summary view:
  id, name, created date, system count).
- **Detail**: Return the full assessment including all scored systems with
  their scores, wave assignments, and effort estimates.
- **Delete**: Remove an assessment and all its data. Only the owner may delete.
  Cascade-delete all related rows and delete the CSV file from S3.

### Dashboard

- A single-page HTML dashboard served by FastAPI at `GET /dashboard`.
- The page requires the user to log in via a simple form. The JWT is stored
  in the browser's `localStorage`.
- Once logged in, the page displays:
  - A list of the user's assessments (name, date, system count).
  - Clicking an assessment shows its scored systems in a table with columns:
    system name, type, composite score, complexity, cloud fit, risk, wave,
    and effort range.
- All data is fetched via vanilla JS `fetch()` calls to the existing API
  endpoints. No frontend framework.
- The page uses a single Jinja2 HTML template with embedded CSS and JS.

### Health

- A single health-check endpoint that confirms the service is running.

---

## API Endpoints

### Public (no auth required)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `POST` | `/auth/register` | `{username, password, password_repeat}` | `201 {user_id, username}` |
| `POST` | `/auth/login` | `{username, password}` (form data, OAuth2-compatible) | `200 {access_token, token_type}` |
| `GET` | `/health` | — | `200 {status: "ok"}` |
| `GET` | `/dashboard` | — | `200` HTML page (Jinja2 template) |

### Protected (JWT required)

| Method | Path | Request | Response |
|--------|------|---------|----------|
| `POST` | `/assessments` | Multipart: `inventory` CSV (required), `name` form field (opt) | `201` full assessment |
| `GET` | `/assessments` | — | `200` list of summaries |
| `GET` | `/assessments/{id}` | — | `200` full detail / `404` |
| `DELETE` | `/assessments/{id}` | — | `204` / `403` / `404` |

**Total: 8 endpoints** (4 public + 4 protected).

---

## Error Responses

All errors return JSON with an appropriate HTTP status code.

| Status | Meaning | Example |
|--------|---------|---------|
| `400` | Bad request / validation failure | Passwords don't match, malformed CSV |
| `401` | Unauthenticated | Missing or invalid JWT |
| `403` | Forbidden | Deleting another user's assessment |
| `404` | Not found | Assessment ID doesn't exist |
| `409` | Conflict | Registration with a taken login |
| `413` | File exceeds limit | CSV contains more than 1000 rows |
| `422` | Unprocessable entity | CSV rows fail Pydantic validation |

---

## CSV Schema

The inventory CSV uses the following columns:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `system_name` | String | Unique name of the system | `order-service` |
| `system_type` | Enum | Category of the system | `web_app`, `database`, `batch_job`, `file_server` |
| `operating_system` | Enum | OS the system runs on | `linux`, `windows` |
| `language` | Enum | Primary language / runtime | `python`, `java`, `dotnet`, `cobol`, `cpp` |
| `num_users` | Integer | Number of active users | `500` |
| `data_size_gb` | Float | Data volume in GB | `120.5` |
| `availability` | Enum | Availability requirement | `high`, `medium`, `low` |
| `has_compliance` | Boolean | Subject to regulatory compliance | `true`, `false` |
| `is_vendor_software` | Boolean | Indicates if the system is COTS | `true`, `false` |

---

## Data Model

### Users

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `username` | String | Unique, not null |
| `password_hash` | String | Not null |
| `created_at` | DateTime | Default: now (UTC) |

### Assessments

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `user_id` | Integer (FK) | → `users.id`, not null |
| `name` | String | Default: "Untitled" |
| `created_at` | DateTime | Default: now (UTC) |
| `system_count` | Integer | Not null |
| `s3_key` | String | S3 object key for the uploaded CSV |

### Scored Systems

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer (PK) | Auto-increment |
| `assessment_id` | Integer (FK) | → `assessments.id`, cascade delete |
| `system_name` | String | Not null |
| `system_type` | String | Not null |
| `composite_score` | Float | Not null |
| `complexity_score` | Float | Not null |
| `cloud_fit_score` | Float | Not null |
| `risk_score` | Float | Not null |
| `wave` | String | Not null |
| `recommended_strategy` | String | Not null |
| `effort_min` | Float | Not null |
| `effort_max` | Float | Not null |

---

## Domain Logic

| Module | Responsibility |
|--------|---------------|
| `loader.py` | Parse and validate the inventory CSV into `SystemInventory` Pydantic models; return structured errors with row numbers on failure |
| `scoring.py` | Compute `complexity_score`, `cloud_fit_score`, and `risk_score` for each system using hardcoded weights; derive a weighted `composite_score`; assign a migration wave (`quick_win`, `standard`, `complex`) based on score thresholds; estimate `effort_min` / `effort_max` in person-days |

### Strategy Assignment (The 6 Rs)

After calculating the base scores, `scoring.py` evaluates the system to assign a `recommended_strategy` using the following sequential logic:

1. **Retire (Decommission):** - **Condition:** If `num_users == 0`.
   - **Action:** Assign `Retire`. Override `wave` to `quick_win` and `effort` to `0-0`.
2. **Repurchase (Drop & Shop):** - **Condition:** If `is_vendor_software == true`.
   - **Action:** Assign `Repurchase`.
3. **Retain (Do Nothing):** - **Condition:** High risk and high complexity (e.g., `has_compliance == true` AND `language` in `[cobol, cpp]`).
   - **Action:** Assign `Retain`.
4. **Active Cloud Migrations:** For all remaining custom-built, active systems, evaluate based on scores:
   - **Rehost (Lift & Shift):** Low `complexity_score` + High `cloud_fit_score`.
   - **Replatform (Tinker & Shift):** Medium `complexity_score` + Medium/High `cloud_fit_score` (e.g., managed databases).
   - **Refactor (Rewrite):** High `complexity_score` + Low `cloud_fit_score`.

All domain models (`SystemInventory`, `ScoredSystem`, wave enum) are defined
as Pydantic v2 models in `app/schemas.py`.

### Scoring Rules

- **complexity_score** (0–10): Based on `language` difficulty + `system_type`
  complexity. Legacy languages (cobol, cpp) and batch jobs score higher.
- **cloud_fit_score** (0–10): Based on `operating_system` and `system_type`.
  Linux and web apps score higher (better cloud fit → lower migration effort).
- **risk_score** (0–10): Based on `num_users`, `data_size_gb`, `availability`,
  and `has_compliance`. More users / data / compliance → higher risk.
- **composite_score**: Weighted average of the three scores.

### Wave Assignment

| Wave | Composite Score Range |
|------|----------------------|
| `quick_win` | 0.0 – 3.9 |
| `standard` | 4.0 – 6.9 |
| `complex` | 7.0 – 10.0 |

---

## Configuration

All runtime config is read from environment variables via `pydantic-settings`:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@db:5432/pymig` |
| `SECRET_KEY` | Yes | JWT signing key | `change-me-in-production` |
| `ALLOWED_ORIGINS` | No | CORS origins (comma-separated) | `http://localhost:3000` |
| `AWS_ACCESS_KEY_ID` | No | S3 credentials | — |
| `AWS_SECRET_ACCESS_KEY` | No | S3 credentials | — |
| `AWS_REGION` | No | AWS region (default: `eu-west-1`) | `eu-west-1` |
| `AWS_BUCKET_NAME` | No | S3 bucket name | `pymig-uploads` |
| `AWS_ENDPOINT_URL` | No | LocalStack URL for local dev | `http://localstack:4566` |

---

## Testing Strategy

- **Framework**: pytest + FastAPI `TestClient` (via httpx) + testcontainers-python (for spinning up
  ephemeral PostgreSQL containers).
- **Database**: Test-scoped PostgreSQL 16 instance via Testcontainers. This ensures 100% environment
  parity with production, strictly enforcing SQL dialects and constraints.
- **S3 mocking**: `moto` mocks S3 in unit tests.
- **Fixtures** (`conftest.py`):
  - `db` — initializes the Testcontainers PostgreSQL engine, creates all tables viaBase.metadata.create_all(), yields a session, and drops/rolls back after the test suite finishes.
  - `client` — `TestClient` with overridden `get_db`.
  - `auth_client` — pre-registered and logged-in user with JWT in headers.
  - `sample_inventory_csv` — temporary CSV file with valid test data.
- **Coverage targets**: All endpoints, all error paths, all service functions.
- **Linting**: `ruff check .` as part of the CI workflow.

---

## Implementation Notes

1. All API responses are JSON. The dashboard is the only HTML response.
2. JWT is stateless — no server-side token revocation; 1-hour expiry.
3. Database schema is created via `Base.metadata.create_all()` on startup.
4. CSV validation errors are returned as structured JSON with row numbers and
   field names — not generic 500 errors.
5. Distributed Transaction Safety: To prevent orphaned files, the CSV upload
   process follows a strict order: (1) Validate & score in-memory, (2) Upload to S3, (3)
   Commit to DB. If the database commit fails (e.g., due to a network error or constraint violation), the backend catches the exception, synchronously calls delete_file() on S3 for that specific key, and returns a 500 error to the client.
6. On assessment deletion, the S3 object is deleted alongside the DB rows.
7. Scoring weights are hardcoded constants — no external config files.
8. The dashboard is a single Jinja2 template (`dashboard.html`) with embedded
   `<style>` and `<script>` tags.
9. SQLAlchemy ORM models use a `Model` suffix (e.g., `UserModel`,
   `AssessmentModel`) to avoid naming collisions with Pydantic schemas.
10. S3 operations are encapsulated in `app/s3.py` — a thin wrapper around
    boto3 providing `upload_file()` and `delete_file()` functions.
11. The backend enforces 1000 row limit to prevent synchronous processing timeouts
    and memory exhaustion. Files exceeding the limit are rejected.
12. Test Execution: Because tests require a real PostgreSQL engine, the test suite will use
    testcontainers to automatically pull and spin up a lightweight postgres:16-alpine Docker container when pytest is executed.
