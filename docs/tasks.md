# Implementation Plan

## Summary

- Total phases: 7
- Total tasks: 25
- Estimated complexity: Medium

## Dependencies

```
 1 → 2 → 3 → 4 → 5 → 6 → 7
 │         │         │
 └→ 8 → 9 ┘         │
       │             │
       └→ 10 → 11 → 12 → 13 → 14 → 15
                                 │
                                 └→ 16 → 17 → 18
                                           │
                                           └→ 19 → 20
```

Tasks within a phase that share the same parent can be done in any order.

---

## Phase 1: App Skeleton

**Goal**: A FastAPI application that starts, responds to health checks, connects to a database, and can be run via Docker.

### Task 1: Create `pyproject.toml` with project metadata and dependencies

**Context:** This project is a FastAPI REST API for cloud migration assessment. Before any code can be written, the Python project needs a build configuration that declares all dependencies. `pyproject.toml` is the modern Python standard for this.

**Build:**
1. Create `pyproject.toml` defining project name `pymigscore`, Python 3.12+
2. Add build-system section using setuptools
3. Declare dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `psycopg2-binary`, `pydantic-settings`, `python-multipart`, `pyjwt`, `passlib[bcrypt]`, `boto3`, `jinja2`, `python-dotenv`
4. Declare dev dependencies: `pytest`, `httpx`, `ruff`, `testcontainers[postgresql]`, `moto`
5. Add `[tool.ruff]` config section with line-length 120 and target-version py312

**Verify:** `tests/test_task01_project_setup.py`
```python
import tomllib
from pathlib import Path

def test_pyproject_exists():
    assert Path("pyproject.toml").exists()

def test_pyproject_metadata():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    assert data["project"]["name"] == "pymigscore"
    assert data["project"]["requires-python"] == ">=3.12"

def test_pyproject_dependencies():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    deps = data["project"]["dependencies"]
    for pkg in ["fastapi", "uvicorn", "sqlalchemy", "psycopg2-binary", "pydantic-settings", "python-multipart", "pyjwt", "passlib", "boto3", "jinja2", "python-dotenv"]:
        assert any(pkg in d for d in deps), f"{pkg} missing from dependencies"

def test_pyproject_dev_dependencies():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    for pkg in ["pytest", "httpx", "ruff", "testcontainers", "moto"]:
        assert any(pkg in d for d in dev_deps), f"{pkg} missing from dev dependencies"

def test_ruff_config():
    data = tomllib.loads(Path("pyproject.toml").read_text())
    assert data["tool"]["ruff"]["line-length"] == 120
    assert data["tool"]["ruff"]["target-version"] == "py312"
```

---

### Task 2: Create `app/settings.py` with pydantic-settings config class

**Context:** The application reads all runtime configuration from environment variables. Using `pydantic-settings` provides type validation and defaults. The settings class is the single source of truth for all config values.

**Build:**
1. Create `app/__init__.py` (empty)
2. Create `app/settings.py` with a `Settings` class extending `BaseSettings`
3. Add fields matching the config table from requirements: `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_ORIGINS` (optional), `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` (default `eu-central-1`), `AWS_BUCKET_NAME`, `AWS_ENDPOINT_URL` (optional)
4. Add `model_config` with `env_file=".env"` so local overrides work
5. Create a cached `get_settings()` function using `@lru_cache`

**Verify:** `tests/test_task02_settings.py`
```python
def test_settings_loads_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import Settings
    s = Settings()
    assert s.AWS_REGION == "eu-central-1"
    assert s.DATABASE_URL == "postgresql://test:test@localhost/test"

def test_settings_aws_endpoint_url_optional(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    from app.settings import Settings
    s = Settings()
    assert s.AWS_ENDPOINT_URL is None

def test_get_settings_is_cached():
    from app.settings import get_settings
    assert get_settings() is get_settings()
```

---

### Task 3: Create `app/database.py` with SQLAlchemy engine and session

**Context:** All data is persisted in PostgreSQL via SQLAlchemy ORM. This file creates the engine, session factory, and `Base` declarative base that all models will inherit from. It also provides the `get_db()` FastAPI dependency.

**Build:**
1. Create `app/database.py` with `Base = declarative_base()`
2. Create engine from `settings.DATABASE_URL`
3. Create `SessionLocal` sessionmaker
4. Implement `get_db()` generator that yields a session and closes it

**Verify:** `tests/test_task03_database.py`
```python
def test_base_is_declarative():
    from app.database import Base
    assert hasattr(Base, "metadata")

def test_get_db_yields_session():
    """Verify get_db is a generator that yields a session and closes it."""
    from app.database import get_db
    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass  # expected — generator closes
```

---

### Task 4: Create `app/main.py` with FastAPI app factory and health endpoint

**Context:** This is the entry point of the application. It creates the FastAPI instance, configures CORS middleware using `ALLOWED_ORIGINS` from settings, creates database tables on startup, and registers all routers.

