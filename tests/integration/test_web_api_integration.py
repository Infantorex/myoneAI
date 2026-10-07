from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from web.api.server import app, create_app


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


def test_web_api_health_and_telemetry(client):
    """Verify health endpoint and system status endpoints."""
    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Telemetry snapshot
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "disk_percent" in data


def test_web_api_chat_endpoint(client):
    """Verify chat endpoint processes text and returns structured response."""
    with patch("web.api.routes.chat.conversation_manager.respond", new_callable=AsyncMock) as mock_respond:
        mock_respond.return_value = "வணக்கம் Infanto!"
        payload = {"message": "வணக்கம் JARVIS"}
        res = client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["response"] == "வணக்கம் Infanto!"
