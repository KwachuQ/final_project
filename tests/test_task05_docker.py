from pathlib import Path


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