**Build:**
1. Create `app/main.py` with a `create_app()` function
2. Add CORS middleware — if `ALLOWED_ORIGINS` is set, parse comma-separated origins; otherwise allow all
3. Add a startup event that calls `Base.metadata.create_all()`
4. Register the health router (create `app/routers/__init__.py` empty and `app/routers/health.py`) with a `GET /health` endpoint returning `{"status": "ok"}`
5. Expose the FastAPI app at module level via `app = create_app()`

**Verify:** `tests/test_task04_health.py`
```python
from fastapi.testclient import TestClient

def test_health_endpoint():
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_cors_middleware_present():
    from app.main import app
    middleware_classes = [type(m).__name__ for m in app.user_middleware]
    # CORS middleware should be registered
    assert any("CORS" in name or "cors" in name for name in middleware_classes) or \
        any("CORSMiddleware" in str(m) for m in app.user_middleware)
```

---

### Task 5: Create `Dockerfile` and `docker-compose.yml`

**Context:** The application runs in Docker alongside PostgreSQL and LocalStack (for S3 emulation). A multi-stage Dockerfile keeps the image small, and docker-compose wires all three services together.

**Build:**
1. Create a multi-stage `Dockerfile` (builder stage + runtime stage)
2. Use `python:3.12-slim` as base, install dependencies, copy app code
3. Create `docker-compose.yml` with three services: `app`, `db` (postgres:16-alpine), `localstack` (localstack/localstack)
4. Wire environment variables: `DATABASE_URL=postgresql://pymig:pymig@db:5432/pymig`, `AWS_ENDPOINT_URL=http://localstack:4566`, `AWS_BUCKET_NAME=pymig-uploads`, `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`, `AWS_REGION=eu-central-1`
5. Add a healthcheck for the `app` service that curls `/health`
6. Add a volume for LocalStack data persistence

**Verify:** `tests/test_task05_docker.py`
```python
from pathlib import Path
import re

def test_dockerfile_exists():
    assert Path("Dockerfile").exists()

def test_dockerfile_multistage():
    content = Path("Dockerfile").read_text()
    assert content.lower().count("from ") >= 2, "Dockerfile should be multi-stage"

def test_compose_file_exists():
    assert Path("docker-compose.yml").exists() or Path("docker-compose.yaml").exists()

def test_compose_has_required_services():
    import yaml
    path = Path("docker-compose.yml") if Path("docker-compose.yml").exists() else Path("docker-compose.yaml")
    compose = yaml.safe_load(path.read_text())
    services = compose.get("services", {}).keys()
    for svc in ["app", "db", "localstack"]:
        assert svc in services, f"{svc} service missing from docker-compose"
```

---

## Phase 2: Authentication

**Goal**: Users can register and log in. Protected endpoints can validate JWTs. This unlocks the auth wall for all subsequent phases.

### Task 6: Create `UserModel` ORM model in `app/database.py`

**Context:** The database needs a `users` table to store registered accounts. The model uses the `Model` naming convention to avoid collisions with Pydantic schemas.

**Build:**
1. Add `UserModel` class to `app/database.py` extending `Base`
2. Define columns: `id` (Integer PK, auto-increment), `username` (String, unique, not null), `password_hash` (String, not null), `created_at` (DateTime, default=utcnow)
3. Add `__tablename__ = "users"`

**Verify:** `tests/test_task06_user_model.py`
```python
def test_user_model_table_name():
    from app.database import UserModel
    assert UserModel.__tablename__ == "users"

def test_user_model_columns():
    from app.database import UserModel
    columns = {c.name for c in UserModel.__table__.columns}
    assert {"id", "username", "password_hash", "created_at"} <= columns

def test_username_is_unique():
    from app.database import UserModel
    col = UserModel.__table__.c.username
    assert col.unique is True
```

---

### Task 7: Create `app/schemas.py` with auth-related Pydantic models

**Context:** FastAPI uses Pydantic models for request validation and response serialization. This file defines the schemas for user registration and login.

**Build:**
1. Create `app/schemas.py`
2. Define `UserRegister` with `username: str`, `password: str`, `password_repeat: str`
3. Add a `model_validator` to check that passwords match (raise `ValueError` if not)
4. Define `UserResponse` with `user_id: int`, `username: str`
5. Define `TokenResponse` with `access_token: str`, `token_type: str`
6. Define `ErrorResponse` with `detail: str` for consistent error shapes

**Verify:** `tests/test_task07_auth_schemas.py`
```python
import pytest
from app.schemas import UserRegister, UserResponse, TokenResponse, ErrorResponse

def test_user_register_valid():
    u = UserRegister(username="alice", password="secret", password_repeat="secret")
    assert u.username == "alice"

def test_user_register_password_mismatch():
    with pytest.raises(ValueError):
        UserRegister(username="alice", password="secret", password_repeat="wrong")

def test_user_response_fields():
    r = UserResponse(user_id=1, username="alice")
    assert r.user_id == 1

def test_token_response_fields():
    t = TokenResponse(access_token="abc", token_type="bearer")
    assert t.access_token == "abc"

def test_error_response_fields():
    e = ErrorResponse(detail="not found")
    assert e.detail == "not found"
```

