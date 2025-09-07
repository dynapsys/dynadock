#!/usr/bin/env python3
"""
Enhanced DynaDock Domain Testing Suite
Tests real browser behavior, network analysis, screenshots, and auto-repair
"""

import sys
import os
import asyncio
import subprocess
import time
import json
import socket
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.live import Live

console = Console()

# Create screenshots directory
SCREENSHOTS_DIR = Path("test_screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Network analysis results
network_analysis = {}

def install_playwright():
    """Install playwright and browsers if not available"""
    try:
        import playwright
        return True
    except ImportError:
        console.print("[yellow]Installing playwright...[/yellow]")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True, capture_output=True)
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=True, capture_output=True)
            return True
        except Exception as e:
            console.print(f"[red]Failed to install playwright: {e}[/red]")
            return False

def analyze_network_connectivity(url):
    """Detailed network analysis for a URL"""
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    hostname = parsed.hostname or 'localhost'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    
    analysis = {
        'hostname': hostname,
        'port': port,
        'scheme': parsed.scheme,
        'tcp_connect': False,
        'dns_resolution': None,
        'ping_result': None,
        'port_scan': {},
        'ssl_cert_info': None
    }
    
    # DNS resolution test
    try:
        import socket
        ip = socket.gethostbyname(hostname)
        analysis['dns_resolution'] = {'success': True, 'ip': ip}
    except Exception as e:
        analysis['dns_resolution'] = {'success': False, 'error': str(e)}
    
    # TCP connection test
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        analysis['tcp_connect'] = (result == 0)
        sock.close()
    except Exception as e:
        analysis['tcp_connect'] = False
    
    # Port scan common ports
    common_ports = [80, 443, 8000, 8001, 8025, 5432, 6379]
    for p in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((hostname, p))
            analysis['port_scan'][p] = (result == 0)
            sock.close()
        except:
            analysis['port_scan'][p] = False
    
    # SSL certificate info for HTTPS
    if parsed.scheme == 'https':
        try:
            import ssl
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    analysis['ssl_cert_info'] = {
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'version': cert['version'],
                        'notAfter': cert['notAfter']
                    }
        except Exception as e:
            analysis['ssl_cert_info'] = {'error': str(e)}
    
    return analysis

def check_system_status():
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
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        status['containers'].append(json.loads(line))
                    except:
                        pass
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
    except Exception as e:
        status['ports_listening']['error'] = str(e)
    
    # Check /etc/hosts for local.dev entries
    try:
        with open('/etc/hosts', 'r') as f:
            for line_num, line in enumerate(f, 1):
                if 'local.dev' in line:
                    status['hosts_file'][line_num] = line.strip()
    except Exception as e:
        status['hosts_file']['error'] = str(e)
    
    return status

def auto_repair_issues(issues):
    """Attempt to automatically repair common issues"""
    repairs_attempted = []
    
    for issue in issues:
        if 'container' in issue.lower() and 'not running' in issue.lower():
            # Try to start containers
            try:
                subprocess.run(['docker-compose', 'up', '-d'], 
                             cwd='/home/tom/github/dynapsys/dynadock/examples/fullstack',
                             timeout=30, check=True)
                repairs_attempted.append("✅ Started Docker containers")
            except Exception as e:
                repairs_attempted.append(f"❌ Failed to start containers: {e}")
        
        elif 'caddy' in issue.lower() and 'not' in issue.lower():
            # Try to start Caddy
            try:
                subprocess.run([
                    'docker', 'run', '--rm', '-d', '--name', 'dynadock-caddy',
                    '-p', '80:80', '-p', '443:443',
                    '-v', '/home/tom/github/dynapsys/dynadock/examples/fullstack/.dynadock/caddy:/etc/caddy',
                    '-v', '/home/tom/github/dynapsys/dynadock/certs:/etc/caddy/certs:ro',
                    'caddy:2-alpine', 'caddy', 'run', '--config', '/etc/caddy/working.conf'
                ], timeout=30, check=True)
                repairs_attempted.append("✅ Started Caddy container") 
            except Exception as e:
                repairs_attempted.append(f"❌ Failed to start Caddy: {e}")
    
    return repairs_attempted

