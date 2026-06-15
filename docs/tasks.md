# Implementation Plan

## Summary

- **Total phases**: 6
- **Total tasks**: 19
- **Estimated complexity**: Medium

---

## Dependencies

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10
                                    T8 → T11 → T12 → T13
                          T6 → T14 → T15
T10, T13, T15 → T16 → T17 → T18 → T19
```

---

## Phase 1: Project Setup

**Goal**: The project can be cloned, `docker compose up` brings it up, and a health check returns 200.

---

### Task 1: Docker & Dependency Files

**Context:** Before writing any application code, you need the files that let you install dependencies and run the app locally inside Docker. Think of this as setting up the workspace.

**Build:**
1. Create `pyproject.toml` — list all packages the app needs to run: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `pydantic-settings`, `python-multipart`, `boto3`, `PyJWT`, `passlib[bcrypt]`. Also list dev-only tools: `pytest`, `httpx`, `moto[s3]`, `ruff`.
2. Create `Dockerfile` — installs the packages from `pyproject.toml` and starts the app with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
3. Create `docker-compose.yml` — defines two containers: `app` (your FastAPI app, port 8000) and `db` (PostgreSQL 16, with a database name, user, and password set via environment variables).
4. Create `.env.example` — a template file listing every environment variable the app needs, with placeholder values: `DATABASE_URL`, `SECRET_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME`, `AWS_ENDPOINT_URL`, `SMTP_HOST`.

**Verify:**
```bash
docker compose build
# Expected: exits 0 with no errors
```

---

### Task 2: App Skeleton & Config

**Context:** You need the simplest possible working FastAPI app — just enough to confirm the server starts and responds. You also need a settings module so the app reads its configuration from environment variables instead of having values hardcoded.

**Build:**
1. Create `app/config.py` — define a `Settings` class using `pydantic-settings` that reads `DATABASE_URL`, `SECRET_KEY`, and `AWS_*` from the environment. Create one shared instance at module level: `settings = Settings()`. Other files will import this `settings` object instead of reading env vars directly.
2. Create `app/main.py` — create a `FastAPI()` app instance and add a single `GET /health` route that returns `{"status": "ok"}`.

**Verify:**
```bash
docker compose up --build -d
curl -s http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

### Task 3: Database Models & Session

**Context:** The app stores data in four database tables: `users`, `projects`, `project_access` (tracks who has access to which project and with what role), and `documents`. You need to define these tables as Python classes using SQLAlchemy ORM, and create a way to get a database connection in your route handlers. The schema will be created automatically when the app starts — no migration tool needed.

**Build:**
1. Create `app/models.py` — write four SQLAlchemy model classes:
   - `User`: columns `id` (primary key), `login` (unique string), `password_hash` (string).
   - `Project`: columns `id`, `name`, `description`, `storage_bytes` (integer, default 0).
   - `ProjectAccess`: columns `project_id` (foreign key → projects, cascade delete), `user_id` (foreign key → users, cascade delete), `role` (string: `"owner"` or `"participant"`).
   - `Document`: columns `id`, `project_id` (foreign key → projects, cascade delete), `filename`, `s3_key`, `size_bytes`.
2. Create `app/dependencies.py` — set up the SQLAlchemy engine using `settings.DATABASE_URL`, create a `SessionLocal` session factory, and write a `get_db` function that FastAPI can use as a dependency to open and close a DB session per request.
3. In `app/main.py`, add a `lifespan` function that calls `Base.metadata.create_all(bind=engine)` on startup so all tables are created automatically.

**Verify:**
```bash
docker compose up --build -d
docker compose exec db psql -U postgres -d appdb -c "\dt"
# Expected: four tables listed: users, projects, project_access, documents
```

---

### Task 4: Pydantic Schemas

**Context:** FastAPI uses Pydantic models to validate what comes in (request bodies) and control what goes out (response bodies). You need to define all the shapes of data the API will accept and return — all in one file to keep things simple. The schemas also need to work when built from SQLAlchemy ORM objects.

**Build:**
1. Create `app/schemas.py` — define the following Pydantic classes:
   - Auth: `RegisterIn` (fields: login, password, password_repeat), `LoginIn` (login, password), `TokenOut` (access_token, token_type), `UserOut` (id, login).
   - Projects: `ProjectIn` (name, description), `ProjectOut` (id, name, description, storage_bytes), `ProjectUpdateIn` (name and description are both optional — allow partial updates).
   - Documents: `DocumentOut` (id, project_id, filename, size_bytes).
2. Add `model_config = ConfigDict(from_attributes=True)` to every class — this lets Pydantic build a schema object directly from a SQLAlchemy model instance.