---

### Task 8: Create `app/routers/auth.py` with register and login endpoints

**Context:** The auth router handles user registration (hashing passwords with bcrypt) and login (verifying credentials and issuing a JWT). It uses FastAPI's `OAuth2PasswordRequestForm` for login to stay OAuth2-compatible.

**Build:**
1. Create `app/routers/auth.py` with an `APIRouter(prefix="/auth")`
2. `POST /register` — validate `UserRegister`, check for duplicate username (return `409`), hash password with passlib bcrypt, create `UserModel`, return `201 UserResponse`
3. `POST /login` — accept `OAuth2PasswordRequestForm`, look up user by username, verify password with passlib, generate a JWT (HS256, 1-hour expiry, `sub=user_id`), return `TokenResponse`
4. Register the auth router in `app/main.py`

**Verify:** `tests/test_task08_auth_endpoints.py`
```python
def test_register_returns_201(client):
    resp = client.post("/auth/register", json={
        "username": "alice", "password": "secret123", "password_repeat": "secret123"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice"
    assert "user_id" in data

def test_register_duplicate_returns_409(client):
    payload = {"username": "dup", "password": "secret123", "password_repeat": "secret123"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409

def test_login_returns_token(client):
    client.post("/auth/register", json={
        "username": "bob", "password": "secret123", "password_repeat": "secret123"
    })
    resp = client.post("/auth/login", data={"username": "bob", "password": "secret123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"

def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={
        "username": "carol", "password": "secret123", "password_repeat": "secret123"
    })
    resp = client.post("/auth/login", data={"username": "carol", "password": "wrong"})
    assert resp.status_code == 401
```

---

### Task 9: Create `app/deps.py` with JWT verification dependency

**Context:** Protected endpoints need to verify the JWT from the `Authorization` header and return the current user. This FastAPI dependency is reusable across all protected routes.

**Build:**
1. Create `app/deps.py`
2. Implement `get_current_user()` that extracts the `Authorization: Bearer <token>` header
3. Decode the JWT using `SECRET_KEY` and HS256 algorithm
4. Look up the `UserModel` by the `sub` (user_id) from the token
5. Raise `HTTPException(401)` if the token is missing, invalid, expired, or the user doesn't exist
6. Define `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")` for Swagger UI integration

**Verify:** `tests/test_task09_jwt_dependency.py`

Note: these tests use `get_current_user` directly as a unit, since the `/assessments` router does not exist yet at this phase.

```python
import pytest
from unittest.mock import MagicMock

def test_valid_token_returns_user(db):
    import jwt, time
    from app.settings import get_settings
    from app.database import UserModel
    from app.deps import get_current_user
    user = UserModel(id=1, username="test", password_hash="x")
    db.add(user)
    db.commit()
    token = jwt.encode({"sub": 1, "exp": int(time.time()) + 3600}, get_settings().SECRET_KEY, algorithm="HS256")
    result = get_current_user(token=token, db=db)
    assert result.username == "test"

def test_expired_token_raises_401(db):
    import jwt, time
    from fastapi import HTTPException
    from app.settings import get_settings
    from app.deps import get_current_user
    token = jwt.encode({"sub": 1, "exp": int(time.time()) - 10}, get_settings().SECRET_KEY, algorithm="HS256")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db)
    assert exc_info.value.status_code == 401

def test_invalid_token_raises_401(db):
    from fastapi import HTTPException
    from app.deps import get_current_user
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="garbage", db=db)
    assert exc_info.value.status_code == 401
```

---

## Phase 3: Domain Logic

**Goal**: The core business logic — CSV parsing and system scoring — is implemented as pure functions with no side effects, fully testable in isolation.

### Task 10: Create domain Pydantic models and enums in `app/schemas.py`

**Context:** The domain layer needs data types for system inventory rows, scored results, and enums for system types, languages, etc. These are used by both the loader and scoring services.

**Build:**
1. Add enums: `SystemTypeEnum` (web_app, database, batch_job, file_server), `OperatingSystemEnum` (linux, windows), `LanguageEnum` (python, java, dotnet, cobol, cpp), `AvailabilityEnum` (high, medium, low), `WaveEnum` (quick_win, standard, complex), `StrategyEnum` (retire, repurchase, retain, rehost, replatform, refactor)
2. Define `SystemInventory` model with fields matching the CSV schema exactly (system_name, system_type, operating_system, language, num_users, data_size_gb, availability, has_compliance, is_vendor_software)
3. Define `ScoredSystem` model with fields: system_name, system_type, composite_score, complexity_score, cloud_fit_score, risk_score, wave, recommended_strategy, effort_min, effort_max
4. Define `AssessmentSummary` response model with: id, name, created_at, system_count
5. Define `AssessmentDetail` response model with: id, name, created_at, system_count, s3_key, scored_systems (list of ScoredSystem)
6. Define `AssessmentCreateResponse` with: id, name, created_at, system_count, s3_key, scored_systems

