from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from importlib.resources import files, as_file
import logging

logger = logging.getLogger('dynadock.network_manager')

class NetworkManager:
    """Manage virtual network interfaces and IP allocation for services."""

    _SUBNET_BASE = "172.20.0."
    _IP_MAP_JSON = ".dynadock_ip_map.json"

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # Use packaged resource for manage_veth.sh to work from PyPI installs
        self._manage_veth_resource = files("dynadock.resources").joinpath("manage_veth.sh")
        self.ip_map_json_path = self.project_dir / self._IP_MAP_JSON
        self.env_dir = self.project_dir / ".dynadock"
        self.env_dir.mkdir(exist_ok=True)
        self.ip_map_env_path = self.env_dir / "ip_map.env"
        
        logger.info(f"🌐 NetworkManager initialized for project: {project_dir}")
        logger.debug(f"📍 IP map file: {self.ip_map_json_path}")
        logger.debug(f"📁 Environment directory: {self.env_dir}")

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

    def setup_interfaces(self, services: Dict[str, Any], domain: str) -> Dict[str, str]:
        """Create virtual network interfaces for all services."""
        service_names = list(services.keys())
        ip_map = self.allocate_ips(service_names)

        # write env mapping for manage_veth
        with open(self.ip_map_env_path, 'w') as f:
            for service, ip in ip_map.items():
                f.write(f"{service}={ip}\n")

        # Access resource as a real file path and execute via bash
        try:
            with as_file(self._manage_veth_resource) as script_path:
                subprocess.run(["sudo", "bash", str(script_path), "up", str(self.ip_map_env_path)], check=True)
        except subprocess.CalledProcessError as e:
            # If script fails, return empty dict to signal fallback to hosts mode
            return {}
        return ip_map

    def teardown_interfaces(self, domain: str) -> None:
        """Remove all managed virtual network interfaces."""
        ip_map = self._load_ip_map()
        if not self.ip_map_env_path.exists() and not ip_map:
            return

        with as_file(self._manage_veth_resource) as script_path:
            subprocess.run(["sudo", "bash", str(script_path), "down", str(self.ip_map_env_path)], check=True)
        
        self.ip_map_env_path.unlink(missing_ok=True)