**Verify:** `tests/test_schemas.py`
- `test_register_in_valid`
- `test_register_in_rejects_missing_fields`
- `test_project_out_from_orm_object`
- `test_document_out_from_orm_object`

---

## Phase 2: Authentication

**Goal**: Users can register and receive a JWT they can use on all subsequent requests.

---

### Task 5: Auth Utilities

**Context:** Before building the login/register endpoints, you need the basic building blocks: a way to hash passwords so they're not stored in plain text, and a way to create and verify JWT tokens. Put these as plain functions in a utility file so they can be imported anywhere and tested on their own without starting the server.

**Build:**
1. Create `app/utils/auth.py` with four functions:
   - `hash_password(plain: str) -> str` — hashes a plain-text password using bcrypt. Returns the hashed string.
   - `verify_password(plain: str, hashed: str) -> bool` — checks if a plain-text password matches a stored hash.
   - `create_token(data: dict, expires_in: int = 3600) -> str` — creates a signed JWT with the given payload plus an `exp` claim set to now + `expires_in` seconds. Uses `settings.SECRET_KEY` and HS256 algorithm.
   - `decode_token(token: str) -> dict` — verifies and decodes a JWT. Raises `HTTPException(401)` if the token is invalid or expired.

**Verify:** `tests/test_utils_auth.py`
- `test_hash_and_verify_password`
- `test_wrong_password_fails`
- `test_create_and_decode_token`
- `test_decode_expired_token_raises_401`
- `test_decode_invalid_token_raises_401`

---

### Task 6: Register Endpoint — `POST /auth`

**Context:** This is the first real endpoint — it lets a new user create an account. The request includes a login name, a password, and the password repeated. You need to validate the input, make sure the login isn't already taken, hash the password, and save the user to the database.

**Build:**
1. Create `app/routers/auth.py` with a `POST /auth` route:
   - Accept a `RegisterIn` body.
   - If the two passwords don't match, raise `HTTPException(400)`.
   - Check the database for an existing user with the same login. If found, raise `HTTPException(409)`.
   - Hash the password using `hash_password` from `utils/auth.py`.
   - Create a `User` model, add it to the DB session, commit, and return the new user as `UserOut` with status `201`.
2. Register the auth router in `app/main.py` with `app.include_router(auth_router)`.

**Verify:** `tests/test_auth.py`
- `test_register_returns_201`
- `test_register_duplicate_login_returns_409`
- `test_register_password_mismatch_returns_400`

---

### Task 7: Login Endpoint & Auth Dependency — `POST /login`

**Context:** Users need to log in and get a JWT token they'll send with every protected request. You also need a reusable FastAPI dependency that any protected route can use to check who's making the request — it reads the token from the request header, decodes it, and returns the user.

**Build:**
1. Add `POST /login` to `app/routers/auth.py`:
   - Accept a `LoginIn` body.
   - Look up the user by login. If not found, raise `HTTPException(401)`.
   - Verify the password. If wrong, raise `HTTPException(401)`.
   - Call `create_token({"sub": str(user.id)})` and return the result as `TokenOut` with status `200`.
2. Add `get_current_user` to `app/dependencies.py`:
   - It takes a token from the `Authorization: Bearer <token>` header using `OAuth2PasswordBearer`.
   - Calls `decode_token(token)` to get the payload.
   - Reads `payload["sub"]` as the user ID and looks up the user in the database.
   - If the user is not found, raises `HTTPException(401)`.
   - Returns the `User` object. Route handlers will use `Depends(get_current_user)` to get the logged-in user.

**Verify:** `tests/test_auth.py`
- `test_login_returns_token`
- `test_login_wrong_password_returns_401`
- `test_login_unknown_user_returns_401`
- `test_protected_route_without_token_returns_401`

---

## Phase 3: Project Endpoints

**Goal**: All project management routes work — create, list, read, update, delete, and invite.

---

### Task 8: Create & List Projects

**Context:** Users need to create projects and see a list of projects they have access to. When a project is created, the creator automatically becomes its owner — that's stored as a row in the `project_access` table. Listing should only return projects where the current user has a row in `project_access`, not all projects in the database.

**Build:**
1. Create `app/routers/projects.py` with two routes (both require `get_current_user`):
   - `POST /projects`: accept `ProjectIn`. Insert a new `Project` row. Insert a `ProjectAccess` row for the current user with `role="owner"`. Return the project as `ProjectOut` with status `201`.
   - `GET /projects`: query all projects that have a `ProjectAccess` row where `user_id` equals the current user's id. Return as `list[ProjectOut]` with status `200`.