**Verify:** `tests/test_task10_domain_schemas.py`
```python
from app.schemas import (
    SystemTypeEnum, OperatingSystemEnum, LanguageEnum,
    AvailabilityEnum, WaveEnum, StrategyEnum,
    SystemInventory, ScoredSystem, AssessmentSummary, AssessmentDetail,
    AssessmentCreateResponse,
)

def test_system_type_enum_values():
    assert set(SystemTypeEnum) == {SystemTypeEnum.web_app, SystemTypeEnum.database, SystemTypeEnum.batch_job, SystemTypeEnum.file_server}

def test_system_inventory_accepts_valid_data():
    si = SystemInventory(
        system_name="erp", system_type="web_app", operating_system="linux",
        language="python", num_users=100, data_size_gb=10.0,
        availability="high", has_compliance=False, is_vendor_software=False,
    )
    assert si.system_name == "erp"
    assert si.system_type == SystemTypeEnum.web_app

def test_scored_system_fields():
    ss = ScoredSystem(
        system_name="erp", system_type="web_app",
        composite_score=5.0, complexity_score=3.0, cloud_fit_score=7.0, risk_score=4.0,
        wave="standard", recommended_strategy="rehost", effort_min=10, effort_max=30,
    )
    assert ss.wave == WaveEnum.standard
    assert ss.recommended_strategy == StrategyEnum.rehost

def test_assessment_summary_fields():
    from datetime import datetime
    s = AssessmentSummary(id=1, name="test", created_at=datetime.now(), system_count=5)
    assert s.system_count == 5
```

---

### Task 11: Create `app/services/loader.py` for CSV parsing and validation

**Context:** Users upload a CSV inventory file. This service parses raw bytes, validates each row against the `SystemInventory` Pydantic model, and returns either parsed data or structured errors with row numbers.

**Build:**
1. Create `app/services/__init__.py` (empty) and `app/services/loader.py`
2. Implement `parse_inventory(data: bytes) -> list[SystemInventory]`
3. Use `csv.DictReader` to parse rows from the bytes
4. For each row, validate against `SystemInventory.model_validate()`
5. If a row fails, collect a structured error with the row number (1-based, skipping header) and field names
6. Enforce a maximum of 1,000 rows — raise a `ValueError` if exceeded
7. After all rows are parsed, check for duplicate `system_name` values and fail with errors if any exist
8. If any errors occurred, raise a custom `CSVValidationError` containing all error details

**Verify:** `tests/test_task11_loader.py`
```python
import pytest
from app.services.loader import parse_inventory, CSVValidationError

VALID_CSV = (
    b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    b"erp,web_app,linux,python,100,10.0,high,false,false\n"
)

def test_valid_csv_returns_inventory_list():
    result = parse_inventory(VALID_CSV)
    assert len(result) == 1
    assert result[0].system_name == "erp"

def test_invalid_csv_raises_with_row_numbers():
    bad = b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n" \
          b"erp,INVALID,linux,python,100,10.0,high,false,false\n"
    with pytest.raises(CSVValidationError) as exc_info:
        parse_inventory(bad)
    assert any("row" in str(e).lower() or "1" in str(e) for e in exc_info.value.errors)

def test_duplicate_system_names_raises():
    dup = VALID_CSV + b"erp,web_app,linux,python,50,5.0,low,false,false\n"
    with pytest.raises(CSVValidationError):
        parse_inventory(dup)

def test_exceeding_1000_rows_raises():
    header = b"system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    row = b"sys_%d,web_app,linux,python,10,1.0,low,false,false\n"
    data = header + b"".join(row.replace(b"%d", str(i).encode()) for i in range(1001))
    with pytest.raises((CSVValidationError, ValueError)):
        parse_inventory(data)
```

---

### Task 12: Create `app/services/scoring.py` with scoring rules, wave assignment, and 6 Rs strategy

**Context:** This is the core of the application — it transforms parsed system data into scored results with migration strategies. It implements hardcoded scoring weights, wave thresholds, and the full 6 Rs strategy logic.

**Build:**
1. Create `app/services/scoring.py`
2. Define hardcoded weight constants for complexity, cloud_fit, and risk
3. Implement `_compute_complexity_score(system)` — 0-10 based on language difficulty + system_type complexity (legacy languages and batch jobs score higher)
4. Implement `_compute_cloud_fit_score(system)` — 0-10 based on OS (linux higher) and system_type (web_app higher)
5. Implement `_compute_risk_score(system)` — 0-10 based on num_users, data_size_gb, availability, has_compliance
6. Implement `_assign_strategy_and_wave(system, scores)` with 6 Rs logic:
   - Retire if `num_users == 0` (override wave to quick_win, effort to 0-0)
   - Repurchase if `is_vendor_software == True`
   - Retain if `has_compliance and language in (cobol, cpp)`
   - Rehost if low complexity + high cloud_fit
   - Replatform if medium complexity + medium/high cloud_fit
   - Refactor if high complexity + low cloud_fit
