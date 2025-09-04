"""Pytest configuration and reusable fixtures for DynaDock tests."""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
from pathlib import Path
from types import GeneratorType
from unittest.mock import Mock, patch

import docker
import pytest

# ---------------------------------------------------------------------------
# Test path setup – make sure `src/` is importable when tests are invoked from
# the project root (e.g. on CI) or inside an isolated filesystem.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


# ---------------------------------------------------------------------------
# Generic fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_dir() -> GeneratorType[Path, None, None]:
    """Return a temporary directory path that is cleaned up afterwards."""
    tmp_path = Path(tempfile.mkdtemp())
    try:
        yield tmp_path
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture()
def mock_docker_client() -> GeneratorType[Mock, None, None]:
    """Patch ``docker.from_env`` so no real Docker daemon is required."""
    with patch("docker.from_env") as patched:
        client = Mock(spec=docker.DockerClient)
        patched.return_value = client
        yield client


# ---------------------------------------------------------------------------
# Network-heavy integration tests (optional, skipped if Docker not available)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def docker_client():
    """Return real Docker client if daemon is available, otherwise skip."""
    try:
        _client = docker.from_env()
        _client.ping()  # type: ignore[attr-defined]
        return _client
    except Exception:  # pragma: no cover – CI w/o docker
        pytest.skip("Docker daemon not available – skipping integration tests")


@pytest.fixture()
def cleanup_docker(docker_client):  # noqa: ANN001 – dynamic fixture
    """Collect containers/networks/volumes created in test and remove them."""
    resources: dict[str, list[str]] = {"containers": [], "networks": [], "volumes": []}
    yield resources

    # --- tear-down ----------------------------------------------------------
    for container_id in resources["containers"]:
        try:
            docker_client.containers.get(container_id).remove(force=True)  # type: ignore[attr-defined]
        except Exception:
            pass
    for network_id in resources["networks"]:
        try:
            docker_client.networks.get(network_id).remove()  # type: ignore[attr-defined]
        except Exception:
            pass
    for volume_id in resources["volumes"]:
        try:
            docker_client.volumes.get(volume_id).remove(force=True)  # type: ignore[attr-defined]
        except Exception:
            pass
