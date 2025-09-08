from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any

from pyroute2 import IPDB

from .log_config import setup_logging

def setup_interfaces(ip_map_json: str) -> None:
    """Create virtual network interfaces based on a JSON map."""
    ip_map = json.loads(ip_map_json)
    with IPDB() as ipdb:
        for service, ip in ip_map.items():
            veth_name = f"veth_{service}"
            peer_name = f"peer_{service}"

            if iface in [veth_name, peer_name]:
                if iface in ipdb.interfaces:
                    ipdb.interfaces[iface].remove().commit()

            ipdb.create(ifname=veth_name, kind='veth', peer=peer_name).commit()
            with ipdb.interfaces[veth_name] as veth:
                veth.add_ip(f"{ip}/24")
                veth.up()
            with ipdb.interfaces[peer_name] as peer:
                peer.up()

def teardown_interfaces(ip_map_json: str) -> None:
    """Remove virtual network interfaces based on a JSON map."""
    ip_map = json.loads(ip_map_json)
    with IPDB() as ipdb:
        for service in ip_map.keys():
            veth_name = f"veth_{service}"
            if veth_name in ipdb.interfaces:
                ipdb.interfaces[veth_name].remove().commit()


if __name__ == "__main__":
    setup_logging()
    command = sys.argv[1]
    ip_map_arg = sys.argv[2]

    if command == "up":
        setup_interfaces(ip_map_arg)
    elif command == "down":
        teardown_interfaces(ip_map_arg)
    else:
        sys.exit(1)