7. Implement `_assign_wave(composite_score)` — quick_win (0-3.9), standard (4-6.9), complex (7-10)
8. Implement `_estimate_effort(strategy, system)` — return (effort_min, effort_max) in person-days
9. Implement `score_systems(systems: list[SystemInventory]) -> list[ScoredSystem]` that orchestrates all of the above

**Verify:** `tests/test_task12_scoring.py`
```python
from app.schemas import SystemInventory
from app.services.scoring import score_systems

def _make_system(**overrides):
    defaults = dict(
        system_name="test", system_type="web_app", operating_system="linux",
        language="python", num_users=100, data_size_gb=10.0,
        availability="high", has_compliance=False, is_vendor_software=False,
    )
    defaults.update(overrides)
    return SystemInventory(**defaults)

def test_retire_strategy():
    result = score_systems([_make_system(num_users=0)])
    assert result[0].recommended_strategy.value == "retire"
    assert result[0].wave.value == "quick_win"
    assert result[0].effort_min == 0
    assert result[0].effort_max == 0

def test_repurchase_strategy():
    result = score_systems([_make_system(is_vendor_software=True)])
    assert result[0].recommended_strategy.value == "repurchase"

def test_retain_strategy():
    result = score_systems([_make_system(language="cobol", has_compliance=True)])
    assert result[0].recommended_strategy.value == "retain"

def test_scores_are_bounded_0_to_10():
    result = score_systems([_make_system()])
    for s in result:
        assert 0 <= s.complexity_score <= 10
        assert 0 <= s.cloud_fit_score <= 10
        assert 0 <= s.risk_score <= 10
        assert 0 <= s.composite_score <= 10
```

---

## Phase 4: Assessment CRUD

**Goal**: Users can create assessments by uploading CSVs, view their assessment history, see full details, and delete assessments. S3 integration for file storage is complete with compensating transactions.

### Task 13: Add `AssessmentModel` and `ScoredSystemModel` ORM models to `app/database.py`

**Context:** The database needs tables for assessments and scored systems. Scored systems cascade-delete with their parent assessment.

**Build:**
1. Add `AssessmentModel` with fields: `id` (PK), `user_id` (FK → users.id), `name` (default "Untitled"), `created_at`, `system_count`, `s3_key`
2. Add `ScoredSystemModel` with fields: `id` (PK), `assessment_id` (FK → assessments.id, cascade delete), `system_name`, `system_type`, `composite_score`, `complexity_score`, `cloud_fit_score`, `risk_score`, `wave`, `recommended_strategy`, `effort_min`, `effort_max`
3. Add a relationship from `AssessmentModel` to `ScoredSystemModel` (one-to-many, cascade="all, delete-orphan")
4. Add a relationship from `UserModel` to `AssessmentModel`

**Verify:** `tests/test_task13_assessment_models.py`
```python
def test_assessment_model_table():
    from app.database import AssessmentModel
    assert AssessmentModel.__tablename__ == "assessments"
    columns = {c.name for c in AssessmentModel.__table__.columns}
    assert {"id", "user_id", "name", "created_at", "system_count", "s3_key"} <= columns

def test_scored_system_model_table():
    from app.database import ScoredSystemModel
    assert ScoredSystemModel.__tablename__ == "scored_systems"
    columns = {c.name for c in ScoredSystemModel.__table__.columns}
    assert {"id", "assessment_id", "system_name", "system_type", "composite_score", "complexity_score", "cloud_fit_score", "risk_score", "wave", "recommended_strategy", "effort_min", "effort_max"} <= columns

def test_assessment_cascade_relationship():
    from app.database import AssessmentModel
    rel = AssessmentModel.__mapper__.relationships["scored_systems"]
    assert "delete" in rel.cascade

def test_user_id_foreign_key():
    from app.database import AssessmentModel
    fks = [fk.target_fullname for fk in AssessmentModel.__table__.c.user_id.foreign_keys]
    assert "users.id" in fks
```

---

### Task 14: Create `app/s3.py` with boto3 wrapper

**Context:** The application stores uploaded CSV files in S3 for record-keeping. This module provides a thin wrapper around boto3's upload and delete operations, isolating AWS SDK calls from the rest of the application.

**Build:**
1. Create `app/s3.py`
2. Implement `get_s3_client()` that creates a boto3 client using settings (endpoint URL for LocalStack support)
3. Implement `upload_file(key: str, data: bytes)` that uploads to the configured bucket
4. Implement `delete_file(key: str)` that deletes an object from the configured bucket
5. If the bucket doesn't exist on first upload, create it automatically (idempotent via `BucketAlreadyExists` handling)
6. Handle `ClientError` gracefully by re-raising as `RuntimeError`