2. Register the projects router in `app/main.py`.

**Verify:** `tests/test_projects.py`
- `test_create_project_returns_201`
- `test_create_project_adds_owner_role`
- `test_list_projects_returns_only_accessible`
- `test_list_projects_unauthenticated_returns_401`

---

### Task 9: Get & Update Project Info

**Context:** Users need to read a project's details and update its name or description. Both the owner and participants can do this. Before returning or updating anything, you need to check two things: does the project exist (404 if not), and does the current user have a row in `project_access` for it (403 if not).

**Build:**
1. Add `GET /project/{project_id}/info` to `app/routers/projects.py`:
   - Look up the project by id. Raise `HTTPException(404)` if not found.
   - Check that there is a `ProjectAccess` row for this project and the current user. Raise `HTTPException(403)` if none.
   - Return `ProjectOut` with status `200`.
2. Add `PUT /project/{project_id}/info`:
   - Same access checks as above.
   - Accept a `ProjectUpdateIn` body. Update only the fields that were provided (name and/or description).
   - Commit and return the updated project as `ProjectOut` with status `200`.

**Verify:** `tests/test_projects.py`
- `test_get_project_info_as_owner`
- `test_get_project_info_as_participant`
- `test_get_project_info_no_access_returns_403`
- `test_get_project_info_not_found_returns_404`
- `test_update_project_info_returns_updated`
- `test_update_project_info_no_access_returns_403`

---

### Task 10: Delete Project

**Context:** Only the project owner can delete a project. Deleting a project must also clean up all its files stored in AWS S3 — otherwise you'd be paying for files that are no longer reachable. After S3 cleanup, deleting the `Project` row from the database is enough; the cascade rules set up in Task 3 will automatically remove related `project_access` and `documents` rows.

**Build:**
1. Add `DELETE /project/{project_id}` to `app/routers/projects.py`:
   - Look up the `ProjectAccess` row for the current user. If the role is not `"owner"`, raise `HTTPException(403)`.
   - Query all `Document` rows for this project. For each one, call `s3.delete_file(doc.s3_key)` — wrap this in a try/except so an S3 error doesn't block the deletion in dev/test environments.
   - Delete the `Project` row from the database and commit. The cascade handles the rest.
   - Return an empty response with status `204`.

**Verify:** `tests/test_projects.py`
- `test_delete_project_as_owner_returns_204`
- `test_delete_project_as_participant_returns_403`
- `test_delete_project_removes_from_db`

---

### Task 11: Invite User — `POST /project/<id>/invite`

**Context:** An owner can invite another registered user to their project by typing that user's login name. Once invited, the user gets `participant` access — they can read and update the project, but not delete it. If the target user doesn't exist or the caller is not the owner, return an error. Inviting someone who is already a participant should not cause an error.

**Build:**
1. Add `POST /project/{project_id}/invite` to `app/routers/projects.py`. The invited login comes in as a query parameter: `?user=<login>`.
   - Check the caller's role is `"owner"`. Raise `HTTPException(403)` if not.
   - Look up the target user by login. Raise `HTTPException(404)` if they don't exist.
   - Check if a `ProjectAccess` row already exists for that user and this project. If it does, do nothing. If it doesn't, insert one with `role="participant"`.
   - Return status `200`.

**Verify:** `tests/test_projects.py`
- `test_invite_user_grants_participant_role`
- `test_invite_nonexistent_user_returns_404`
- `test_invite_as_participant_returns_403`
- `test_invite_idempotent`

---

## Phase 4: Document Endpoints

**Goal**: Users can upload, download, update, and delete project documents stored in S3.

---

### Task 12: S3 Utilities

**Context:** Documents are stored in AWS S3, not on the server's disk. You need helper functions to upload a file, delete a file, and generate a temporary download link (called a presigned URL). These go in a utility file so the document routes can call them without dealing with boto3 (the AWS library) directly. For local development, the app will connect to LocalStack — a local fake AWS — instead of the real thing.

