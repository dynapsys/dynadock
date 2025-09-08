from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import logging

from pyroute2 import IPDB, NetNS

from .log_config import setup_logging

logger = logging.getLogger('dynadock.network_manager')


class NetworkManager:
    """Manage virtual network interfaces and IP allocation for services using pyroute2."""

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

    def setup_interfaces(self, services: Dict[str, Any], domain: str) -> Dict[str, str]:
        """Create virtual network interfaces for all services."""
        setup_logging()  # Ensure logging is configured in sudo context
        service_names = list(services.keys())
        ip_map = self.allocate_ips(service_names)

        try:
            with IPDB() as ipdb:
                for service, ip in ip_map.items():
                    veth_name = f"veth_{service}"
                    peer_name = f"peer_{service}"

                    # Clean up old interfaces first
                    for iface in [veth_name, peer_name]:
                        if iface in ipdb.interfaces:
                            ipdb.interfaces[iface].remove().commit()
                            logger.debug(f"Removed existing interface: {iface}")

                    # Create veth pair
                    ipdb.create(ifname=veth_name, kind='veth', peer=peer_name).commit()
                    logger.info(f"Created veth pair: {veth_name} <-> {peer_name}")

                    # Configure the host-side interface
                    with ipdb.interfaces[veth_name] as veth:
                        veth.add_ip(f"{ip}/24")
                        veth.up()
                    
                    # Configure the peer interface (can be moved to a netns later)
                    with ipdb.interfaces[peer_name] as peer:
                        peer.up()

            return ip_map
        except Exception as e:
            logger.error(f"❌ Failed to set up network interfaces using pyroute2: {e}")
            # Attempt to clean up on failure
            self.teardown_interfaces(domain)
            return {}

    def teardown_interfaces(self, domain: str) -> None:
        """Remove all managed virtual network interfaces."""
        setup_logging()  # Ensure logging is configured in sudo context
        ip_map = self._load_ip_map()
        if not ip_map:
            return

        logger.info("🧹 Tearing down virtual network interfaces...")
        try:
            with IPDB() as ipdb:
                for service in ip_map.keys():
                    veth_name = f"veth_{service}"
                    if veth_name in ipdb.interfaces:
                        ipdb.interfaces[veth_name].remove().commit()
                        logger.info(f"Removed interface: {veth_name}")
        except Exception as e:
            logger.error(f"❌ Failed to tear down network interfaces: {e}")

        # Clean up tracking file
        self.ip_map_json_path.unlink(missing_ok=True)
