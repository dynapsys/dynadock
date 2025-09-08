import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any

from pyroute2 import IPDB

from dynadock.log_config import setup_logging

logger = logging.getLogger('dynadock.network_helper')

def setup_interfaces(ip_map_json: str) -> None:
    """Create virtual network interfaces based on a JSON map."""
    ip_map = json.loads(ip_map_json)
    logger.info(f"Setting up interfaces for: {list(ip_map.keys())}")
    with IPDB() as ipdb:
        for service, ip in ip_map.items():
            veth_name = f"veth_{service}"
            peer_name = f"peer_{service}"

            for iface_name in [veth_name, peer_name]:
                if iface_name in ipdb.interfaces:
                    logger.debug(f"Removing existing interface: {iface_name}")
                    ipdb.interfaces[iface_name].remove().commit()

            ipdb.create(ifname=veth_name, kind='veth', peer=peer_name).commit()
            logger.debug(f"Created veth pair: {veth_name} <-> {peer_name}")
            with ipdb.interfaces[veth_name] as veth:
                veth.add_ip(f"{ip}/24")
                veth.up()
            with ipdb.interfaces[peer_name] as peer:
                peer.up()
    logger.info("Interfaces configured successfully.")

def teardown_interfaces(ip_map_json: str) -> None:
    """Remove virtual network interfaces based on a JSON map."""
    ip_map = json.loads(ip_map_json)
    logger.info(f"Tearing down interfaces for: {list(ip_map.keys())}")
    with IPDB() as ipdb:
        for service in ip_map.keys():
            veth_name = f"veth_{service}"
            if veth_name in ipdb.interfaces:
                logger.debug(f"Removing interface: {veth_name}")
                ipdb.interfaces[veth_name].remove().commit()
    logger.info("Interfaces torn down successfully.")


if __name__ == "__main__":
    # Note: This script is executed with sudo, so logging needs to be re-initialized.
    setup_logging()
    try:
        command = sys.argv[1]
        ip_map_arg = sys.argv[2]

        if command == "up":
            setup_interfaces(ip_map_arg)
        elif command == "down":
            teardown_interfaces(ip_map_arg)
        else:
            logger.error(f"Unknown command: {command}")
            sys.exit(1)
    except Exception as e:
        logger.critical(f"An error occurred in network_helper: {e}", exc_info=True)
        # Write error to stderr to be captured by the main process
        print(f"Helper script failed: {e}", file=sys.stderr)
        sys.exit(1)
