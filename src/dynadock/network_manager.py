from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class NetworkManager:
    """Manage virtual network interfaces and IP allocation for services."""

    _SUBNET_BASE = "172.20.0."
    _IP_MAP_JSON = ".dynadock_ip_map.json"

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        # Locate scripts/ relative to repository root (src/dynadock/ -> repo/)
        repo_root = Path(__file__).resolve().parents[2]
        self.manage_veth_script = (repo_root / "scripts" / "manage_veth.sh").resolve()
        self.ip_map_json_path = self.project_dir / self._IP_MAP_JSON
        self.env_dir = self.project_dir / ".dynadock"
        self.env_dir.mkdir(exist_ok=True)
        self.ip_map_env_path = self.env_dir / "ip_map.env"

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

        subprocess.run(["sudo", str(self.manage_veth_script), "up", str(self.ip_map_env_path)], check=True)
        return ip_map

    def teardown_interfaces(self, domain: str) -> None:
        """Remove all managed virtual network interfaces."""
        ip_map = self._load_ip_map()
        if not self.ip_map_env_path.exists() and not ip_map:
            return

        subprocess.run(["sudo", str(self.manage_veth_script), "down", str(self.ip_map_env_path)], check=True)
        
        self.ip_map_env_path.unlink(missing_ok=True)
