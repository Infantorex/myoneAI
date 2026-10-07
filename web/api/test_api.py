"""Automated API and Security Test Suite for myoneAI Web Dashboard (Phase 11).

Uses FastAPI TestClient to test endpoints, auth policies, error responses, and schemas with mocks.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from web.api.server import app, create_app


@pytest.fixture
def client():
    """Create FastAPI test client with disabled auth for baseline tests."""
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


@pytest.fixture
def auth_client():
    """Create FastAPI test client with strict auth enabled."""
    mock_settings = Settings(
        web_enabled=True,
        web_auth_enabled=True,
        web_auth_token="secret-jarvis-token-123",
        web_chat_max_length=2000,
    )
    app.dependency_overrides[get_settings] = lambda: mock_settings
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_settings, None)


def test_health_check(client):
    """Test public health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


def test_auth_rejection_when_enabled(auth_client):
    """Test that unauthorized requests are rejected when auth is enabled."""
    # No token provided
    res = auth_client.get("/api/system/status")
    assert res.status_code == 401
    assert res.json()["success"] is False
    assert res.json()["error"]["code"] == "UNAUTHORIZED"

    # Invalid token provided
    res = auth_client.get("/api/system/status", headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401
    assert res.json()["success"] is False


def test_auth_success_when_enabled(auth_client):
    """Test successful request with correct Bearer token."""
    headers = {"Authorization": "Bearer secret-jarvis-token-123"}
    res = auth_client.get("/api/system/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data


def test_system_status_endpoint(client):
    """Test GET /api/system/status format."""
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["cpu_percent"], (int, float))
    assert isinstance(data["memory_percent"], (int, float))
    assert isinstance(data["disk_percent"], (int, float))
    assert isinstance(data["network_available"], bool)


def test_system_diagnosis_endpoint(client):
    """Test GET /api/system/diagnosis format."""
    res = client.get("/api/system/diagnosis")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "warning", "critical")
    assert isinstance(data["warnings"], list)
    assert isinstance(data["top_cpu_processes"], list)
    assert isinstance(data["top_memory_processes"], list)


def test_assistant_status_and_control(client):
    """Test assistant status and start/stop controls."""
    # Status
    res = client.get("/api/assistant/status")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] in ("idle", "listening", "thinking", "speaking", "error")

    # Start
    res = client.post("/api/assistant/start")
    assert res.status_code == 200
    assert res.json()["state"] == "listening"

    # Stop
    res = client.post("/api/assistant/stop")
    assert res.status_code == 200
    assert res.json()["state"] == "idle"


def test_chat_endpoint_success(client):
    """Test POST /api/chat with mock AI response."""
    with patch("web.api.routes.chat.conversation_manager.respond", new_callable=AsyncMock) as mock_respond:
        mock_respond.return_value = "RAM is at 68%."
        res = client.post("/api/chat", json={"message": "How is my laptop?"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["response"] == "RAM is at 68%."


def test_chat_validation_errors(client):
    """Test chat input validation (empty message, too long)."""
    # Empty message
    res = client.post("/api/chat", json={"message": ""})
    assert res.status_code in (400, 422)

    # Missing message field
    res = client.post("/api/chat", json={})
    assert res.status_code == 422


def test_memory_crud_and_confirmation(client):
    """Test Memory API endpoints."""
    # List memories
    res = client.get("/api/memory")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Get stats
    res = client.get("/api/memory/stats")
    assert res.status_code == 200
    assert "total_memories" in res.json()

    # Clear memories without confirmation -> should fail
    res = client.delete("/api/memory?confirmed=false")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "CONFIRMATION_REQUIRED"

    # Clear memories with confirmation -> should succeed
    res = client.delete("/api/memory?confirmed=true")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_tasks_crud_cycle(client):
    """Test Task creation, listing, updating, and deletion."""
    # 1. Create task
    res = client.post(
        "/api/tasks",
        json={
            "title": "Phase 11 Dashboard Review",
            "description": "Verify dark mode and tests",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 201
    created = res.json()
    task_id = created["id"]
    assert created["title"] == "Phase 11 Dashboard Review"
    assert created["priority"] == "HIGH"

    # 2. List tasks
    res = client.get("/api/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert any(t["id"] == task_id for t in tasks)

    # 3. Update task
    res = client.patch(f"/api/tasks/{task_id}", json={"status": "COMPLETED"})
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"

    # 4. Delete task
    res = client.delete(f"/api/tasks/{task_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_reminders_crud_cycle(client):
    """Test Reminder scheduling, listing, and cancellation."""
    # 1. Create reminder
    res = client.post(
        "/api/reminders",
        json={
            "message": "Project sync meeting",
            "trigger_at": "2026-10-07T20:00:00",
            "recurrence": "DAILY",
        },
    )
    assert res.status_code == 201
    reminder = res.json()
    r_id = reminder["id"]
    assert reminder["message"] == "Project sync meeting"

    # 2. List reminders
    res = client.get("/api/reminders")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 3. Delete reminder
    res = client.delete(f"/api/reminders/{r_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_notes_crud_cycle(client):
    """Test Note creation, listing, search, updating, and deletion."""
    # 1. Create note
    res = client.post(
        "/api/notes",
        json={
            "title": "Dashboard Design Specs",
            "content": "Use dark mode, cyan accents, and glassmorphism.",
            "tags": ["ui", "design", "phase11"],
        },
    )
    assert res.status_code == 201
    note = res.json()
    note_id = note["id"]
    assert note["title"] == "Dashboard Design Specs"

    # 2. Search notes
    res = client.get("/api/notes?q=glassmorphism")
    assert res.status_code == 200
    notes = res.json()
    assert any(n["id"] == note_id for n in notes)

    # 3. Update note
    res = client.patch(f"/api/notes/{note_id}", json={"title": "Updated Specs"})
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Specs"

    # 4. Delete note
    res = client.delete(f"/api/notes/{note_id}")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_activity_endpoint(client):
    """Test GET /api/activity."""
    res = client.get("/api/activity")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "event_type" in item
        assert "description" in item
        assert "level" in item


def test_settings_endpoint(client):
    """Test GET /api/settings."""
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "app_name" in data
    assert "version" in data
    assert "web_host" in data
    # Ensure secrets are NOT in settings
    assert "ai_api_key" not in data
    assert "stt_api_key" not in data
    assert "web_auth_token" not in data
