from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class NetworkManager:
    """Manage virtual network interfaces, IP allocation, and /etc/hosts entries for services."""

    _SUBNET_BASE = "172.20.0."
    _IP_MAP_FILE = ".dynadock_ip_map.json"

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.manage_veth_script = Path("/home/tom/github/dynapsys/dynadock/scripts/manage_veth.sh").resolve()
        self.ip_map_path = self.project_dir / self._IP_MAP_FILE

    def _load_ip_map(self) -> Dict[str, str]:
        """Load the service-to-IP mapping from file."""
        if not self.ip_map_path.exists():
            return {}
        with self.ip_map_path.open("r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

    def _save_ip_map(self, ip_map: Dict[str, str]) -> None:
        """Save the service-to-IP mapping to file."""
        with self.ip_map_path.open("w") as f:
            json.dump(ip_map, f, indent=2)

    def _update_hosts_file(self, ip_map: Dict[str, str], domain: str, remove: bool = False) -> None:
        """Add or remove entries from /etc/hosts using a sed script."""
        marker_start = "# BEGIN DYNADOCK BLOCK"
        marker_end = "# END DYNADOCK BLOCK"
        script_path = self.project_dir / ".dynadock_update_hosts.sh"

        # First, ensure the block is removed to avoid duplicates or stale entries
        sed_script_remove = f"/^{marker_start}$/,/^{marker_end}$/d"
        
        script_content = [
            "#!/bin/bash",
            "set -e",
            f"sed -i.bak '{sed_script_remove}' /etc/hosts",
        ]

        # If adding entries, create the new block
        if not remove:
            hosts_block = [f"\n{marker_start}"]
            for service, ip in ip_map.items():
                hosts_block.append(f"{ip}\t{service}.{domain}")
            hosts_block.append(f"{marker_end}\n")
            
            # Append the new block to /etc/hosts
            block_str = "\n".join(hosts_block)
            script_content.append(f"echo -e '{block_str}' >> /etc/hosts")

        try:
            # Write the script and make it executable
            with open(script_path, "w") as f:
                f.write("\n".join(script_content))
            script_path.chmod(0o755)

            # Execute the script with sudo
            subprocess.run(["sudo", str(script_path)], check=True)
        finally:
            # Clean up the script file
            script_path.unlink(missing_ok=True)

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

        with open(self.ip_map_path, 'w') as f:
            for service, ip in ip_map.items():
                f.write(f"{service}={ip}\n")

        subprocess.run(["sudo", str(self.manage_veth_script), "up", str(self.ip_map_path)], check=True)
        self._update_hosts_file(ip_map, domain)
        return ip_map

    def teardown_interfaces(self, domain: str) -> None:
        """Remove all managed virtual network interfaces."""
        ip_map = self._load_ip_map()
        if not self.ip_map_path.exists() and not ip_map:
            return

        subprocess.run(["sudo", str(self.manage_veth_script), "down", str(self.ip_map_path)], check=True)
        if ip_map:
            self._update_hosts_file(ip_map, domain, remove=True)
        
        self.ip_map_path.unlink(missing_ok=True)
