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
    for pkg in [
        "fastapi", "uvicorn", "sqlalchemy", "psycopg2-binary",
        "pydantic-settings", "python-multipart", "pyjwt", "passlib",
        "boto3", "jinja2", "python-dotenv",
    ]:
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