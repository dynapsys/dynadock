#!/usr/bin/env python3
"""
LAN-Visible Network Manager for DynaDock
Creates virtual IPs visible across the entire local network without DNS configuration
"""

import os
import sys
import subprocess
import socket
import time
import json
import ipaddress
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from .exceptions import DynaDockNetworkError, ErrorHandler

logger = logging.getLogger('dynadock.lan_network')

class LANNetworkManager:
    """Manages virtual IPs visible across the entire local network"""
    
    def __init__(self, project_dir: Path, interface: Optional[str] = None):
        self.project_dir = project_dir
        self.interface = interface or self._auto_detect_interface()
        self.virtual_ips = []
        self.arp_announced = []
        self.error_handler = ErrorHandler()
        
        # Ensure project dir exists and create tracking files
        self.project_dir.mkdir(exist_ok=True)
        self.ip_tracking_file = self.project_dir / ".dynadock_lan_ips.json"
        
        logger.info(f"🌐 LANNetworkManager initialized for interface: {self.interface}")
        logger.debug(f"📁 Project directory: {project_dir}")
        
    def _auto_detect_interface(self) -> str:
        """Auto-detect the active network interface"""
        try:
            # Find the default route interface
            cmd = "ip route | grep default | awk '{print $5}' | head -1"
            result = subprocess.check_output(cmd, shell=True, text=True).strip()
            
            if result:
                logger.info(f"🔍 Auto-detected network interface: {result}")
                return result
            else:
                # Fallback to common interface names
                for iface in ['eth0', 'enp0s3', 'ens33', 'wlan0']:
                    if self._interface_exists(iface):
                        logger.info(f"🔍 Using fallback interface: {iface}")
                        return iface
                        
                raise DynaDockNetworkError("No suitable network interface found")
                
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_subprocess_error(e, "detecting network interface")
            return "eth0"  # Final fallback
    
    def _interface_exists(self, interface: str) -> bool:
        """Check if network interface exists"""
        try:
            subprocess.check_output(f"ip link show {interface}", shell=True, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def check_root_privileges(self) -> bool:
        """Check if running with root privileges"""
        if os.geteuid() != 0:
            logger.error("❌ Root privileges required for LAN-visible networking")
            return False
        return True
    
    def get_network_details(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Get detailed network information for the interface"""
        try:
            cmd = f"ip addr show {self.interface}"
            result = subprocess.check_output(cmd, shell=True, text=True)
            
            # Extract IP and subnet mask
            ip_pattern = r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)'
            match = re.search(ip_pattern, result)
            
            if match:
                ip = match.group(1)
                cidr = match.group(2)
                
                # Calculate network range
                network = ipaddress.IPv4Network(f"{ip}/{cidr}", strict=False)
                
                logger.info(f"📡 Interface: {self.interface}")
                logger.info(f"📍 Current IP: {ip}/{cidr}")
                logger.info(f"🌐 Network: {network.network_address}")
                logger.info(f"📡 Broadcast: {network.broadcast_address}")
                logger.debug(f"🔢 Available hosts: {network.num_addresses - 2}")
                
                return str(ip), str(network.network_address), cidr, str(network.broadcast_address)
            
            raise DynaDockNetworkError(f"Could not parse network information for {self.interface}")
            
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_subprocess_error(e, f"getting network details for {self.interface}")
            return None, None, None, None
    
    def find_free_ips(self, base_network: str, cidr: str, num_ips: int = 3, start_range: int = 100) -> List[str]:
        """Find available IP addresses in the network"""
        network = ipaddress.IPv4Network(f"{base_network}/{cidr}", strict=False)
        free_ips = []
        checked = 0
        max_check = 50  # Limit to prevent long scans
        
        logger.info(f"🔍 Scanning for {num_ips} free IP addresses in network {network}...")
        
        for ip in network.hosts():
            # Start from a safe range (avoid DHCP conflicts)
            if int(str(ip).split('.')[-1]) < start_range:
                continue
                
            if checked >= max_check:
                logger.warning(f"⚠️ Reached maximum scan limit ({max_check} addresses)")
                break
                
            ip_str = str(ip)
            
            # Check if IP is free (ping test)
            if self._is_ip_available(ip_str):
                free_ips.append(ip_str)
                logger.debug(f"   ✅ Available: {ip_str}")
                
                if len(free_ips) >= num_ips:
                    break
            
            checked += 1
        
        if len(free_ips) < num_ips:
            logger.warning(f"⚠️ Found only {len(free_ips)} available IPs out of {num_ips} requested")
        
        return free_ips
    
    def _is_ip_available(self, ip_address: str) -> bool:
        """Check if an IP address is available using ping and ARP"""
        try:
            # Quick ping test
            ping_cmd = f"ping -c 1 -W 1 {ip_address}"
            ping_result = subprocess.run(ping_cmd, shell=True, capture_output=True)
            
            if ping_result.returncode == 0:
                return False  # IP responds, not available
            
            # Additional ARP check
            arp_cmd = f"arping -c 1 -w 1 {ip_address}"
            arp_result = subprocess.run(arp_cmd, shell=True, capture_output=True, stderr=subprocess.DEVNULL)
            
            return arp_result.returncode != 0  # No ARP response = available
            
        except Exception as e:
            logger.debug(f"Error checking IP {ip_address}: {e}")
            return False  # Assume unavailable on error
    
    def add_virtual_ip(self, ip_address: str, service_name: str, cidr: str = "24") -> bool:
        """Add a virtual IP address with full LAN visibility"""
        try:
            label = f"{self.interface}:{service_name}"
            
            # Add IP alias to interface
            cmd = f"ip addr add {ip_address}/{cidr} dev {self.interface} label {label}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise DynaDockNetworkError(f"Failed to add IP {ip_address}: {result.stderr}")
            
            # Enable IP forwarding for better visibility
            subprocess.run("echo 1 > /proc/sys/net/ipv4/ip_forward", shell=True)
            
            # Enable ARP proxy for improved network visibility
            subprocess.run(f"echo 1 > /proc/sys/net/ipv4/conf/{self.interface}/proxy_arp", shell=True)
            
            # Announce the new IP via gratuitous ARP
            self._announce_arp(ip_address)
            
            # Update ARP cache
            self._update_arp_cache(ip_address)
            
            logger.info(f"✅ Added virtual IP: {ip_address} for service '{service_name}'")
            self.virtual_ips.append((ip_address, label, service_name))
            
            # Save tracking information
            self._save_ip_tracking()
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_subprocess_error(e, f"adding virtual IP {ip_address}")
            return False
        except Exception as e:
            self.error_handler.handle_error(e, f"configuring virtual IP {ip_address}")
            return False
    
    def _announce_arp(self, ip_address: str) -> None:
        """Send gratuitous ARP to announce new IP in the network"""
        try:
            # Method 1: Use arping for gratuitous ARP
            arp_cmd = f"arping -U -I {self.interface} -c 3 {ip_address}"
            subprocess.run(arp_cmd, shell=True, stderr=subprocess.DEVNULL)
            
            # Method 2: Add to neighbor table for persistence
            mac = self._get_interface_mac()
            if mac:
                neigh_cmd = f"ip neigh add {ip_address} lladdr {mac} dev {self.interface} nud permanent"
                subprocess.run(neigh_cmd, shell=True, stderr=subprocess.DEVNULL)
            
            self.arp_announced.append(ip_address)
            logger.debug(f"   📢 Announced ARP for {ip_address}")
            
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to announce ARP for {ip_address}: {e}")
    
    def _get_interface_mac(self) -> Optional[str]:
        """Get the MAC address of the network interface"""
        try:
            cmd = f"ip link show {self.interface} | grep ether | awk '{{print $2}}'"
            mac = subprocess.check_output(cmd, shell=True, text=True).strip()
            return mac if mac else None
        except:
            return None
    
    def _update_arp_cache(self, ip_address: str) -> None:
        """Update local ARP cache for the virtual IP"""
        try:
            mac = self._get_interface_mac()
            if mac:
                cmd = f"arp -s {ip_address} {mac}"
                subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
        except:
            pass
    
    def setup_services_lan(self, services: Dict[str, Any]) -> Dict[str, str]:
        """Set up LAN-visible IPs for all services"""
        if not self.check_root_privileges():
            raise DynaDockNetworkError("Root privileges required for LAN networking")
        
        # Get network details
        current_ip, network_base, cidr, broadcast = self.get_network_details()
        if not current_ip:
            raise DynaDockNetworkError("Unable to determine network configuration")
        
        service_names = list(services.keys())
        num_services = len(service_names)
        
        logger.info(f"🚀 Setting up LAN-visible networking for {num_services} services...")
        
        # Find available IPs
        available_ips = self.find_free_ips(network_base, cidr, num_services)
        
        if len(available_ips) < num_services:
            raise DynaDockNetworkError(f"Not enough available IPs: need {num_services}, found {len(available_ips)}")
        
        # Create service to IP mapping
        service_ip_map = {}
        
        for i, service_name in enumerate(service_names):
            ip_address = available_ips[i]
            
            if self.add_virtual_ip(ip_address, service_name, cidr):
                service_ip_map[service_name] = ip_address
                logger.info(f"   📍 {service_name} -> {ip_address}")
            else:
                logger.error(f"   ❌ Failed to configure {service_name} -> {ip_address}")
        
        # Send additional ARP announcements after short delay
        time.sleep(1)
        logger.info("📢 Refreshing ARP announcements...")
        for ip in service_ip_map.values():
            self._announce_arp(ip)
        
        logger.info(f"✅ LAN networking configured for {len(service_ip_map)} services")
        return service_ip_map
    
    def remove_virtual_ip(self, ip_address: str, cidr: str = "24") -> bool:
        """Remove a virtual IP address"""
        try:
            # Remove IP from interface
            cmd = f"ip addr del {ip_address}/{cidr} dev {self.interface}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            
            # Remove from ARP cache
            subprocess.run(f"arp -d {ip_address}", shell=True, stderr=subprocess.DEVNULL)
            
            # Remove from neighbor table
            subprocess.run(f"ip neigh del {ip_address} dev {self.interface}", shell=True, stderr=subprocess.DEVNULL)
            
            logger.info(f"✅ Removed virtual IP: {ip_address}")
            
            # Update tracking
            self.virtual_ips = [
                (ip, label, service) for ip, label, service in self.virtual_ips 
                if ip != ip_address
            ]
            self._save_ip_tracking()
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Failed to remove IP {ip_address}: {e}")
            return False
    
    def cleanup_all(self) -> None:
        """Clean up all virtual IPs and configuration"""
        logger.info("🧹 Cleaning up LAN networking...")
        
        # Load and remove tracked IPs
        tracked_ips = self._load_ip_tracking()
        for ip_info in tracked_ips.get('virtual_ips', []):
            ip_address = ip_info.get('ip')
            if ip_address:
                self.remove_virtual_ip(ip_address)
        
        # Clear tracking file
        if self.ip_tracking_file.exists():
            self.ip_tracking_file.unlink()
        
        self.virtual_ips.clear()
        self.arp_announced.clear()
        
        logger.info("✅ LAN networking cleanup completed")
    
    def _save_ip_tracking(self) -> None:
        """Save IP tracking information to file"""
        tracking_data = {
            'interface': self.interface,
            'virtual_ips': [
                {
                    'ip': ip,
                    'label': label,
                    'service': service,
                    'timestamp': time.time()
                }
                for ip, label, service in self.virtual_ips
            ]
        }
        
        with open(self.ip_tracking_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)
    
    def _load_ip_tracking(self) -> Dict[str, Any]:
        """Load IP tracking information from file"""
        if not self.ip_tracking_file.exists():
            return {}
        
        try:
            with open(self.ip_tracking_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def refresh_arp_announcements(self) -> None:
        """Refresh ARP announcements for all virtual IPs"""
        logger.debug("🔄 Refreshing ARP announcements...")
        for ip, _, _ in self.virtual_ips:
            self._update_arp_cache(ip)
            self._announce_arp(ip)
    
    def get_service_urls(self, service_ip_map: Dict[str, str], port_map: Dict[str, int]) -> Dict[str, str]:
        """Generate service URLs for LAN access"""
        urls = {}
        for service, ip in service_ip_map.items():
            port = port_map.get(service, 80)
            urls[service] = f"http://{ip}:{port}"
        return urls
    
    def test_connectivity(self, service_ip_map: Dict[str, str], port_map: Dict[str, int]) -> Dict[str, bool]:
        """Test connectivity to all services"""
        results = {}
        
        logger.info("🧪 Testing LAN connectivity...")
        
        for service, ip in service_ip_map.items():
            port = port_map.get(service, 80)
            
            try:
                sock = socket.create_connection((ip, port), timeout=2)
                sock.close()
                results[service] = True
                logger.info(f"   ✅ {service} ({ip}:{port}) - OK")
            except (socket.error, socket.timeout):
                results[service] = False
                logger.warning(f"   ❌ {service} ({ip}:{port}) - Failed")
        
        return results
