"""
Comprehensive tests for LAN Network Manager functionality
"""

import pytest
import unittest.mock as mock
import subprocess
import json
import ipaddress
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

from dynadock.lan_network_manager import LANNetworkManager
from dynadock.exceptions import DynaDockNetworkError


class TestLANNetworkManager:
    """Test suite for LAN Network Manager"""
    
    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a temporary project directory"""
        return tmp_path / "test_project"
    
    @pytest.fixture
    def lan_manager(self, project_dir):
        """Create LAN Network Manager instance with mocked interface detection"""
        with patch.object(LANNetworkManager, '_auto_detect_interface', return_value='eth0'):
            return LANNetworkManager(project_dir)
    
    def test_init_with_interface(self, project_dir):
        """Test initialization with specified interface"""
        manager = LANNetworkManager(project_dir, "wlan0")
        assert manager.interface == "wlan0"
        assert manager.project_dir == project_dir
        assert manager.virtual_ips == []
    
    def test_init_auto_detect_interface(self, project_dir):
        """Test initialization with auto-detected interface"""
        with patch.object(LANNetworkManager, '_auto_detect_interface', return_value='eth0'):
            manager = LANNetworkManager(project_dir)
            assert manager.interface == "eth0"
    
    @patch('subprocess.check_output')
    def test_auto_detect_interface_success(self, mock_subprocess, project_dir):
        """Test successful interface auto-detection"""
        mock_subprocess.return_value = "eth0\n"
        manager = LANNetworkManager(project_dir)
        assert manager.interface == "eth0"
    
    @patch('subprocess.check_output')
    @patch.object(LANNetworkManager, '_interface_exists')
    def test_auto_detect_interface_fallback(self, mock_exists, mock_subprocess, project_dir):
        """Test interface auto-detection with fallback"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'cmd')
        mock_exists.side_effect = lambda iface: iface == 'eth0'
        
        manager = LANNetworkManager(project_dir)
        assert manager.interface == "eth0"
    
    @patch('os.geteuid')
    def test_check_root_privileges_success(self, mock_geteuid, lan_manager):
        """Test root privilege check success"""
        mock_geteuid.return_value = 0
        assert lan_manager.check_root_privileges() is True
    
    @patch('os.geteuid')
    def test_check_root_privileges_failure(self, mock_geteuid, lan_manager):
        """Test root privilege check failure"""
        mock_geteuid.return_value = 1000
        assert lan_manager.check_root_privileges() is False
    
    @patch('subprocess.check_output')
    def test_get_network_details_success(self, mock_subprocess, lan_manager):
        """Test successful network details retrieval"""
        mock_subprocess.return_value = "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> inet 192.168.1.10/24"
        
        ip, network, cidr, broadcast = lan_manager.get_network_details()
        
        assert ip == "192.168.1.10"
        assert network == "192.168.1.0"
        assert cidr == "24"
        assert broadcast == "192.168.1.255"
    
    @patch('subprocess.check_output')
    def test_get_network_details_failure(self, mock_subprocess, lan_manager):
        """Test network details retrieval failure"""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'cmd')
        
        result = lan_manager.get_network_details()
        assert result == (None, None, None, None)
    
    def test_find_free_ips(self, lan_manager):
        """Test finding free IP addresses"""
        with patch.object(lan_manager, '_is_ip_available', side_effect=[False, True, True, False, True]):
            free_ips = lan_manager.find_free_ips("192.168.1.0", "24", 2, 100)
            
            # Should find 2 IPs starting from .100
            assert len(free_ips) == 2
            assert all(ip.startswith("192.168.1.") for ip in free_ips)
    
    @patch('subprocess.run')
    def test_is_ip_available_ping_responds(self, mock_run, lan_manager):
        """Test IP availability when ping responds (IP not available)"""
        mock_run.return_value.returncode = 0  # Ping successful = IP not available
        
        result = lan_manager._is_ip_available("192.168.1.100")
        assert result is False
    
    @patch('subprocess.run')
    def test_is_ip_available_no_response(self, mock_run, lan_manager):
        """Test IP availability when no response (IP available)"""
        mock_run.side_effect = [
            Mock(returncode=1),  # Ping fails
            Mock(returncode=1)   # ARP fails
        ]
        
        result = lan_manager._is_ip_available("192.168.1.100")
        assert result is True
    
    @patch('subprocess.run')
    def test_add_virtual_ip_success(self, mock_run, lan_manager):
        """Test successful virtual IP addition"""
        mock_run.return_value.returncode = 0
        
        with patch.object(lan_manager, '_announce_arp'), \
             patch.object(lan_manager, '_update_arp_cache'), \
             patch.object(lan_manager, '_save_ip_tracking'):
            
            result = lan_manager.add_virtual_ip("192.168.1.100", "test_service")
            
            assert result is True
            assert len(lan_manager.virtual_ips) == 1
            assert lan_manager.virtual_ips[0][0] == "192.168.1.100"
            assert lan_manager.virtual_ips[0][2] == "test_service"
    
    @patch('subprocess.run')
    def test_add_virtual_ip_failure(self, mock_run, lan_manager):
        """Test virtual IP addition failure"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Permission denied"
        
        result = lan_manager.add_virtual_ip("192.168.1.100", "test_service")
        
        assert result is False
        assert len(lan_manager.virtual_ips) == 0
    
    @patch.object(LANNetworkManager, 'check_root_privileges', return_value=True)
    @patch.object(LANNetworkManager, 'get_network_details', return_value=("192.168.1.10", "192.168.1.0", "24", "192.168.1.255"))
    @patch.object(LANNetworkManager, 'find_free_ips', return_value=["192.168.1.100", "192.168.1.101"])
    @patch.object(LANNetworkManager, 'add_virtual_ip', return_value=True)
    def test_setup_services_lan_success(self, mock_add_ip, mock_find_ips, mock_get_network, mock_check_root, lan_manager):
        """Test successful LAN services setup"""
        services = {"web": {}, "api": {}}
        
        result = lan_manager.setup_services_lan(services)
        
        assert len(result) == 2
        assert "web" in result
        assert "api" in result
        assert mock_add_ip.call_count == 2
    
    @patch.object(LANNetworkManager, 'check_root_privileges', return_value=False)
    def test_setup_services_lan_no_root(self, mock_check_root, lan_manager):
        """Test LAN services setup without root privileges"""
        services = {"web": {}}
        
        with pytest.raises(DynaDockNetworkError, match="Root privileges required"):
            lan_manager.setup_services_lan(services)
    
    @patch('subprocess.run')
    def test_remove_virtual_ip_success(self, mock_run, lan_manager):
        """Test successful virtual IP removal"""
        mock_run.return_value.returncode = 0
        lan_manager.virtual_ips = [("192.168.1.100", "eth0:test", "test_service")]
        
        with patch.object(lan_manager, '_save_ip_tracking'):
            result = lan_manager.remove_virtual_ip("192.168.1.100")
            
            assert result is True
            assert len(lan_manager.virtual_ips) == 0
    
    def test_cleanup_all(self, lan_manager):
        """Test cleanup all virtual IPs"""
        lan_manager.virtual_ips = [("192.168.1.100", "eth0:test", "test")]
        
        with patch.object(lan_manager, '_load_ip_tracking', return_value={'virtual_ips': [{'ip': '192.168.1.100'}]}), \
             patch.object(lan_manager, 'remove_virtual_ip', return_value=True), \
             patch.object(lan_manager.ip_tracking_file, 'exists', return_value=True), \
             patch.object(lan_manager.ip_tracking_file, 'unlink'):
            
            lan_manager.cleanup_all()
            
            assert len(lan_manager.virtual_ips) == 0
    
    def test_get_service_urls(self, lan_manager):
        """Test service URL generation"""
        service_ip_map = {"web": "192.168.1.100", "api": "192.168.1.101"}
        port_map = {"web": 8000, "api": 8001}
        
        urls = lan_manager.get_service_urls(service_ip_map, port_map)
        
        assert urls["web"] == "http://192.168.1.100:8000"
        assert urls["api"] == "http://192.168.1.101:8001"
    
    @patch('socket.create_connection')
    def test_connectivity_test_success(self, mock_socket, lan_manager):
        """Test successful connectivity test"""
        mock_socket.return_value.__enter__ = Mock()
        mock_socket.return_value.__exit__ = Mock(return_value=None)
        
        service_ip_map = {"web": "192.168.1.100"}
        port_map = {"web": 8000}
        
        results = lan_manager.test_connectivity(service_ip_map, port_map)
        
        assert results["web"] is True
    
    @patch('socket.create_connection')
    def test_connectivity_test_failure(self, mock_socket, lan_manager):
        """Test connectivity test failure"""
        mock_socket.side_effect = OSError("Connection refused")
        
        service_ip_map = {"web": "192.168.1.100"}
        port_map = {"web": 8000}
        
        results = lan_manager.test_connectivity(service_ip_map, port_map)
        
        assert results["web"] is False
    
    def test_save_and_load_ip_tracking(self, lan_manager):
        """Test IP tracking save and load functionality"""
        lan_manager.virtual_ips = [("192.168.1.100", "eth0:test", "test_service")]
        
        with patch('builtins.open', mock.mock_open()), \
             patch('json.dump') as mock_json_dump, \
             patch('json.load') as mock_json_load:
            
            # Test save
            lan_manager._save_ip_tracking()
            mock_json_dump.assert_called_once()
            
            # Test load
            mock_json_load.return_value = {'virtual_ips': [{'ip': '192.168.1.100'}]}
            result = lan_manager._load_ip_tracking()
            assert 'virtual_ips' in result


class TestLANNetworkManagerIntegration:
    """Integration tests for LAN Network Manager (require root privileges)"""
    
    @pytest.mark.integration
    @pytest.mark.skipif(not Path('/proc/sys/net/ipv4/ip_forward').exists(), 
                       reason="Integration tests require Linux network stack")
    def test_network_detection_integration(self, tmp_path):
        """Integration test for network detection"""
        manager = LANNetworkManager(tmp_path)
        
        # Should auto-detect interface without error
        assert manager.interface is not None
        assert len(manager.interface) > 0
    
    @pytest.mark.integration
    @pytest.mark.skipif(not Path('/proc/sys/net/ipv4/ip_forward').exists(), 
                       reason="Integration tests require Linux network stack")
    def test_get_network_details_integration(self, tmp_path):
        """Integration test for network details retrieval"""
        manager = LANNetworkManager(tmp_path)
        
        ip, network, cidr, broadcast = manager.get_network_details()
        
        # Should detect real network configuration
        if ip:  # Only test if network interface is available
            assert ipaddress.IPv4Address(ip)
            assert ipaddress.IPv4Network(f"{network}/{cidr}")


class TestLANNetworkManagerErrorHandling:
    """Test error handling in LAN Network Manager"""
    
    def test_interface_not_found_error(self, tmp_path):
        """Test error when interface is not found"""
        with patch.object(LANNetworkManager, '_auto_detect_interface') as mock_detect, \
             patch.object(LANNetworkManager, '_interface_exists', return_value=False):
            
            mock_detect.side_effect = DynaDockNetworkError("No suitable network interface found")
            
            with pytest.raises(DynaDockNetworkError):
                LANNetworkManager(tmp_path)
    
    def test_network_config_parse_error(self, lan_manager):
        """Test error when network configuration cannot be parsed"""
        with patch('subprocess.check_output', return_value="invalid output"):
            
            result = lan_manager.get_network_details()
            assert result == (None, None, None, None)
    
    def test_insufficient_ips_error(self, lan_manager):
        """Test error when not enough IPs are available"""
        with patch.object(lan_manager, '_is_ip_available', return_value=False):
            
            free_ips = lan_manager.find_free_ips("192.168.1.0", "24", 5, 100)
            assert len(free_ips) == 0


if __name__ == '__main__':
    pytest.main([__file__])
