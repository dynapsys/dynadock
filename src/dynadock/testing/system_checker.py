#!/usr/bin/env python3
"""
System status checker module for DynaDock testing
"""

import json
import subprocess
from typing import Dict, Any


def check_system_status() -> Dict[str, Any]:
    """Check Docker containers, processes, and system status"""
    status = {
        'containers': [],
        'ports_listening': {},
        'hosts_file': {},
        'processes': []
    }
    
    # Docker containers
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        status['containers'].append(json.loads(line))
                    except Exception:
                        pass
        else:
            status['containers'] = [{'error': 'No containers running or Docker not accessible'}]
    except Exception as e:
        status['containers'] = [{'error': str(e)}]
    
    # Check listening ports
    try:
        result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ':443 ' in line or ':80 ' in line or ':8000' in line or ':8025' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        status['ports_listening'][parts[3]] = parts[6] if len(parts) > 6 else 'unknown'
        
        if not status['ports_listening']:
            status['ports_listening']['info'] = 'No DynaDock-related ports found listening'
    except Exception as e:
        status['ports_listening']['error'] = str(e)
    
    # Check /etc/hosts for dynadock.lan entries
    try:
        with open('/etc/hosts', 'r') as f:
            for line_num, line in enumerate(f, 1):
                if 'dynadock.lan' in line:
                    status['hosts_file'][line_num] = line.strip()
        
        if not status['hosts_file']:
            status['hosts_file']['info'] = 'No dynadock.lan entries found in /etc/hosts'
    except Exception as e:
        status['hosts_file']['error'] = str(e)
    
    return status


def get_docker_status() -> Dict[str, Any]:
    """Get detailed Docker status"""
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return {'status': 'not_running', 'error': 'Docker daemon not accessible'}
        
        # Get container status
        result = subprocess.run(['docker', 'ps', '-a', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True, timeout=10)
        
        return {'status': 'running', 'containers_output': result.stdout}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
