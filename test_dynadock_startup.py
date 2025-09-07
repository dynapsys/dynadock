#!/usr/bin/env python3
"""
Comprehensive DynaDock startup and test script
Tests each component step by step
"""

import sys
import os
import subprocess
import time
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run_command(cmd, cwd=None, check=True):
    """Run command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def test_connection(url, expected_status=200, timeout=5):
    """Test HTTP/HTTPS connection"""
    try:
        response = requests.get(url, timeout=timeout, verify=False)
        return response.status_code == expected_status, response.status_code
    except Exception as e:
        return False, str(e)

def step_1_cleanup():
    """Step 1: Clean up existing containers"""
    console.print(Panel("[bold blue]Step 1: Cleanup existing containers[/bold blue]"))
    
    # Stop all DynaDock related containers
    commands = [
        "docker stop dynadock-caddy 2>/dev/null || true",
        "docker rm dynadock-caddy 2>/dev/null || true",
        "cd /home/tom/github/dynapsys/dynadock/examples/fullstack && docker-compose down 2>/dev/null || true"
    ]
    
    for cmd in commands:
        success, stdout, stderr = run_command(cmd, check=False)
        console.print(f"✓ {cmd}")
    
    # Check no containers running
    success, stdout, stderr = run_command("docker ps -q")
    if stdout.strip():
        console.print(f"[yellow]Warning: Some containers still running[/yellow]")
    else:
        console.print("[green]✓ All containers stopped[/green]")
    
    return True

def step_2_check_certs():
    """Step 2: Verify mkcert certificates exist"""
    console.print(Panel("[bold blue]Step 2: Check mkcert certificates[/bold blue]"))
    
    certs_dir = Path("/home/tom/github/dynapsys/dynadock/certs")
    cert_files = [
        "_wildcard.local.dev+2.pem",
        "_wildcard.local.dev+2-key.pem"
    ]
    
    for cert_file in cert_files:
        cert_path = certs_dir / cert_file
        if cert_path.exists():
            console.print(f"[green]✓ Certificate found: {cert_file}[/green]")
        else:
            console.print(f"[red]✗ Certificate missing: {cert_file}[/red]")
            return False
    
    return True

def step_3_check_hosts():
    """Step 3: Verify /etc/hosts entries"""
    console.print(Panel("[bold blue]Step 3: Check /etc/hosts entries[/bold blue]"))
    
    try:
        with open('/etc/hosts', 'r') as f:
            hosts_content = f.read()
        
        domains = ['frontend.local.dev', 'backend.local.dev', 'mailhog.local.dev']
        for domain in domains:
            if domain in hosts_content:
                console.print(f"[green]✓ {domain} found in /etc/hosts[/green]")
            else:
                console.print(f"[red]✗ {domain} missing from /etc/hosts[/red]")
                return False
        
        return True
    except Exception as e:
        console.print(f"[red]Error reading /etc/hosts: {e}[/red]")
        return False

def step_4_start_compose():
    """Step 4: Start docker-compose services"""
    console.print(Panel("[bold blue]Step 4: Start docker-compose services[/bold blue]"))
    
    cwd = "/home/tom/github/dynapsys/dynadock/examples/fullstack"
    
    # Start services
    success, stdout, stderr = run_command("docker-compose up -d", cwd=cwd)
    if not success:
        console.print(f"[red]✗ Failed to start docker-compose services[/red]")
        console.print(f"Error: {stderr}")
        return False
    
    console.print("[green]✓ Docker-compose services started[/green]")
    
    # Wait for services to be ready
    console.print("Waiting for services to start...")
    time.sleep(10)
    
    # Check service status
    success, stdout, stderr = run_command("docker-compose ps", cwd=cwd)
    console.print("Service status:")
    console.print(stdout)
    
    return True

def step_5_start_caddy():
    """Step 5: Start Caddy with HTTPS"""
    console.print(Panel("[bold blue]Step 5: Start Caddy with HTTPS[/bold blue]"))
    
    cwd = "/home/tom/github/dynapsys/dynadock/examples/fullstack"
    
    # Generate Caddyfile
    sys.path.insert(0, '/home/tom/github/dynapsys/dynadock/src')
    os.chdir(cwd)
    
    try:
        from dynadock.caddy_config import CaddyConfig
        
        caddy = CaddyConfig(Path('.'))
        
        # Generate configuration
        services = {'frontend': 8000, 'backend': 8001, 'postgres': 5432, 'redis': 6379, 'mailhog': 8025}
        ips = {service: '127.0.0.1' for service in services}
        
        caddy.generate(
            services={name: {} for name in services},
            ports=services,
            domain='local.dev',
            enable_tls=True,
            cors_origins=['*'],
            ips=ips
        )
        
        console.print("[green]✓ Caddyfile generated[/green]")
        
        # Start Caddy
        caddy.start_caddy()
        console.print("[green]✓ Caddy container started[/green]")
        
        # Wait for Caddy to start
        time.sleep(5)
        
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Failed to start Caddy: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

def step_6_test_services():
    """Step 6: Test all services"""
    console.print(Panel("[bold blue]Step 6: Test all services[/bold blue]"))
    
    tests = [
        ("HTTP Health Check", "http://localhost/health", 200),
        ("HTTPS Health Check", "https://localhost/health", 200),
        ("Frontend HTTP", "http://localhost:8000", 200),
        ("Backend HTTP", "http://localhost:8001", 404),  # Expect 404 for root path
        ("MailHog HTTP", "http://localhost:8025", 200),
        ("Frontend HTTPS", "https://frontend.local.dev/", 200),
        ("Backend HTTPS", "https://backend.local.dev/", 404),  # Expect 404 for root path
        ("MailHog HTTPS", "https://mailhog.local.dev/", 200),
    ]
    
    results = []
    for name, url, expected_status in tests:
        console.print(f"Testing {name}: {url}")
        success, status = test_connection(url, expected_status)
        if success:
            console.print(f"[green]✓ {name}: Status {status}[/green]")
            results.append(True)
        else:
            console.print(f"[red]✗ {name}: {status}[/red]")
            results.append(False)
    
    return all(results)

def step_7_final_status():
    """Step 7: Show final status"""
    console.print(Panel("[bold blue]Step 7: Final Status[/bold blue]"))
    
    # Show running containers
    success, stdout, stderr = run_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    console.print("Running containers:")
    console.print(stdout)
    
    # Show listening ports
    success, stdout, stderr = run_command("sudo netstat -tlnp | grep ':80\\|:443'", check=False)
    if success and stdout:
        console.print("Listening ports:")
        console.print(stdout)
    
    console.print("\n[green]🎉 DynaDock is ready![/green]")
    console.print("[bold]Access your services:[/bold]")
    console.print("• Frontend HTTPS: https://frontend.local.dev/")
    console.print("• Backend HTTPS: https://backend.local.dev/")
    console.print("• MailHog HTTPS: https://mailhog.local.dev/")
    console.print("• HTTP Health: http://localhost/health")
    console.print("• HTTPS Health: https://localhost/health")

def main():
    """Main test runner"""
    console.print(Panel("[bold green]DynaDock Comprehensive Startup Test[/bold green]"))
    
    steps = [
        ("Cleanup", step_1_cleanup),
        ("Check Certificates", step_2_check_certs),
        ("Check /etc/hosts", step_3_check_hosts),
        ("Start Docker Services", step_4_start_compose),
        ("Start Caddy HTTPS", step_5_start_caddy),
        ("Test All Services", step_6_test_services),
        ("Final Status", step_7_final_status),
    ]
    
    for i, (name, step_func) in enumerate(steps, 1):
        console.print(f"\n[bold cyan]═══ {i}/7: {name} ═══[/bold cyan]")
        
        try:
            if not step_func():
                console.print(f"[red]✗ Step {i} failed: {name}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]✗ Step {i} crashed: {name} - {e}[/red]")
            import traceback
            traceback.print_exc()
            return False
            
        console.print(f"[green]✓ Step {i} completed: {name}[/green]")
    
    console.print(Panel("[bold green]🎉 ALL TESTS PASSED! DynaDock is fully operational![/bold green]"))
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
