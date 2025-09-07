"""Wrapper around *docker-compose* and Docker SDK used by DynaDock.

The class primarily operates via the *docker-compose* CLI because that is the
lowest-common-denominator that will work in virtually every environment. For a
few helper operations – such as querying running containers – we fall back to
*docker-py* which offers a richer Python API.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import logging

import docker
import yaml

from .port_allocator import PortAllocator

logger = logging.getLogger('dynadock.docker_manager')

__all__ = ["DockerManager"]

_LOGGED_ENV_VARS = (
    "DYNADOCK_DOMAIN",
    "DYNADOCK_PROTOCOL",
    "DYNADOCK_ENABLE_TLS",
)


def _run(
    cmd: List[str],
    *,
    cwd: str | Path | None = None,
    env: Dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with some sensible defaults."""
    logger.debug(f"🔨 Running command: {' '.join(cmd)}")
    if cwd:
        logger.debug(f"📁 Working directory: {cwd}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.debug(f"✅ Command completed successfully: {cmd[0]}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Command failed: {' '.join(cmd)}")
        logger.error(f"💥 Error: {e.stderr}")
        raise


class DockerManager:  # pylint: disable=too-many-public-methods
    """Orchestrate *docker-compose* lifecycle on behalf of DynaDock."""

    def __init__(self, compose_file: str | Path, project_dir: Path | None = None, env_file: str | None = None):
        self.compose_file = str(compose_file)
        self.project_dir = Path(project_dir or Path(compose_file).parent).resolve()
        self.env_file = env_file
        self.client = docker.from_env()  # heavy import but only used on demand
        
        logger.info(f"🐳 DockerManager initialized")
        logger.debug(f"📄 Compose file: {self.compose_file}")
        logger.debug(f"📁 Project directory: {self.project_dir}")
        logger.debug(f"🔧 Env file: {self.env_file}")
        self.project_name = self._get_project_name()
        # Determine compose command (docker-compose or docker compose)
        if shutil.which("docker-compose"):
            self._compose_base = ["docker-compose"]
        elif shutil.which("docker"):
            # Verify that docker compose exists (plugin)
            try:
                subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
                self._compose_base = ["docker", "compose"]
            except Exception:
                # Fallback to docker-compose name (will fail later with clearer error from preflight)
                self._compose_base = ["docker-compose"]
        else:
            self._compose_base = ["docker-compose"]
        print(f"[dynadock] Using compose command: {' '.join(self._compose_base)}")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_project_name(self) -> str:
        """Derive a compose project name from the directory name."""
        return (
            self.project_dir.name.lower().replace("_", "").replace("-", "")
        )[:50]  # compose limits name length

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    # Parsing ----------------------------------------------------------------
    def parse_compose(self) -> Dict[str, Any]:
        """Return the *services* mapping from the compose YAML."""
        with open(self.compose_file, "r", encoding="utf-8") as fp:
            compose_data = yaml.safe_load(fp)
        return compose_data.get("services", {})  # type: ignore[return-value]

    # Port allocation --------------------------------------------------------
    def allocate_ports(
        self, services: Dict[str, Any], start_port: int = 8000
    ) -> Dict[str, int]:
        allocator = PortAllocator(start_port)
        ports: Dict[str, int] = {}
        for svc_name, svc_cfg in services.items():
            if "ports" in svc_cfg or "expose" in svc_cfg:
                ports[svc_name] = allocator.get_free_port()
        return ports

    # Compose wrappers -------------------------------------------------------
    def _compose_cmd(self, *args: str) -> List[str]:
        cmd = [
            *self._compose_base,
            "-f",
            self.compose_file,
            "-p",
            self.project_name,
        ]
        if self.env_file and Path(self.env_file).exists():
            cmd.extend(["--env-file", self.env_file])
        cmd.extend(args)
        return cmd

    def up(self, env_vars: Dict[str, str], *, detach: bool = True) -> List[Any]:
        env = os.environ.copy()
        env.update(env_vars)

        # Log selected env vars for debugging
        for key in _LOGGED_ENV_VARS:
            if key in env:
                print(f"[dynadock] {key}={env[key]}")  # noqa: T201 – small debug aid

        cmd_args = ["up", "-d"] if detach else ["up"]
        cmd = self._compose_cmd(*cmd_args)
        result = _run(cmd, cwd=self.project_dir, env=env)
        if result.returncode != 0:
            raise RuntimeError(
                "docker-compose up failed:\n" + (result.stderr or result.stdout)
            )
        return self.ps()

    def down(self, *, remove_volumes: bool = False, remove_images: bool = False) -> None:
        cmd = self._compose_cmd("down")
        if remove_volumes:
            cmd.append("-v")
        if remove_images:
            cmd.extend(["--rmi", "all"])
        result = _run(cmd, cwd=self.project_dir)
        if result.returncode != 0:
            # _run redirects stderr to stdout
            raise RuntimeError("docker-compose down failed:\n" + result.stdout)

    def ps(self) -> List[Any]:  # noqa: D401 – returns docker objects
        filters = {"label": f"com.docker.compose.project={self.project_name}"}
        return self.client.containers.list(filters=filters)

    def logs(self, service: Optional[str] = None, *, follow: bool = True) -> None:
        cmd = self._compose_cmd("logs")
        if follow:
            cmd.append("-f")
        if service:
            cmd.append(service)
        subprocess.run(cmd, cwd=self.project_dir)  # noqa: S603 – CLI pass-through

    def exec(self, service: str, command: str) -> None:  # noqa: D401
        cmd = self._compose_cmd("exec", service, command)
        subprocess.run(cmd, cwd=self.project_dir)  # noqa: S603 – CLI pass-through
