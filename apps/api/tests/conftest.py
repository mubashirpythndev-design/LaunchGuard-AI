"""Pytest fixtures for LaunchGuard AI API testing."""
import socket
from pathlib import Path

import pytest

FIXTURES_IMAGES = Path(__file__).resolve().parent / "fixtures" / "images"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_IMAGES


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block outbound socket connections to verify zero-network offline execution."""
    original_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: tuple[str, int]) -> None:
        host, port = address
        # Allow loopback connections only
        if host in ("localhost", "127.0.0.1", "::1"):
            return original_connect(self, address)
        raise RuntimeError(f"Outbound network access to {host}:{port} is prohibited by test policy")

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
