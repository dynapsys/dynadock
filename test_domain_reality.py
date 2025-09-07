#!/usr/bin/env python3
"""
Simple but accurate domain testing script
Tests what actually works vs what we claim works
"""

import subprocess
import requests
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def test_actual_curl(url, timeout=5):
    """Test with curl - strict SSL verification"""
    try:
        # First try with strict SSL
        result = subprocess.run(
            ['curl', '-s', '-f', '--max-time', str(timeout), '-o', '/dev/null', '-w', '%{http_code}|%{ssl_verify_result}', url],
            capture_output=True, text=True, timeout=timeout+2
        )
        
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            http_code = parts[0] if parts else 'unknown'
            ssl_verify = parts[1] if len(parts) > 1 else 'unknown'
            return {
                'success': True, 
                'http_code': http_code,
                'ssl_verify': ssl_verify == '0',
                'method': 'strict_ssl'
            }
        else:
            # Try without SSL verification to see if it's SSL issue
            result2 = subprocess.run(
                ['curl', '-s', '-f', '-k', '--max-time', str(timeout), '-o', '/dev/null', '-w', '%{http_code}', url],
                capture_output=True, text=True, timeout=timeout+2
            )
            if result2.returncode == 0:
                return {
                    'success': True,
                    'http_code': result2.stdout.strip(),
                    'ssl_verify': False,
                    'method': 'ssl_bypassed',
                    'ssl_error': result.stderr.strip()
                }
            else:
                return {
                    'success': False,
                    'error': f"Connection failed: {result.stderr.strip()}",
                    'method': 'failed'
                }
    except Exception as e:
        return {'success': False, 'error': str(e), 'method': 'exception'}

def test_python_requests(url, timeout=5):
    """Test with Python requests - shows different perspective"""
    try:
        response = requests.get(url, timeout=timeout, verify=True)
        return {
            'success': True,
            'status_code': response.status_code,
            'ssl_verified': True,
            'content_length': len(response.content)
        }
    except requests.exceptions.SSLError as e:
        try:
            # Try without SSL verification
            response = requests.get(url, timeout=timeout, verify=False)
            return {
                'success': True,
                'status_code': response.status_code,
                'ssl_verified': False,
                'ssl_error': str(e),
                'content_length': len(response.content)
            }
        except Exception as e2:
            return {'success': False, 'error': f"SSL + Connection error: {str(e2)}"}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_telnet_connection(domain, port):
    """Test basic TCP connection"""
    try:
        result = subprocess.run(
            ['timeout', '3', 'bash', '-c', f'echo > /dev/tcp/{domain}/{port}'],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False

def main():
    console.print(Panel("[bold red]DynaDock REALITY CHECK - What Actually Works?[/bold red]"))
    
    domains_to_test = [
        ("https://frontend.local.dev/", "frontend.local.dev", 443),
        ("https://backend.local.dev/", "backend.local.dev", 443), 
        ("https://mailhog.local.dev/", "mailhog.local.dev", 443),
        ("https://localhost/health", "localhost", 443),
        ("http://localhost:8000", "localhost", 8000),
        ("http://localhost:8001", "localhost", 8001),
        ("http://localhost:8025", "localhost", 8025)
    ]
    
    table = Table()
    table.add_column("URL", style="cyan")
    table.add_column("TCP Connection", style="blue")
    table.add_column("Curl Test", style="green") 
    table.add_column("Python Requests", style="yellow")
    table.add_column("Real Status", style="red", no_wrap=False)
    
    real_issues = []
    
    for url, domain, port in domains_to_test:
        console.print(f"Testing: {url}")
        
        # Test TCP connection first
        tcp_works = test_telnet_connection(domain, port)
        tcp_status = "✅ Connected" if tcp_works else "❌ Cannot connect"
        
        # Test with curl
        curl_result = test_actual_curl(url)
        if curl_result['success']:
            if curl_result['ssl_verify']:
                curl_status = f"✅ {curl_result['http_code']} (SSL ✅)"
            else:
                curl_status = f"⚠️ {curl_result['http_code']} (SSL ❌)"
        else:
            curl_status = f"❌ {curl_result.get('error', 'Failed')[:30]}"
        
        # Test with Python requests
        req_result = test_python_requests(url)
        if req_result['success']:
            if req_result['ssl_verified']:
                req_status = f"✅ {req_result['status_code']} (SSL ✅)"
            else:
                req_status = f"⚠️ {req_result['status_code']} (SSL ❌)"  
        else:
            req_status = f"❌ {req_result.get('error', 'Failed')[:30]}"
        
        # Determine real status
        if not tcp_works:
            real_status = "❌ SERVICE DOWN - No TCP connection"
            real_issues.append(f"{url}: Service not responding on {domain}:{port}")
        elif url.startswith('https://') and not curl_result.get('ssl_verify', False):
            real_status = "⚠️ SSL ISSUES - Insecure connection"
            real_issues.append(f"{url}: SSL certificate problems")
        elif curl_result['success'] and req_result['success']:
            real_status = "✅ WORKING"
        else:
            real_status = "❌ HTTP ERRORS"
            real_issues.append(f"{url}: HTTP connection issues")
        
        table.add_row(url, tcp_status, curl_status, req_status, real_status)
    
    console.print("\n")
    console.print(table)
    
    # Show real problems
    if real_issues:
        console.print(f"\n[red]🚨 ACTUAL ISSUES FOUND ({len(real_issues)}):[/red]")
        for i, issue in enumerate(real_issues, 1):
            console.print(f"  {i}. {issue}")
        
        # Provide specific fixes
        console.print(f"\n[yellow]📋 RECOMMENDED FIXES:[/yellow]")
        console.print("1. Check if all Docker containers are actually running:")
        console.print("   docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
        console.print("2. Verify Caddy is listening on correct ports:")
        console.print("   sudo netstat -tlnp | grep ':80\\|:443'")
        console.print("3. Check /etc/hosts entries:")
        console.print("   grep 'local.dev' /etc/hosts")
        console.print("4. Test certificate trust:")
        console.print("   openssl s_client -connect frontend.local.dev:443 -servername frontend.local.dev")
        
        return False
    else:
        console.print(f"\n[green]✅ ALL SERVICES ACTUALLY WORKING![/green]")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
