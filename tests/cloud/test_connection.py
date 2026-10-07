"""Unit tests for CloudConnection state and TLS enforcement (Phase 12)."""

import pytest

from app.cloud.connection import CloudConnection, ConnectionState
from app.cloud.errors import CloudConnectionError, CloudSecurityError
from app.core.config import Settings


def test_connection_state_transitions():
    """Test connection state changes."""
    conn = CloudConnection()
    assert conn.state == ConnectionState.DISCONNECTED
    assert conn.is_connected is False

    conn.set_state(ConnectionState.CONNECTING)
    assert conn.state == ConnectionState.CONNECTING

    conn.set_state(ConnectionState.CONNECTED)
    assert conn.is_connected is True

    conn.set_state(ConnectionState.ERROR, "Network timeout")
    assert conn.state == ConnectionState.ERROR
    assert conn.is_connected is False


def test_missing_cloud_api_url():
    """Test error raised when cloud URL is missing."""
    settings = Settings(cloud_api_url="")
    conn = CloudConnection(settings=settings)
    with pytest.raises(CloudConnectionError, match="CLOUD_API_URL is not configured"):
        conn._get_base_url()


def test_tls_enforcement_for_public_domains():
    """Test that HTTP on public domain raises CloudSecurityError when TLS is required."""
    settings = Settings(cloud_api_url="http://myoneai-control-plane.vercel.app", cloud_tls_required=True)
    conn = CloudConnection(settings=settings)
    with pytest.raises(CloudSecurityError, match="CLOUD_TLS_REQUIRED is enabled"):
        conn._get_base_url()


def test_tls_allowed_for_localhost():
    """Test that HTTP is allowed on 127.0.0.1 for local testing even with TLS required."""
    settings = Settings(cloud_api_url="http://127.0.0.1:8000", cloud_tls_required=True)
    conn = CloudConnection(settings=settings)
    assert conn._get_base_url() == "http://127.0.0.1:8000"