**Build:**
1. Create `app/utils/s3.py`:
   - Write `get_s3_client()` — creates and returns a boto3 S3 client using `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optionally `AWS_ENDPOINT_URL` (used to point at LocalStack in dev).
   - Write `upload_file(project_id: int, filename: str, file_obj, content_type: str) -> tuple[str, int]` — generates a unique S3 key in the format `projects/{project_id}/{uuid}_{filename}`, uploads the file, and returns the key and file size in bytes.
   - Write `delete_file(s3_key: str) -> None` — deletes the object at the given key.
   - Write `presign_url(s3_key: str, expires: int = 900) -> str` — generates and returns a temporary signed download URL that expires in `expires` seconds (default 15 minutes).

**Verify:** `tests/test_utils_s3.py` (uses `moto` mock)
- `test_upload_file_returns_key_and_size`
- `test_upload_key_format_contains_project_id_and_filename`
- `test_delete_file_removes_object`
- `test_presign_url_returns_http_url`

---

### Task 13: Upload & List Documents

**Context:** Users need to upload one or more files to a project and get a list of files already there. Only PDF and DOCX files are allowed — anything else should be rejected before it reaches S3. The caller must have access (owner or participant) to the project. Each uploaded file gets saved to S3 and a record is saved to the `documents` table in the database.

**Build:**
1. Create `app/routers/documents.py`:
   - `POST /project/{project_id}/documents` — accepts a list of files as a multipart upload (`files: list[UploadFile]`).
     - Check the current user has a `ProjectAccess` row for this project. Raise `HTTPException(403)` if not.
     - For each file, check its `content_type`. If it's not `application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, raise `HTTPException(422)`.
     - Upload each file using `s3.upload_file`. Insert a `Document` row with the returned key and size. Collect and return all new documents as `list[DocumentOut]` with status `201`.
   - `GET /project/{project_id}/documents` — check access, then query and return all `Document` rows for that project as `list[DocumentOut]` with status `200`.
2. Register the documents router in `app/main.py`.

**Verify:** `tests/test_documents.py`
- `test_upload_pdf_returns_201`
- `test_upload_docx_returns_201`
- `test_upload_invalid_mime_returns_422`
- `test_upload_no_access_returns_403`
- `test_list_documents_returns_uploaded_files`

---

### Task 14: Download, Update & Delete Document

**Context:** Users need to download, replace, and delete their documents. Downloads work via a redirect — instead of streaming the file through the server, the API returns a temporary link pointing directly to S3 (this is faster and cheaper). Update replaces the old file completely. Delete removes the file from both S3 and the database.

**Build:**
1. Add three more routes to `app/routers/documents.py`. All three must check the current user has access to the project the document belongs to:
   - `GET /document/{document_id}` — look up the document, check access via its `project_id`, call `s3.presign_url(doc.s3_key)`, and return a `RedirectResponse` pointing to that URL with status `302`.
   - `PUT /document/{document_id}` — accept one `UploadFile`. Validate MIME type. Call `s3.delete_file` on the old key, then `s3.upload_file` for the new one. Update the `Document` row with the new key, filename, and size. Return the updated document as `DocumentOut` with status `200`.
   - `DELETE /document/{document_id}` — call `s3.delete_file`. Delete the `Document` row from the database. Return status `204`.

**Verify:** `tests/test_documents.py`
- `test_download_redirects_to_presigned_url`
- `test_download_no_access_returns_403`
- `test_update_document_replaces_file`
- `test_delete_document_returns_204`
- `test_delete_document_no_access_returns_403`

---

## Phase 5: Sharing

**Goal**: An owner can email a join link; clicking it (with a valid JWT) grants participant access.

---

### Task 15: Share Endpoint & Email Utility

**Context:** An owner can share a project with someone by entering their email address. The app generates a special short-lived link containing a signed token that encodes which project it's for. That link is sent by email. In development, where no email server is configured, just print it to the console so you can copy it for testing.

**Build:**
1. Create `app/utils/email.py` with a single function `send_email(to: str, subject: str, body: str) -> None`:
   - If `settings.SMTP_HOST` is set, connect using Python's built-in `smtplib` and send the email.
   - If `SMTP_HOST` is not set, just `print` the email content to stdout.
2. Add `GET /project/{project_id}/share` to `app/routers/projects.py`. The recipient's email comes in as a query parameter: `?with=<email>`.
   - Check the caller is `"owner"`. Raise `HTTPException(403)` if not.
   - Create a JWT token using `create_token({"type": "share", "project_id": project_id}, expires_in=900)`.
   - Build the join URL: `http://<host>/join?token=<token>`.
   - Call `send_email(to=email, subject="...", body=join_url)`.
   - Return `{"detail": "invite sent"}` with status `200`.

**Verify:** `tests/test_projects.py`
- `test_share_as_owner_returns_200`
- `test_share_as_participant_returns_403`
- `test_share_token_is_printed_when_no_smtp`
- `test_send_email_called_with_join_url`

---

### Task 16: Join Endpoint — `GET /join`

**Context:** When someone clicks the link from the share email, this endpoint handles it. It reads the token from the URL, checks that it's a valid share token (not an access token), and grants the currently logged-in user participant access to the project. If the token is expired or the wrong type, return an error.

