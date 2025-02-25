from datetime import timedelta
import pytest
import yaml
from depictio_models.models.cli import CLIConfig  # Adjust import as needed
from bson import ObjectId, datetime
import httpx
from typing import Any, Optional, Dict

from src.depictio_cli.cli.utils.api_calls import (
    api_create_project,
    api_get_project_from_id,
    api_login,
)


@pytest.fixture
def dummy_cli_config() -> CLIConfig:
    # Create a minimal valid CLIConfig for testing.
    # Adjust the dictionary keys/values based on your CLIConfig model requirements.
    return CLIConfig(
        api_base_url="http://dummy.api",
        user={
            "email": "dummy@example.com",
            "is_admin": False,
            "id": ObjectId(),
            "groups": [],
            "token": {
                "name": "dummy_user",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkdW1teUBleGFtcGxlLmNvbSIsImlhdCI6MTcwODY3MjAwMCwiZXhwIjoxNzA4Njc1NjAwfQ.PvFZok3c8p_jX-1Ih2i69H2EoPZHZiF9Sz6GfbEvfYw",
                "expire_datetime": (datetime.now() + timedelta(hours=1)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),  # Correct format
            },
        },
        s3_storage={
            "bucket": "dummy-bucket",
            "region": "us-east-1",
            "endpoint": "http://dummy.endpoint:1000",
            "minio_root_user": "dummy_user",
            "minio_root_password": "dummy_password",
        },
    )


# A simple dummy response class for testing.
class DummyResponse:
    def __init__(self, status_code: int, text: str, json_data: Any = None) -> None:
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self) -> Any:
        return self._json


def dummy_post_success(
    url: str, json: Any, headers: Optional[Dict[Any, Any]] = None
) -> DummyResponse:
    # Simulate a successful POST request.
    return DummyResponse(200, "OK", {"message": "Config valid"})


def dummy_post_failure(
    url: str, json: Any, headers: Optional[Dict[Any, Any]] = None
) -> DummyResponse:
    # Simulate a failed POST request.
    return DummyResponse(400, "Error", None)


def dummy_get_success(
    url: str, params: dict, headers: Optional[Dict[Any, Any]] = None
) -> DummyResponse:
    # Simulate a successful GET request.
    return DummyResponse(200, "OK", {"id": "123", "name": "Test Project"})


def dummy_create_project(
    url: str, json: Any, headers: Optional[Dict[Any, Any]] = None
) -> DummyResponse:
    # Simulate a successful project creation.
    return DummyResponse(200, "Created", {"id": "123", "name": json.get("name")})


# Tests


def test_api_login_success(
    monkeypatch: pytest.MonkeyPatch, dummy_cli_config: CLIConfig
):
    dummy_cli_config_dict = dummy_cli_config.model_dump()
    # Write the config to a YAML file.
    with open("dummy_cli_config.yaml", "w") as f:
        yaml.dump(dummy_cli_config_dict, f)
    # Monkey-patch httpx.post with our dummy_post_success.
    monkeypatch.setattr(httpx, "post", dummy_post_success)
    # Call api_login with only the YAML file.
    result = api_login("dummy_cli_config.yaml")
    # Expect a successful login response.
    assert result.get("success") is True
    assert "CLI_config" in result


def test_api_login_failure(
    monkeypatch: pytest.MonkeyPatch, dummy_cli_config: CLIConfig
):
    dummy_cli_config_dict = dummy_cli_config.model_dump()
    # Write the config to a YAML file.
    with open("dummy_cli_config.yaml", "w") as f:
        yaml.dump(dummy_cli_config_dict, f)
    # Override httpx.post with our dummy failure function.
    monkeypatch.setattr(httpx, "post", dummy_post_failure)
    result = api_login("dummy_cli_config.yaml")
    # Expect a failure response.
    assert result.get("success") is False


def test_api_get_project_from_id(
    monkeypatch: pytest.MonkeyPatch, dummy_cli_config: CLIConfig
):
    # Override httpx.get with our dummy GET function.
    monkeypatch.setattr(httpx, "get", dummy_get_success)
    response = api_get_project_from_id("123", dummy_cli_config)
    assert response.status_code == 200
    data = response.json()
    assert data.get("id") == "123"
    assert data.get("name") == "Test Project"


def test_api_create_project(
    monkeypatch: pytest.MonkeyPatch, dummy_cli_config: CLIConfig
):
    # Override httpx.post for project creation.
    monkeypatch.setattr(httpx, "post", dummy_create_project)
    project_config = {"name": "New Project", "other_field": "value"}
    response = api_create_project(project_config, dummy_cli_config)
    assert response.status_code == 200
    data = response.json()
    assert data.get("id") == "123"
    assert data.get("name") == "New Project"