**Verify:** `tests/test_task14_s3.py`
```python
import pytest
from moto import mock_aws

@pytest.fixture
def s3_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("SECRET_KEY", "testsecret")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("AWS_BUCKET_NAME", "test-bucket")

@mock_aws
def test_upload_and_retrieve(s3_env):
    from app.s3 import upload_file, get_s3_client
    from app.settings import get_settings
    upload_file("test.csv", b"hello")
    obj = get_s3_client().get_object(Bucket=get_settings().AWS_BUCKET_NAME, Key="test.csv")
    assert obj["Body"].read() == b"hello"

@mock_aws
def test_delete_file(s3_env):
    from app.s3 import upload_file, delete_file, get_s3_client
    from app.settings import get_settings
    upload_file("del.csv", b"data")
    delete_file("del.csv")
    import botocore.exceptions
    with pytest.raises(botocore.exceptions.ClientError):
        get_s3_client().get_object(Bucket=get_settings().AWS_BUCKET_NAME, Key="del.csv")
```

---

### Task 15: Create `POST /assessments` endpoint in assessments router

**Context:** This is the most complex endpoint — it accepts a multipart upload, parses and scores the CSV, uploads to S3, commits to the database, and handles compensating transactions if the DB commit fails.

**Build:**
1. Create `app/routers/assessments.py` with `APIRouter(prefix="/assessments", dependencies=[Depends(get_current_user)])`
2. Implement `POST /assessments` accepting `UploadFile` (`inventory`) and optional `name` form field
3. Read the file bytes, call `loader.parse_inventory()` — return `400` with structured errors on failure
4. Call `scoring.score_systems()` to get scored results
5. Generate an S3 key (e.g., `uploads/{user_id}/{uuid}.csv`)
6. Call `s3.upload_file()` — if this fails, return `500`
7. Create `AssessmentModel` and `ScoredSystemModel` rows, add to session
8. Try `db.commit()` — on failure, catch exception, call `s3.delete_file()` as compensating action, return `500`
9. Return `201` with the full assessment detail
10. Register the router in `app/main.py`

**Verify:** `tests/test_task15_create_assessment.py`
```python
import io

VALID_CSV = (
    "system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    "erp,web_app,linux,python,100,10.0,high,false,false\n"
)

def test_create_assessment_returns_201(auth_client, mock_s3):
    resp = auth_client.post("/assessments", files={"inventory": ("test.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")}, data={"name": "My Assessment"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Assessment"
    assert data["system_count"] == 1
    assert len(data["scored_systems"]) == 1

def test_create_assessment_invalid_csv_returns_400(auth_client, mock_s3):
    bad_csv = b"system_name,system_type\nfoo,INVALID\n"
    resp = auth_client.post("/assessments", files={"inventory": ("bad.csv", io.BytesIO(bad_csv), "text/csv")})
    assert resp.status_code == 400
```

---

### Task 16: Create `GET /assessments`, `GET /assessments/{id}`, and `DELETE /assessments/{id}` endpoints

**Context:** Users need to list their assessments, view details, and delete them. These are straightforward CRUD operations with owner checks.

**Build:**
1. `GET /assessments` — query all `AssessmentModel` rows where `user_id == current_user.id`, ordered by `created_at` desc, return list of `AssessmentSummary`
2. `GET /assessments/{id}` — get assessment by id, verify ownership (return `403` if not owner, `404` if not found), eager-load `scored_systems`, return `AssessmentDetail`
3. `DELETE /assessments/{id}` — verify ownership, call `s3.delete_file()` to remove the CSV, delete the assessment (cascade deletes scored systems), return `204`

**Verify:** `tests/test_task16_assessment_crud.py`
```python
import io

VALID_CSV = (
    "system_name,system_type,operating_system,language,num_users,data_size_gb,availability,has_compliance,is_vendor_software\n"
    "erp,web_app,linux,python,100,10.0,high,false,false\n"
)

def test_list_assessments_empty(auth_client, mock_s3):
    resp = auth_client.get("/assessments")
    assert resp.status_code == 200
    assert resp.json() == []

def test_get_assessment_detail(auth_client, mock_s3):
    create = auth_client.post("/assessments", files={"inventory": ("t.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")})
    aid = create.json()["id"]
    resp = auth_client.get(f"/assessments/{aid}")
    assert resp.status_code == 200
    assert "scored_systems" in resp.json()

def test_delete_assessment(auth_client, mock_s3):
    create = auth_client.post("/assessments", files={"inventory": ("t.csv", io.BytesIO(VALID_CSV.encode()), "text/csv")})
    aid = create.json()["id"]
    resp = auth_client.delete(f"/assessments/{aid}")
    assert resp.status_code == 204
    assert auth_client.get(f"/assessments/{aid}").status_code == 404

def test_get_nonexistent_assessment_returns_404(auth_client, mock_s3):
    resp = auth_client.get("/assessments/9999")
    assert resp.status_code == 404
```

---

## Phase 5: Dashboard

**Goal**: A working HTML dashboard served by FastAPI that lets users log in and browse their assessments.

### Task 17: Create `GET /dashboard` router and Jinja2 HTML template

**Context:** The dashboard is a single-page HTML app served by FastAPI. It uses a Jinja2 template with embedded CSS and vanilla JavaScript. The JS handles login (stores JWT in localStorage), fetches assessments, and renders scored systems in a table.

