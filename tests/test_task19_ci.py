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

def test_ci_job_ordering():
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())
    assert "lint" in ci["jobs"]["test"]["needs"]
    assert "test" in ci["jobs"]["build"]["needs"]
    assert "build" in ci['jobs']