async def test_domain_headless(url, timeout=10):
    """Enhanced domain testing with screenshots and detailed analysis"""
    try:
        from playwright.async_api import async_playwright
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        safe_filename = f"{parsed_url.netloc}_{parsed_url.path.replace('/', '_')}_{int(time.time())}"
        
        async with async_playwright() as p:
            # Use Chromium for testing
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                ignore_https_errors=False,
                extra_http_headers={},
                viewport={'width': 1280, 'height': 720}
            )
            
            page = await context.new_page()
            
            # Enhanced monitoring
            errors = []
            ssl_errors = []
            network_requests = []
            console_logs = []
            
            # Network request monitoring
            def handle_request(request):
                network_requests.append({
                    'url': request.url,
                    'method': request.method,
                    'headers': dict(request.headers),
                    'timestamp': time.time()
                })
            
            def handle_response(response):
                for req in network_requests:
                    if req['url'] == response.url:
                        req['response_status'] = response.status
                        req['response_headers'] = dict(response.headers)
                        break
            
            def handle_page_error(error):
                errors.append(f"Page Error: {error}")
            
            def handle_request_failed(request):
                failure = request.failure or "Unknown failure"
                if 'ssl' in failure.lower() or 'certificate' in failure.lower():
                    ssl_errors.append(f"SSL Error: {request.url} - {failure}")
                errors.append(f"Request failed: {request.url} - {failure}")
            
            def handle_console(msg):
                console_logs.append({
                    'type': msg.type,
                    'text': msg.text,
                    'timestamp': time.time()
                })
            
            # Set up event handlers
            page.on("request", handle_request)
            page.on("response", handle_response) 
            page.on("pageerror", handle_page_error)
            page.on("requestfailed", handle_request_failed)
            page.on("console", handle_console)
            
            try:
                start_time = time.time()
                
                # Navigate to the URL
                response = await page.goto(url, timeout=timeout*1000, wait_until="domcontentloaded")
                
                load_time = time.time() - start_time
                
                if response:
                    # Take screenshot
                    screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_success.png"
                    await page.screenshot(path=screenshot_path, full_page=True)
                    
                    # Get detailed page info
                    title = await page.title()
                    content = await page.content()
                    content_length = len(content)
                    
                    # Enhanced security analysis
                    security_info = await page.evaluate("""
                        () => {
                            const info = {
                                protocol: location.protocol,
                                host: location.host,
                                origin: location.origin,
                                userAgent: navigator.userAgent,
                                cookieEnabled: navigator.cookieEnabled,
                                language: navigator.language
                            };
                            
                            if (location.protocol === 'https:') {
                                info.secure = true;
                                // Try to get certificate info if available
                                try {
                                    info.securityState = 'secure';
                                } catch (e) {
                                    info.securityState = 'unknown';
                                }
                            } else {
                                info.secure = false;
                                info.securityState = 'not-secure';
                            }
                            
                            return info;
                        }
                    """)
                    
                    # Check for specific elements
                    page_analysis = await page.evaluate("""
                        () => {
                            return {
                                hasErrors: document.querySelector('.error, .err, #error') !== null,
                                hasContent: document.body.innerText.length > 100,
                                formCount: document.forms.length,
                                linkCount: document.links.length,
                                imageCount: document.images.length,
                                scriptCount: document.scripts.length
                            };
                        }
                    """)
                    
                    await browser.close()
                    
                    return {
                        'success': True,
                        'status': response.status,
                        'title': title[:80] + '...' if len(title) > 80 else title,
                        'content_length': content_length,
                        'load_time': round(load_time, 2),
                        'screenshot': str(screenshot_path),
                        'security_info': security_info,
                        'page_analysis': page_analysis,
                        'network_requests': network_requests,
                        'console_logs': console_logs[-10:],  # Last 10 console logs
                        'errors': errors,
                        'ssl_errors': ssl_errors
                    }
                else:
                    # Take error screenshot
                    screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_error.png"
                    try:
                        await page.screenshot(path=screenshot_path)
                    except:
                        pass
                    
                    await browser.close()
                    return {
                        'success': False,
                        'error': 'No response received',
                        'screenshot': str(screenshot_path),
                        'network_requests': network_requests,
                        'errors': errors,
                        'ssl_errors': ssl_errors
                    }
                    
            except Exception as e:
                # Take error screenshot
                screenshot_path = SCREENSHOTS_DIR / f"{safe_filename}_exception.png"
                try:
                    await page.screenshot(path=screenshot_path)
                except:
                    pass
                
                await browser.close()
                return {
                    'success': False,
                    'error': str(e),
                    'screenshot': str(screenshot_path),
                    'network_requests': network_requests,
                    'errors': errors,
                    'ssl_errors': ssl_errors
                }
                
    except Exception as e:
        return {
            'success': False,
            'error': f"Browser setup failed: {str(e)}",
            'errors': [],
            'ssl_errors': [],
            'network_requests': []
        }

