from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import logging

from .log_config import setup_logging

logger = logging.getLogger('dynadock.network_manager')


class NetworkManager:
    """Manage virtual network interfaces by invoking a helper script with sudo."""

    _SUBNET_BASE = "172.20.0."
    _IP_MAP_JSON = ".dynadock_ip_map.json"

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.ip_map_json_path = self.project_dir / self._IP_MAP_JSON
        logger.info(f"🌐 NetworkManager initialized for project: {project_dir}")

    def _load_ip_map(self) -> Dict[str, str]:
        """Load the service-to-IP mapping from file."""
        if not self.ip_map_json_path.exists():
            return {}
        with self.ip_map_json_path.open("r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _save_ip_map(self, ip_map: Dict[str, str]) -> None:
        """Save the service-to-IP mapping to file."""
        with self.ip_map_json_path.open("w") as f:
            json.dump(ip_map, f, indent=2)

    def allocate_ips(self, services: List[str]) -> Dict[str, str]:
        """Allocate a unique IP address for each service."""
        ip_map = {}
        for i, service in enumerate(services):
            ip_map[service] = f"{self._SUBNET_BASE}{10 + i}"
        self._save_ip_map(ip_map)
        return ip_map

    def _run_helper(self, command: str, ip_map: Dict[str, str]) -> bool:
        """Run the network_helper.py script with sudo, ensuring the correct python environment."""
        setup_logging()
        try:
            ip_map_json = json.dumps(ip_map)
            python_executable = sys.executable
            
            # Construct the PYTHONPATH from the current environment to pass to sudo
            # This ensures that the virtualenv's site-packages is available.
            python_path = ":".join(sys.path)

            cmd = [
                "sudo",
                "-E",
                f"PYTHONPATH={python_path}",
                python_executable,
                "-m",
                "dynadock.network_helper",
                command,
                ip_map_json
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Network helper script failed for command '{command}':")
            logger.error(f"   STDOUT: {e.stdout.strip()}")
            logger.error(f"   STDERR: {e.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"❌ An unexpected error occurred while running network helper: {e}")
            return False

    def setup_interfaces(self, services: Dict[str, Any], domain: str) -> Dict[str, str]:
        """Create virtual network interfaces for all services."""
        service_names = list(services.keys())
        ip_map = self.allocate_ips(service_names)

        logger.info("🚀 Setting up network interfaces via helper...")
        if self._run_helper("up", ip_map):
            logger.info("✅ Network interfaces created successfully.")
            return ip_map
        else:
            logger.error("Failed to set up network interfaces. Falling back may be necessary.")
            return {}

    def teardown_interfaces(self, domain: str) -> None:
        """Remove all managed virtual network interfaces."""
        ip_map = self._load_ip_map()
        if not ip_map:
            return

        logger.info("🧹 Tearing down virtual network interfaces via helper...")
        if self._run_helper("down", ip_map):
            logger.info("✅ Network interfaces torn down successfully.")
        else:
            logger.error("Failed to tear down network interfaces.")

        # Clean up tracking file
        self.ip_map_json_path.unlink(missing_ok=True)
