from app.security.policies import is_path_allowed, is_path_blocked


def test_path_traversal_detection():
    """Verify directory traversal patterns are blocked."""
    malicious_paths = [
        "../../Windows/System32",
        "..\\..\\Windows\\System32\\cmd.exe",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "/etc/passwd",
        "/var/run/secrets",
        "data/../../../Windows",
    ]
    for path in malicious_paths:
        assert is_path_blocked(path) is True


def test_allowed_workspace_paths(tmp_path):
    """Verify safe paths within designated workspace are allowed."""
    safe_file = tmp_path / "notes.txt"
    safe_file.write_text("Safe content")
    # Path inside workspace should not be blocked
    assert is_path_blocked(str(safe_file)) is False