def test_curl_comparison(url):
    """Test with curl for comparison"""
    try:
        # Test with SSL verification
        result = subprocess.run(
            ['curl', '-s', '-I', '--max-time', '10', url],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0] if result.stdout else 'No output'
            return {'success': True, 'status': first_line, 'ssl_verified': True}
        else:
            # Try without SSL verification
            result_insecure = subprocess.run(
                ['curl', '-s', '-I', '-k', '--max-time', '10', url],
                capture_output=True, text=True, timeout=15
            )
            if result_insecure.returncode == 0:
                first_line = result_insecure.stdout.split('\n')[0] if result_insecure.stdout else 'No output'
                return {'success': True, 'status': first_line, 'ssl_verified': False, 'ssl_error': result.stderr}
            else:
                return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def main():
    """Enhanced main testing function with comprehensive analysis"""
    console.print(Panel(f"[bold green]🚀 Enhanced DynaDock Testing Suite[/bold green]\n[dim]Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]", 
                       border_style="green"))
    
    # Install playwright if needed
    if not install_playwright():
        console.print("[red]Cannot proceed without playwright[/red]")
        return False
    
    # Phase 1: System Status Check
    console.print("\n[bold blue]📋 Phase 1: System Analysis[/bold blue]")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Analyzing system status...", total=None)
        system_status = check_system_status()
        progress.update(task, description="✅ System analysis complete")
    
    # Display system status
    status_tree = Tree("🖥️  System Status")
    
    # Containers
    container_node = status_tree.add("🐳 Docker Containers")
    if 'error' in str(system_status.get('containers', [])):
        container_node.add("[red]❌ Docker not accessible[/red]")
    else:
        for container in system_status.get('containers', []):
            if isinstance(container, dict) and 'Names' in container:
                status = "🟢" if container.get('State') == 'running' else "🔴"
                container_node.add(f"{status} {container['Names']} ({container.get('State', 'unknown')})")
    
    # Ports
    ports_node = status_tree.add("🔌 Listening Ports")
    for port, process in system_status.get('ports_listening', {}).items():
        ports_node.add(f"✅ {port} → {process}")
    
    # Hosts file
    hosts_node = status_tree.add("🌐 /etc/hosts entries")
    hosts_entries = system_status.get('hosts_file', {})
    if hosts_entries:
        for line_num, entry in hosts_entries.items():
            if isinstance(line_num, int):
                hosts_node.add(f"Line {line_num}: {entry}")
    else:
        hosts_node.add("[yellow]⚠️  No local.dev entries found[/yellow]")
    
    console.print(status_tree)
    
    # Phase 2: Network Analysis
    console.print(f"\n[bold blue]🌐 Phase 2: Network Connectivity Analysis[/bold blue]")
    
    domains_to_test = [
        "https://frontend.local.dev/",
        "https://backend.local.dev/",
        "https://mailhog.local.dev/", 
        "https://localhost/health",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8025"
    ]
    
    # Analyze network for each domain
    network_results = {}
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        for url in domains_to_test:
            task = progress.add_task(f"Analyzing {url}...", total=None)
            network_results[url] = analyze_network_connectivity(url)
            progress.update(task, description=f"✅ {url}")
    
    # Phase 3: Headless Browser Testing  
    console.print(f"\n[bold blue]🎭 Phase 3: Headless Browser Testing[/bold blue]")
    
    # Create comprehensive results table
    table = Table(title=f"🧪 Test Results - {len(domains_to_test)} URLs")
    table.add_column("URL", style="cyan", no_wrap=True, min_width=25)
    table.add_column("Network", style="blue", min_width=15)
    table.add_column("Browser", style="green", min_width=20)
    table.add_column("Performance", style="yellow", min_width=15)
    table.add_column("Security", style="red", min_width=15)
    table.add_column("Screenshot", style="magenta", min_width=20)
    
    issues_found = []
    successful_tests = 0
    
    for url in domains_to_test:
        console.print(f"\n🔍 Testing: [cyan]{url}[/cyan]")
        
        # Get network analysis
        network_info = network_results.get(url, {})
        
        # Test with headless browser
        browser_result = await test_domain_headless(url, timeout=15)
        
        # Network status
        dns_ok = network_info.get('dns_resolution', {}).get('success', False)
        tcp_ok = network_info.get('tcp_connect', False)
        network_status = f"{'🟢' if dns_ok else '🔴'} DNS | {'🟢' if tcp_ok else '🔴'} TCP"
        
        # Browser status 
        if browser_result['success']:
            successful_tests += 1
            load_time = browser_result.get('load_time', 0)
            browser_status = f"✅ {browser_result['status']}\n📄 {browser_result.get('content_length', 0)} chars"
        else:
            browser_status = f"❌ Failed\n🚫 {browser_result.get('error', 'Unknown')[:30]}"
            issues_found.append(f"{url}: {browser_result.get('error', 'Unknown error')}")
        
        # Performance metrics
        if browser_result['success']:
            perf_status = f"⚡ {browser_result.get('load_time', 0)}s\n🔗 {len(browser_result.get('network_requests', []))} requests"
        else:
            perf_status = "❌ N/A"
        
        # Security analysis
        if browser_result['success'] and browser_result.get('security_info'):
            sec_info = browser_result['security_info']
            is_https = sec_info.get('protocol') == 'https:'
            sec_status = f"{'🔒' if is_https else '🔓'} {sec_info.get('protocol', 'unknown')}\n🛡️ {sec_info.get('securityState', 'unknown')}"
        else:
            sec_status = "❓ Unknown"
        
        # Screenshot info
        screenshot_path = browser_result.get('screenshot', '')
        if screenshot_path and Path(screenshot_path).exists():
            screenshot_status = f"📸 Captured\n📁 {Path(screenshot_path).name}"
        else:
            screenshot_status = "❌ Failed"
        
        table.add_row(url, network_status, browser_status, perf_status, sec_status, screenshot_status)
    
    console.print(f"\n")
    console.print(table)
    
    # Phase 4: Issue Analysis and Auto-Repair
    console.print(f"\n[bold blue]🔧 Phase 4: Issue Analysis & Auto-Repair[/bold blue]")
    
    if issues_found:
        console.print(f"\n[red]❌ Found {len(issues_found)} issues:[/red]")
        for i, issue in enumerate(issues_found[:5], 1):
            console.print(f"  {i}. {issue}")
        
        # Attempt auto-repair
        console.print(f"\n[yellow]🛠️  Attempting automatic repairs...[/yellow]")
        repairs = auto_repair_issues(issues_found)
        
        for repair in repairs:
            console.print(f"  {repair}")
    
    # Phase 5: Summary Report
    console.print(f"\n[bold blue]📊 Phase 5: Final Report[/bold blue]")
    
    success_rate = (successful_tests / len(domains_to_test)) * 100
    
    summary_panel = Panel(
        f"[bold green]🎯 Test Summary[/bold green]\n\n"
        f"✅ Successful tests: {successful_tests}/{len(domains_to_test)} ({success_rate:.1f}%)\n"
        f"📸 Screenshots saved: {len(list(SCREENSHOTS_DIR.glob('*.png')))}\n"
        f"🔍 Network analysis: Complete for all URLs\n"
        f"🛠️  Auto-repair attempts: {len(auto_repair_issues(issues_found))}\n\n"
        f"📁 Screenshots directory: [cyan]{SCREENSHOTS_DIR.absolute()}[/cyan]",
        border_style="green" if success_rate > 80 else "yellow"
    )
    console.print(summary_panel)
    
    # Save detailed report
    report_file = Path("test_report.json")
    detailed_report = {
        'timestamp': datetime.now().isoformat(),
        'success_rate': success_rate,
        'system_status': system_status,
        'network_analysis': network_results,
        'issues_found': issues_found,
        'screenshots_dir': str(SCREENSHOTS_DIR.absolute()),
        'total_tests': len(domains_to_test),
        'successful_tests': successful_tests
    }
    
    with open(report_file, 'w') as f:
        json.dump(detailed_report, f, indent=2, default=str)
    
    console.print(f"\n💾 Detailed report saved: [cyan]{report_file.absolute()}[/cyan]")
    
    return success_rate > 80

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Test failed: {e}[/red]")
        sys.exit(1)