**Build:**
1. Create `app/routers/dashboard.py` with `APIRouter` and `GET /dashboard`
2. Configure Jinja2 `Templates` pointing to `app/templates/`
3. Create `app/templates/__init__.py` (empty)
4. Create `app/templates/dashboard.html` with:
   - A login form (username + password) that stores the JWT in `localStorage`
   - An assessment list section (fetched via `fetch("/assessments", {headers: {Authorization: "Bearer " + token}})`)
   - A detail table shown on click with columns: system name, type, composite score, complexity, cloud fit, risk, wave, effort range
   - Embedded `<style>` for a clean, readable UI
   - Embedded `<script>` with all JS logic (no external libraries)
5. Register the dashboard router in `app/main.py`

**Verify:** `tests/test_task17_dashboard.py`
```python
from fastapi.testclient import TestClient

def test_dashboard_returns_html(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

def test_dashboard_contains_login_form(client):
    resp = client.get("/dashboard")
    html = resp.text.lower()
    assert "login" in html
    assert "<form" in html or "<input" in html

def test_dashboard_contains_app_name(client):
    resp = client.get("/dashboard")
    assert "PyMigScore" in resp.text or "pymigscore" in resp.text.lower()
```

---

## Phase 6: Testing

**Goal**: Full test coverage of all endpoints, services, and error paths using pytest with testcontainers for PostgreSQL parity and moto for S3 mocking.

### Task 18: Create `tests/conftest.py` with testcontainers, fixtures, and mocks

**Context:** The test suite needs a real PostgreSQL instance via testcontainers, a test client with overridden DB dependency, an authenticated client fixture, and sample CSV data. This file sets up all shared fixtures.

**Build:**
1. Create `tests/__init__.py` (empty) and `tests/conftest.py`
2. Create `db` fixture that starts a testcontainers PostgreSQL 16 container, creates all tables via `Base.metadata.create_all()`, yields a session, then drops/rolls back
3. Create `client` fixture that overrides `get_db` dependency to use the testcontainer session
4. Create `auth_client` fixture that registers and logs in a test user, returns the TestClient with auth header pre-set
5. Create `sample_inventory_csv` fixture that writes a valid CSV to a temp file and returns its path
6. Create `mock_s3` fixture using moto to mock S3

**Verify:** `tests/test_task18_conftest.py`
```python
def test_db_fixture_provides_session(db):
    """The db fixture should yield a working SQLAlchemy session."""
    assert db is not None
    assert hasattr(db, "execute")

def test_client_fixture_works(client):
    """The client fixture should be a TestClient that can hit /health."""
    resp = client.get("/health")
    assert resp.status_code == 200

def test_auth_client_has_auth_header(auth_client):
    """The auth_client fixture should have a pre-set Authorization header."""
    resp = auth_client.get("/assessments")
    assert resp.status_code == 200  # not 401

def test_mock_s3_fixture_isolates(mock_s3):
    """The mock_s3 fixture should provide a working mocked S3 environment."""
    assert mock_s3 is not None
```

---

### Task 19: Create `tests/test_health.py`

**Context:** The health endpoint is the simplest — one test to confirm it returns the expected response.

**Build:**
1. Create `tests/test_health.py`
2. Test `GET /health` returns `{"status": "ok"}` with `200`

**Verify:** `pytest tests/test_health.py -v` — 1 test passes:
```
tests/test_health.py::test_health_returns_ok PASSED
```

---

### Task 20: Create `tests/test_auth.py`

**Context:** Authentication has multiple paths: successful register and login, duplicate username (409), password mismatch (400), invalid credentials (401).

**Build:**
1. Test successful register returns `201` with user_id and username
2. Test duplicate username returns `409`
3. Test password mismatch returns `400`
4. Test successful login returns `200` with access_token
5. Test login with wrong password returns `401`
6. Test accessing a protected endpoint without a token returns `401`

**Verify:** `pytest tests/test_auth.py -v` — 6 tests pass:
```
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate_409 PASSED
tests/test_auth.py::test_register_password_mismatch_400 PASSED
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_wrong_password_401 PASSED
tests/test_auth.py::test_protected_without_token_401 PASSED
```

---

### Task 21: Create `tests/test_services/test_loader.py`

**Context:** The CSV loader is a pure function — easy to unit test. Tests cover valid CSVs, invalid rows, duplicate system names, empty files, and files exceeding 1000 rows.

**Build:**
1. Create `tests/test_services/__init__.py` (empty) and `tests/test_services/test_loader.py`
2. Test valid CSV parses all rows correctly into `SystemInventory` objects
3. Test invalid CSV raises `CSVValidationError` with row-numbered errors
4. Test duplicate system_names in CSV raises validation error
5. Test CSV with >1000 rows raises an error

**Verify:** `pytest tests/test_services/test_loader.py -v` — 4 tests pass:
```
tests/test_services/test_loader.py::test_valid_csv_parses PASSED
tests/test_services/test_loader.py::test_invalid_csv_raises PASSED
tests/test_services/test_loader.py::test_duplicate_names_raises PASSED
tests/test_services/test_loader.py::test_exceeding_1000_rows_raises PASSED
```

---

### Task 22: Create `tests/test_services/test_scoring.py`

