"""Dynamic TCP port allocation helper used by DynaDock.

This helper scans all currently *LISTEN* ports on the system at import time
(using *psutil*) and then hands out free ports in the configured range.
"""

from __future__ import annotations

import socket
from typing import Set
import logging

import psutil

logger = logging.getLogger("dynadock.port_allocator")

__all__ = [
    "PortAllocator",
]


class PortAllocator:
    """Allocate free TCP ports inside a given range.

    Parameters
    ----------
    start_port:
        The first port to try when looking for a free port.
    end_port:
        The last port (inclusive) that may be returned.  Defaults to *9999*.
    """

    def __init__(self, start_port: int = 8000, end_port: int = 9999):
        logger.info(f"🔌 PortAllocator initialized - range: {start_port}-{end_port}")
        if start_port < 1 or end_port > 65535:
            raise ValueError("Port range must be within 1-65535")
        if start_port >= end_port:
            raise ValueError("start_port must be lower than end_port")

        self.start_port = start_port
        self.end_port = end_port
        self.allocated_ports: Set[int] = set()
        self._scan_used_ports()

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------

    def _scan_used_ports(self) -> None:
        """Populate *self.allocated_ports* with ports currently in use."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.status == psutil.CONN_LISTEN:
                self.allocated_ports.add(conn.laddr.port)

    def _is_port_free_os(self, port: int) -> bool:
        """Try binding *port* to check if the OS considers it available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                return False
        return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_port_free(self, port: int) -> bool:
        """Return ``True`` if *port* is free and not yet allocated."""
        if port in self.allocated_ports:
            return False
        return self._is_port_free_os(port)

    def get_free_port(self) -> int:
        """Return the next available free port and mark it as allocated."""
        for port in range(self.start_port, self.end_port + 1):
            if self.is_port_free(port):
                self.allocated_ports.add(port)
                return port
        raise RuntimeError(
            f"No free ports available in range {self.start_port}-{self.end_port}"
        )

    def release_port(self, port: int) -> None:
        """Release *port* so that it can be handed out again later."""
        self.allocated_ports.discard(port)
