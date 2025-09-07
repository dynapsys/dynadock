#!/usr/bin/env python3
"""
Simplified DynaDock Domain Testing Suite
Refactored from 598-line monolithic script to modular design
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

console = Console()

# Import our modular components
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from src.dynadock.testing.network_analyzer import analyze_network_connectivity
    from src.dynadock.testing.system_checker import check_system_status, get_docker_status
    from src.dynadock.testing.browser_tester import test_domain_headless, setup_screenshots_dir
    from src.dynadock.testing.auto_repair import auto_repair_issues, repair_hosts_file
    console.print("[green]✅ All testing modules imported successfully[/green]")
except ImportError as e:
    console.print(f"[red]❌ Error importing modules: {e}[/red]")
    console.print("[yellow]Please ensure you're running from the dynadock root directory[/yellow]")
    sys.exit(1)

# Default test domains
DEFAULT_DOMAINS = [
    "https://frontend.local.dev/",
    "https://mailhog.local.dev/", 
    "https://localhost/health",
    "http://localhost:8000",
    "http://localhost:8025"
]

def install_playwright():
    """Install playwright if needed"""
    try:
        import playwright
        return True
    except ImportError:
        console.print("[yellow]Installing playwright...[/yellow]")
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], 
                         check=True, capture_output=True)
            subprocess.run([sys.executable, "-m", "playwright", "install"], 
                         check=True, capture_output=True)
            console.print("[green]✅ Playwright installed successfully[/green]")
            return True
        except Exception as e:
            console.print(f"[red]❌ Failed to install playwright: {e}[/red]")
            return False

def display_system_status(system_status):
    """Display system status in a tree format"""
    status_tree = Tree("🖥️  System Status")
    
    # Docker containers
    container_node = status_tree.add("🐳 Docker Containers")
    containers = system_status.get('containers', [])
    
    if not containers or (len(containers) == 1 and 'error' in containers[0]):
        container_node.add("[red]❌ No containers running or Docker not accessible[/red]")
    else:
        for container in containers:
            if isinstance(container, dict) and 'Names' in container:
                status = "🟢" if container.get('State') == 'running' else "🔴"
                container_node.add(f"{status} {container['Names']} ({container.get('State', 'unknown')})")
    
    # Listening ports
    ports_node = status_tree.add("🔌 Listening Ports")
    ports = system_status.get('ports_listening', {})
    
    if not ports or 'info' in ports or 'error' in ports:
        ports_node.add("[yellow]⚠️  No DynaDock ports detected[/yellow]")
    else:
        for port, process in ports.items():
            ports_node.add(f"✅ {port} → {process}")
    
    # /etc/hosts entries
    hosts_node = status_tree.add("🌐 /etc/hosts entries")
    hosts_entries = system_status.get('hosts_file', {})
    
    if not hosts_entries or 'info' in hosts_entries or 'error' in hosts_entries:
        hosts_node.add("[yellow]⚠️  No local.dev entries found[/yellow]")
    else:
        for line_num, entry in hosts_entries.items():
            if isinstance(line_num, int):
                hosts_node.add(f"Line {line_num}: {entry}")
    
    console.print(status_tree)

async def run_tests(domains=None):
    """Run comprehensive testing suite with detailed logging"""
    domains = domains or DEFAULT_DOMAINS
    
    console.print(Panel(
        f"[bold green]🚀 DynaDock Testing Suite (Enhanced & Logged)[/bold green]\n"
        f"[dim]Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n"
        f"[dim]Testing {len(domains)} domains[/dim]", 
        border_style="green"
    ))
    
    # Phase 0: Cleanup & Preparation
    console.print("\n[bold blue]🧹 Phase 0: Cleanup & Preparation[/bold blue]")
    console.print("📸 Cleaning up old screenshots...")
    screenshots_dir = setup_screenshots_dir()
    console.print(f"✅ Screenshots directory ready: {screenshots_dir}")
    
    # Phase 1: System Check with detailed logging
    console.print("\n[bold blue]📋 Phase 1: System Analysis[/bold blue]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Checking system status...", total=None)
        console.print("🔍 Analyzing Docker containers...")
        console.print("🔍 Checking listening ports...")
        console.print("🔍 Verifying /etc/hosts entries...")
        system_status = check_system_status()
        progress.update(task, description="✅ System check complete")
    
    # Log system status details
    console.print(f"📊 Found {len(system_status.get('containers', []))} container(s)")
    console.print(f"📊 Found {len(system_status.get('ports_listening', {}))} listening port(s)")
    console.print(f"📊 Found {len(system_status.get('hosts_file', {}))} hosts entry(ies)")
    
    display_system_status(system_status)
    
    # Phase 2: Network Analysis with detailed logging
    console.print("\n[bold blue]🌐 Phase 2: Network Analysis[/bold blue]")
    console.print(f"🔍 Testing network connectivity for {len(domains)} domains...")
    
    network_results = {}
    network_issues = []
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        for i, url in enumerate(domains, 1):
            task = progress.add_task(f"[{i}/{len(domains)}] Analyzing {url}...", total=None)
            console.print(f"🌐 [{i}/{len(domains)}] Network analysis: {url}")
            
            network_info = analyze_network_connectivity(url)
            network_results[url] = network_info
            
            # Log network analysis results
            dns_ok = network_info.get('dns_resolution', {}).get('success', False)
            tcp_ok = network_info.get('tcp_connect', False)
            console.print(f"   📍 DNS: {'✅' if dns_ok else '❌'} | TCP: {'✅' if tcp_ok else '❌'}")
            
            if not dns_ok:
                network_issues.append(f"{url}: DNS resolution failed")
            if not tcp_ok:
                network_issues.append(f"{url}: TCP connection failed")
                
            progress.update(task, description=f"✅ [{i}/{len(domains)}] {url}")
    
    console.print(f"📊 Network analysis complete: {len(network_issues)} issue(s) found")
    if network_issues:
        for issue in network_issues[:3]:
            console.print(f"   ⚠️  {issue}")
        if len(network_issues) > 3:
            console.print(f"   ... and {len(network_issues) - 3} more issues")
    
    # Phase 3: Playwright Setup
    console.print("\n[bold blue]🎭 Phase 3: Browser Testing Setup[/bold blue]")
    console.print("🔍 Checking Playwright installation...")
    
    if not install_playwright():
        console.print("[red]❌ Cannot proceed without playwright[/red]")
        return False
    
    console.print("✅ Playwright ready for browser testing")
    
    # Phase 4: Browser Testing Execution
    console.print("\n[bold blue]🎭 Phase 4: Browser Testing Execution[/bold blue]")
    console.print(f"🔍 Running headless browser tests for {len(domains)} URLs...")
    
    # Create results table
    table = Table(title="🧪 Detailed Test Results")
    table.add_column("URL", style="cyan", no_wrap=True)
    table.add_column("Network", style="blue")
    table.add_column("Browser", style="green")
    table.add_column("Performance", style="yellow")
    table.add_column("Screenshot", style="magenta")
    
    issues_found = []
    successful_tests = 0
    browser_details = {}
    
    for i, url in enumerate(domains, 1):
        console.print(f"\n🎭 [{i}/{len(domains)}] Browser testing: [cyan]{url}[/cyan]")
        
        # Network status from previous analysis
        network_info = network_results.get(url, {})
        dns_ok = network_info.get('dns_resolution', {}).get('success', False)
        tcp_ok = network_info.get('tcp_connect', False)
        network_status = f"{'🟢' if dns_ok else '🔴'} DNS\n{'🟢' if tcp_ok else '🔴'} TCP"
        
        console.print(f"   📊 Network Status: DNS {'✅' if dns_ok else '❌'}, TCP {'✅' if tcp_ok else '❌'}")
        
        # Browser test with detailed logging
        console.print(f"   🌐 Launching headless browser...")
        browser_result = await test_domain_headless(url, timeout=15)
        
        if browser_result['success']:
            successful_tests += 1
            load_time = browser_result.get('load_time', 0)
            content_length = browser_result.get('content_length', 0)
            network_requests = len(browser_result.get('network_requests', []))
            
            browser_status = f"✅ {browser_result['status']}"
            perf_info = f"⚡ {load_time}s\n📄 {content_length} chars\n🔗 {network_requests} requests"
            
            console.print(f"   ✅ Success: HTTP {browser_result['status']} in {load_time}s")
            console.print(f"   📄 Content: {content_length} characters")
            console.print(f"   🔗 Network: {network_requests} requests made")
            
            # Log security info
            if browser_result.get('security_info'):
                sec_info = browser_result['security_info']
                protocol = sec_info.get('protocol', 'unknown')
                console.print(f"   🔒 Security: {protocol} ({sec_info.get('securityState', 'unknown')})")
            
        else:
            error_msg = browser_result.get('error', 'Unknown error')
            browser_status = "❌ Failed"
            perf_info = f"🚫 {error_msg[:30]}"
            issues_found.append(f"{url}: {error_msg}")
            
            console.print(f"   ❌ Failed: {error_msg}")
            
            # Log any SSL errors
            if browser_result.get('ssl_errors'):
                console.print(f"   🔐 SSL Errors: {len(browser_result['ssl_errors'])}")
        
        # Screenshot info
        screenshot_path = browser_result.get('screenshot', '')
        if screenshot_path and Path(screenshot_path).exists():
            screenshot_info = f"📸 Saved\n📁 {Path(screenshot_path).name}"
            console.print(f"   📸 Screenshot saved: {Path(screenshot_path).name}")
        else:
            screenshot_info = "❌ Failed"
            console.print(f"   📸 Screenshot: Failed to capture")
        
        browser_details[url] = browser_result
        table.add_row(url, network_status, browser_status, perf_info, screenshot_info)
    
    console.print(f"\n📊 Browser testing complete: {successful_tests}/{len(domains)} successful")
    console.print(table)
    
    # Phase 5: Auto-Repair & Issue Resolution
    if issues_found:
        console.print(f"\n[bold blue]🔧 Phase 5: Auto-Repair & Issue Resolution[/bold blue]")
        console.print(f"[red]❌ Found {len(issues_found)} issues requiring attention[/red]")
        
        console.print("🛠️  Attempting automatic repairs...")
        repairs = auto_repair_issues(issues_found)
        console.print("🏠 Checking hosts file configuration...")
        hosts_repair = repair_hosts_file()
        
        all_repairs = repairs + [hosts_repair]
        console.print(f"📊 Completed {len(all_repairs)} repair attempt(s)")
        
        for repair in all_repairs:
            console.print(f"  {repair}")
    else:
        console.print(f"\n[bold blue]✅ Phase 5: No Issues Found[/bold blue]")
        console.print("🎉 All tests passed successfully - no repairs needed!")
    
    # Phase 6: Final Summary & Report Generation
    console.print(f"\n[bold blue]📊 Phase 6: Final Report Generation[/bold blue]")
    
    success_rate = (successful_tests / len(domains)) * 100
    screenshot_count = len(list(screenshots_dir.glob('*.png'))) if screenshots_dir.exists() else 0
    
    # Generate detailed statistics
    console.print("📈 Generating test statistics...")
    stats = {
        'total_domains_tested': len(domains),
        'successful_tests': successful_tests,
        'failed_tests': len(domains) - successful_tests,
        'network_issues': len(network_issues),
        'browser_issues': len(issues_found),
        'screenshots_captured': screenshot_count,
        'repair_attempts': len(all_repairs) if issues_found else 0
    }
    
    for key, value in stats.items():
        console.print(f"   📊 {key.replace('_', ' ').title()}: {value}")
    
    summary = Panel(
        f"[bold green]🎯 Final Test Summary[/bold green]\n\n"
        f"✅ Success Rate: {successful_tests}/{len(domains)} ({success_rate:.1f}%)\n"
        f"📸 Screenshots: {screenshot_count} saved in test_screenshots/\n"
        f"🔧 Auto-repairs: {len(all_repairs) if issues_found else 0} attempted\n"
        f"📊 Detailed Report: test_report.json\n"
        f"⏱️  Total Test Duration: {datetime.now().strftime('%H:%M:%S')}",
        border_style="green" if success_rate > 80 else "yellow"
    )
    console.print(f"\n{summary}")
    
    # Save comprehensive report with all details
    console.print("💾 Saving comprehensive test report...")
    report = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'test_duration': f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'domains_tested': len(domains),
            'success_rate': success_rate
        },
        'results': {
            'successful_tests': successful_tests,
            'failed_tests': len(domains) - successful_tests,
            'issues_found': issues_found,
            'network_issues': network_issues
        },
        'system_analysis': system_status,
        'network_analysis': {k: v for k, v in network_results.items()},
        'browser_details': {k: v for k, v in browser_details.items()},
        'repair_attempts': all_repairs if issues_found else [],
        'statistics': stats,
        'screenshots': {
            'directory': str(screenshots_dir),
            'count': screenshot_count,
            'files': [f.name for f in screenshots_dir.glob('*.png')] if screenshots_dir.exists() else []
        }
    }
    
    with open('test_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    console.print("✅ Test report saved successfully")
    
    return success_rate > 80

async def main():
    """Main entry point with comprehensive error handling"""
    start_time = datetime.now()
    
    try:
        console.print(f"[blue]🚀 DynaDock Enhanced Testing Suite starting...[/blue]")
        console.print(f"[dim]Process ID: {os.getpid()}, Start time: {start_time.strftime('%H:%M:%S')}[/dim]")
        
        success = await run_tests()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if success:
            console.print(f"\n[green]🎉 All tests completed successfully![/green]")
            console.print(f"[dim]Total duration: {duration}[/dim]")
        else:
            console.print(f"\n[yellow]⚠️  Some tests failed - check the detailed report[/yellow]")
            console.print(f"[dim]Total duration: {duration}[/dim]")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        console.print(f"\n[yellow]⚠️  Test interrupted by user after {datetime.now() - start_time}[/yellow]")
        sys.exit(1)
    except ImportError as e:
        console.print(f"\n[red]❌ Module import error: {e}[/red]")
        console.print("[yellow]💡 Try running from the dynadock root directory[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Test failed with error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

def test_all_modules():
    """Quick test of all refactored modules"""
    console.print("[blue]🧪 Testing all refactored modules...[/blue]")
    
    modules_status = {}
    
    # Test network analyzer
    try:
        result = analyze_network_connectivity('http://localhost:8000')
        modules_status['network_analyzer'] = f"✅ OK ({result['hostname']}:{result['port']})"
    except Exception as e:
        modules_status['network_analyzer'] = f"❌ Error: {e}"
    
    # Test system checker
    try:
        status = check_system_status()
        containers = len(status.get('containers', []))
        modules_status['system_checker'] = f"✅ OK ({containers} containers found)"
    except Exception as e:
        modules_status['system_checker'] = f"❌ Error: {e}"
    
    # Test auto repair
    try:
        result = repair_hosts_file()
        modules_status['auto_repair'] = f"✅ OK (hosts check)"
    except Exception as e:
        modules_status['auto_repair'] = f"❌ Error: {e}"
    
    # Test screenshot setup
    try:
        screenshots_dir = setup_screenshots_dir()
        modules_status['browser_tester'] = f"✅ OK ({screenshots_dir})"
    except Exception as e:
        modules_status['browser_tester'] = f"❌ Error: {e}"
    
    # Display results
    for module, status in modules_status.items():
        console.print(f"  📦 {module}: {status}")
    
    failed_modules = [m for m, s in modules_status.items() if s.startswith('❌')]
    
    if failed_modules:
        console.print(f"[red]❌ {len(failed_modules)} module(s) failed[/red]")
        return False
    else:
        console.print(f"[green]✅ All {len(modules_status)} modules working correctly[/green]")
        return True

if __name__ == "__main__":
    # Quick module test first
    if not test_all_modules():
        console.print("[red]❌ Module test failed - cannot proceed with full test suite[/red]")
        sys.exit(1)
    
    # Run full test suite
    asyncio.run(main())