**Context:** The scoring service is a pure function. Tests verify scoring rules, wave assignment, the 6 Rs strategy, and edge cases.

**Build:**
1. Create `tests/test_services/test_scoring.py`
2. Test Retire strategy: system with `num_users=0` → strategy=retire, wave=quick_win, effort=0-0
3. Test Repurchase strategy: vendor software → strategy=repurchase
4. Test Retain strategy: cobol system with compliance → strategy=retain
5. Test Rehost strategy: low complexity, high cloud_fit
6. Test Replatform strategy: medium complexity, medium cloud_fit
7. Test Refactor strategy: high complexity, low cloud_fit
8. Test wave assignment boundaries (3.9 → quick_win, 4.0 → standard, 7.0 → complex)
9. Test composite_score is weighted average of three scores

**Verify:** `pytest tests/test_services/test_scoring.py -v` — 8 tests pass:
```
tests/test_services/test_scoring.py::test_retire_strategy PASSED
tests/test_services/test_scoring.py::test_repurchase_strategy PASSED
tests/test_services/test_scoring.py::test_retain_strategy PASSED
tests/test_services/test_scoring.py::test_rehost_strategy PASSED
tests/test_services/test_scoring.py::test_replatform_strategy PASSED
tests/test_services/test_scoring.py::test_refactor_strategy PASSED
tests/test_services/test_scoring.py::test_wave_boundaries PASSED
tests/test_services/test_scoring.py::test_composite_weighted_average PASSED
```

---

### Task 23: Create `tests/test_assessments.py`

**Context:** Assessment endpoints are tested via the authenticated test client with real PostgreSQL and mocked S3. Tests cover the full create-list-detail-delete cycle and error paths.

**Build:**
1. Test create assessment with valid CSV returns `201` with scored systems
2. Test create assessment with invalid CSV returns `400` with structured errors
3. Test list assessments returns list of summaries
4. Test get assessment detail returns full data with scored_systems
5. Test delete assessment returns `204` and subsequent `GET` returns `404`
6. Test deleting another user's assessment returns `403`
7. Test get non-existent assessment returns `404`
8. Test compensating transaction: mock DB commit to fail, confirm S3 file is deleted
9. Test CSV with >1000 rows returns `413`

**Verify:** `pytest tests/test_assessments.py -v` — 9 tests pass:
```
tests/test_assessments.py::test_create_valid_csv_201 PASSED
tests/test_assessments.py::test_create_invalid_csv_400 PASSED
tests/test_assessments.py::test_list_assessments PASSED
tests/test_assessments.py::test_get_detail PASSED
tests/test_assessments.py::test_delete_204_then_404 PASSED
tests/test_assessments.py::test_delete_other_user_403 PASSED
tests/test_assessments.py::test_get_nonexistent_404 PASSED
tests/test_assessments.py::test_compensating_transaction PASSED
tests/test_assessments.py::test_csv_over_1000_rows_413 PASSED
```

---

### Task 24: Create `tests/test_dashboard.py`

**Context:** The dashboard endpoint returns HTML. Tests verify it renders correctly and contains expected elements.

**Build:**
1. Test `GET /dashboard` returns `200` with `text/html` content type
2. Test the HTML contains "PyMigScore" and "login" in the body (case-insensitive)

**Verify:** `pytest tests/test_dashboard.py -v` — 2 tests pass:
```
tests/test_dashboard.py::test_dashboard_returns_html PASSED
tests/test_dashboard.py::test_dashboard_contains_expected_content PASSED
```

---

## Phase 7: CI/CD

**Goal**: Every push or PR is linted, tested, and built automatically via GitHub Actions.

### Task 25: Create `.github/workflows/ci.yml`

**Context:** Continuous integration ensures code quality. The pipeline lints with ruff, runs the full test suite (which will spin up testcontainers PostgreSQL via Docker-in-Docker), and builds the Docker image.

**Build:**
1. Create `.github/workflows/ci.yml`
2. Trigger on `push` and `pull_request` to `main`
3. Job 1: `lint` — checkout, set up Python 3.12, install deps, run `ruff check .`
4. Job 2: `test` — needs lint, checkout, set up Python 3.12, install deps, run `pytest -v` (testcontainers handles PostgreSQL automatically)
5. Job 3: `build` — needs test, checkout, run `docker build .`

**Verify:** `tests/test_task25_ci.py`
```python
from pathlib import Path
import yaml

def test_ci_yml_exists():
    assert Path(".github/workflows/ci.yml").exists()

def test_ci_triggers():
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    # PyYAML parses bare `on:` as boolean True
    triggers = ci.get(True) or ci.get("on")
    assert "push" in triggers
    assert "pull_request" in triggers

def test_ci_has_three_jobs():
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    jobs = ci["jobs"]
    assert "lint" in jobs
    assert "test" in jobs
    assert "build" in jobs

def test_ci_job_ordering():
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    assert "lint" in ci["jobs"]["test"]["needs"]
    assert "test" in ci["jobs"]["build"]["needs"]
```