**Build:**
1. Add `GET /join` to `app/routers/projects.py`. The token comes in as a query parameter: `?token=<token>`.
   - Call `decode_token(token)` — this already raises `401` if the token is expired or invalid.
   - Check that `payload["type"] == "share"`. If not, raise `HTTPException(400, "invalid token type")`.
   - Read `payload["project_id"]`.
   - Check if a `ProjectAccess` row already exists for the current user and that project. If not, insert one with `role="participant"`.
   - Return `{"detail": "access granted"}` with status `201`.

**Verify:** `tests/test_projects.py`
- `test_join_with_valid_token_grants_participant`
- `test_join_with_expired_token_returns_400`
- `test_join_with_wrong_token_type_returns_400`
- `test_join_idempotent`

---

## Phase 6: Quality

**Goal**: Tests pass, Lambda tracks storage, CI pipeline runs green.

---

### Task 17: Test Suite

**Context:** Now that all endpoints are implemented, write the tests that verify everything works. Tests use an in-memory SQLite database (fast, no setup needed) and a fake S3 provided by `moto`. The `conftest.py` file sets up fixtures that all test files share — like a test client and pre-logged-in users.

**Build:**
1. Write `tests/conftest.py` with fixtures:
   - `db` — creates all tables in an in-memory SQLite database and returns the session.
   - `client` — a FastAPI `TestClient` with the `get_db` dependency replaced by the test `db` session.
   - `alice_client` — a `client` where Alice is already registered and her JWT is injected in the headers.
   - `bob_client` — same but for Bob.
   - `mock_s3` — a `moto`-mocked S3 environment with a test bucket pre-created.
2. Write `tests/test_auth.py`, `tests/test_projects.py`, `tests/test_documents.py` — each file covers the tests named in the Verify sections of the tasks above.

**Verify:**
```bash
pytest tests/ -v
# Expected: all tests pass, 0 failures
```

---

### Task 18: Lambda — Storage Quota Tracking

**Context:** Every time a file is uploaded or deleted, an AWS Lambda function updates the total storage used by that project. The Lambda is triggered automatically by S3 — no need to call it from the app. It reads the S3 event to find out which file changed and by how much, then updates the `storage_bytes` column in the `projects` table directly in PostgreSQL.

**Build:**
1. Create `lambda/handler.py` with a single function `lambda_handler(event, context)`:
   - Read the first record from `event["Records"]`.
   - Get the S3 key (`record["s3"]["object"]["key"]`) and file size (`record["s3"]["object"]["size"]`).
   - Parse the project ID from the key — the format is `projects/{project_id}/...`, so split on `/` and take index 1.
   - Connect to PostgreSQL using `psycopg2` with `DATABASE_URL` from the environment.
   - If the event name starts with `"ObjectCreated"`, run `UPDATE projects SET storage_bytes = storage_bytes + %s WHERE id = %s`.
   - If it starts with `"ObjectRemoved"`, run `UPDATE projects SET storage_bytes = GREATEST(0, storage_bytes - %s) WHERE id = %s`.
   - Commit and close the connection.
2. Create `lambda/requirements.txt` with: `psycopg2-binary`, `boto3`.

**Verify:** `tests/test_lambda.py` (mocks `psycopg2`)
- `test_object_created_increments_storage_bytes`
- `test_object_removed_decrements_storage_bytes`
- `test_storage_bytes_does_not_go_below_zero`
- `test_project_id_parsed_from_s3_key`

---

### Task 19: CI/CD Pipeline

**Context:** Every time code is pushed to GitHub, a pipeline should run automatically to catch mistakes — lint errors, failing tests, or a Docker image that won't build. On merge to `main`, the Docker image is built and pushed to GitHub's container registry so it's ready to deploy.

**Build:**
1. Create `.github/workflows/ci.yml` with three jobs:
   - `lint` — runs `ruff check .` on every push and pull request.
   - `test` — runs `pytest --cov=app` after lint passes.
   - `build` — only runs when code is merged to `main`; builds the Docker image and pushes it to `ghcr.io/<your-github-username>/<repo-name>:latest`. Add a commented-out `deploy` job as a placeholder for when the deployment target is agreed with the mentor.
2. Write `README.md` covering: what the project does, how to run it locally (`cp .env.example .env`, then `docker compose up --build`), a table of all env vars, and how to run the tests (`pytest tests/`).

**Verify:**
```bash
# Push a branch to GitHub and open a pull request.
# Expected: lint and test jobs appear in the Actions tab and both turn green.
```
