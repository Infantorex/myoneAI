"""Integration test suite for Phase 11 Web Dashboard."""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from web.api.server import app


@pytest.fixture
def client():
    mock_settings = Settings(
        web_enabled=True,
        web_auth_enabled=False,
        web_auth_token="",
        web_chat_max_length=2000,
    )
    app.dependency_overrides[get_settings] = lambda: mock_settings
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_settings, None)


def test_web_static_index(client):
    """Test that frontend index.html is served."""
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text or "myoneAI" in response.text


def test_web_cors_headers(client):
    """Test local origin CORS verification."""
    response = client.options(
        "/api/system/status",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in (200, 204)
