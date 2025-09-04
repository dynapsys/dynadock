"""Unit tests for PortAllocator."""
from __future__ import annotations

import socket
from unittest.mock import Mock, patch

import pytest

from dynadock.port_allocator import PortAllocator


class TestPortAllocator:
    """Test PortAllocator functionality."""

    # ------------------------------------------------------------------
    # Construction & internal helpers
    # ------------------------------------------------------------------

    def test_init(self):
        """PortAllocator should correctly persist constructor args."""
        allocator = PortAllocator(8000, 9000)
        assert allocator.start_port == 8000
        assert allocator.end_port == 9000
        assert isinstance(allocator.allocated_ports, set)

    @patch("psutil.net_connections")
    def test_scan_used_ports(self, mock_connections):
        """Verify that used ports are picked up during initial scan."""
        # Fake two listening ports returned by psutil
        from psutil import CONN_LISTEN
        
        mock_conn1 = Mock()
        mock_conn1.laddr = Mock(port=8080)
        mock_conn1.status = CONN_LISTEN
        mock_conn2 = Mock()
        mock_conn2.laddr = Mock(port=3000)
        mock_conn2.status = CONN_LISTEN
        mock_connections.return_value = [mock_conn1, mock_conn2]

        allocator = PortAllocator()
        assert 8080 in allocator.allocated_ports
        assert 3000 in allocator.allocated_ports

    # ------------------------------------------------------------------
    # Public API: is_port_free()
    # ------------------------------------------------------------------

    def test_is_port_free_allocated(self):
        """Already allocated ports should be reported as unavailable."""
        allocator = PortAllocator()
        allocator.allocated_ports.add(8080)
        assert not allocator.is_port_free(8080)

    @patch("socket.socket")
    def test_is_port_free_socket_error(self, mock_socket_class):
        """Socket bind errors should mark port as unavailable."""
        from unittest.mock import MagicMock
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        mock_socket.__exit__.return_value = None
        mock_socket.bind.side_effect = socket.error()
        mock_socket_class.return_value = mock_socket

        allocator = PortAllocator()
        assert not allocator.is_port_free(8080)

    @patch("socket.socket")
    @patch("psutil.net_connections", return_value=[])
    def test_is_port_free_success(self, _mock_connections, mock_socket_class):
        """Successful OS bind indicates free port."""
        from unittest.mock import MagicMock
        mock_socket = MagicMock()
        mock_socket.__enter__.return_value = mock_socket
        mock_socket.__exit__.return_value = None
        mock_socket.bind.return_value = None  # no error
        mock_socket_class.return_value = mock_socket

        allocator = PortAllocator()
        assert allocator.is_port_free(8080)

    # ------------------------------------------------------------------
    # Public API: get_free_port()
    # ------------------------------------------------------------------

    @patch.object(PortAllocator, "is_port_free")
    def test_get_free_port(self, mock_is_free):
        """Return first free port and register it as allocated."""
        mock_is_free.side_effect = [False, False, True]

        allocator = PortAllocator(8000, 8100)
        port = allocator.get_free_port()

        assert port == 8002
        assert port in allocator.allocated_ports

    @patch.object(PortAllocator, "is_port_free")
    def test_get_free_port_none_available(self, mock_is_free):
        """Raise RuntimeError when the whole range is occupied."""
        mock_is_free.return_value = False

        allocator = PortAllocator(8000, 8001)
        with pytest.raises(RuntimeError, match="No free ports available"):
            allocator.get_free_port()

    # ------------------------------------------------------------------
    # Public API: release_port()
    # ------------------------------------------------------------------

    def test_release_port(self):
        """Allocated port should be removed from internal registry."""
        allocator = PortAllocator()
        allocator.allocated_ports.add(8080)

        allocator.release_port(8080)
        assert 8080 not in allocator.allocated_ports

        # Releasing non-existing port must be a no-op
        allocator.release_port(9999)
