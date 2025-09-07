#!/usr/bin/env python3
"""
Production-ready DynaDock Testing Framework
Modular, comprehensive testing with clear output and diagnostics
"""

import sys
import os
import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def print_header():
    """Print test framework header"""
    print("=" * 60)
    print("🚀 DynaDock Enhanced Testing Framework")
    print("=" * 60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Directory: {os.getcwd()}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print()

def test_module_imports():
    """Test all refactored module imports"""
    print("📦 Phase 1: Testing Module Imports")
    print("-" * 40)
    
    modules = {
        'network_analyzer': 'src.dynadock.testing.network_analyzer',
        'system_checker': 'src.dynadock.testing.system_checker',
        'browser_tester': 'src.dynadock.testing.browser_tester',
        'auto_repair': 'src.dynadock.testing.auto_repair'
    }
    
    results = {}
    
    for name, module_path in modules.items():
        try:
            __import__(module_path)
            print(f"  ✅ {name}: Import successful")
            results[name] = True
        except Exception as e:
            print(f"  ❌ {name}: Import failed - {e}")
            results[name] = False
    
    success_count = sum(results.values())
    print(f"\n📊 Import Results: {success_count}/{len(modules)} modules imported successfully")
    
    return all(results.values()), results

def test_module_functionality():
    """Test core functionality of each module"""
    print("\n🔧 Phase 2: Testing Module Functionality")
    print("-" * 40)
    
    # Import modules
    from src.dynadock.testing.network_analyzer import analyze_network_connectivity
    from src.dynadock.testing.system_checker import check_system_status
    from src.dynadock.testing.browser_tester import setup_screenshots_dir, cleanup_old_screenshots
    from src.dynadock.testing.auto_repair import repair_hosts_file
    
    results = {}
    
    # Test 1: Network Analysis
    try:
        print("  🌐 Testing network analyzer...")
        result = analyze_network_connectivity('http://localhost:8000')
        print(f"    ✅ Network analyzer: {result['hostname']}:{result['port']} ({result['scheme']})")
        results['network_analyzer'] = True
    except Exception as e:
        print(f"    ❌ Network analyzer failed: {e}")
        results['network_analyzer'] = False
    
    # Test 2: System Status
    try:
        print("  🖥️  Testing system checker...")
        status = check_system_status()
        containers = len(status.get('containers', []))
        ports = len(status.get('ports_listening', {}))
        print(f"    ✅ System checker: {containers} containers, {ports} listening ports")
        results['system_checker'] = True
    except Exception as e:
        print(f"    ❌ System checker failed: {e}")
        results['system_checker'] = False
    
    # Test 3: Browser Testing Setup
    try:
        print("  📸 Testing browser tester...")
        cleanup_old_screenshots()
        screenshots_dir = setup_screenshots_dir()
        print(f"    ✅ Browser tester: Screenshots dir ready at {screenshots_dir}")
        results['browser_tester'] = True
    except Exception as e:
        print(f"    ❌ Browser tester failed: {e}")
        results['browser_tester'] = False
    
    # Test 4: Auto Repair
    try:
        print("  🛠️  Testing auto repair...")
        hosts_result = repair_hosts_file()
        status_indicator = "✅" if "✅" in hosts_result else "⚠️" if "⚠️" in hosts_result else "❓"
        print(f"    {status_indicator} Auto repair: Hosts file check completed")
        results['auto_repair'] = True
    except Exception as e:
        print(f"    ❌ Auto repair failed: {e}")
        results['auto_repair'] = False
    
    success_count = sum(results.values())
    print(f"\n📊 Functionality Results: {success_count}/{len(results)} modules working correctly")
    
    return all(results.values()), results

def test_system_environment():
    """Test the system environment and dependencies"""
    print("\n🏗️  Phase 3: Testing System Environment")
    print("-" * 40)
    
    checks = {}
    
    # Check Docker
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            containers = len(result.stdout.strip().split('\n')) - 1  # Subtract header
            print(f"  ✅ Docker: {containers} running containers")
            checks['docker'] = True
        else:
            print(f"  ❌ Docker: Not available or not running")
            checks['docker'] = False
    except Exception as e:
        print(f"  ❌ Docker: Error - {e}")
        checks['docker'] = False
    
    # Check network connectivity
    try:
        result = subprocess.run(['curl', '-s', '--max-time', '5', 'http://localhost:8000'], 
                              capture_output=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✅ Network: localhost:8000 is accessible")
            checks['network'] = True
        else:
            print(f"  ⚠️  Network: localhost:8000 not responding (may be normal if not running)")
            checks['network'] = False
    except Exception as e:
        print(f"  ⚠️  Network: Cannot test localhost:8000 - {e}")
        checks['network'] = False
    
    # Check required Python packages
    packages = ['rich', 'playwright']
    for package in packages:
        try:
            __import__(package)
            print(f"  ✅ Package: {package} is available")
            checks[f'package_{package}'] = True
        except ImportError:
            print(f"  ❌ Package: {package} is missing")
            checks[f'package_{package}'] = False
    
    success_count = sum(checks.values())
    print(f"\n📊 Environment Results: {success_count}/{len(checks)} checks passed")
    
    return checks

async def run_integration_test():
    """Run a basic integration test"""
    print("\n🔗 Phase 4: Integration Test")
    print("-" * 40)
    
    try:
        print("  🚀 Running integrated test flow...")
        
        # Import the testing modules
        from src.dynadock.testing.network_analyzer import analyze_network_connectivity
        from src.dynadock.testing.system_checker import check_system_status
        
        # Test a few URLs
        test_urls = [
            'http://localhost:8000',
            'https://localhost:443',
            'https://frontend.local.dev'
        ]
        
        results = {}
        for url in test_urls:
            print(f"    🌐 Testing {url}...")
            result = analyze_network_connectivity(url)
            success = result.get('tcp_connect', {}).get('success', False)
            results[url] = success
            status = "✅" if success else "❌"
            print(f"      {status} {url}: {'Connected' if success else 'Failed'}")
        
        # Check system status
        print(f"    🖥️  Checking system status...")
        system_status = check_system_status()
        containers = len(system_status.get('containers', []))
        print(f"      📊 Found {containers} Docker containers")
        
        success_rate = sum(results.values()) / len(results) * 100
        print(f"\n📊 Integration Results: {success_rate:.1f}% of connectivity tests passed")
        
        return success_rate > 50  # At least half should work for basic functionality
        
    except Exception as e:
        print(f"    ❌ Integration test failed: {e}")
        return False

def generate_report(import_results, functionality_results, environment_results, integration_success):
    """Generate comprehensive test report"""
    print("\n📋 Phase 5: Generating Test Report")
    print("-" * 40)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_summary': {
            'imports_passed': sum(import_results.values()),
            'imports_total': len(import_results),
            'functionality_passed': sum(functionality_results.values()),
            'functionality_total': len(functionality_results),
            'environment_passed': sum(environment_results.values()),
            'environment_total': len(environment_results),
            'integration_success': integration_success
        },
        'detailed_results': {
            'imports': import_results,
            'functionality': functionality_results,
            'environment': environment_results,
            'integration': integration_success
        },
        'recommendations': []
    }
    
    # Add recommendations based on results
    if not all(import_results.values()):
        report['recommendations'].append("Some modules failed to import - check Python path and dependencies")
    
    if not all(functionality_results.values()):
        report['recommendations'].append("Some module functionality is broken - check individual module implementations")
    
    if not environment_results.get('docker', True):
        report['recommendations'].append("Docker is not available - some tests will not work properly")
    
    if not environment_results.get('package_rich', True):
        report['recommendations'].append("Rich package missing - install with: pip install rich")
    
    if not environment_results.get('package_playwright', True):
        report['recommendations'].append("Playwright missing - install with: pip install playwright")
    
    # Save report
    report_file = Path('test_framework_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"  💾 Report saved to: {report_file}")
    
    # Print summary
    overall_success = (
        all(import_results.values()) and 
        all(functionality_results.values()) and
        integration_success
    )
    
    print(f"\n📊 Overall Status: {'✅ SUCCESS' if overall_success else '⚠️  PARTIAL SUCCESS'}")
    
    return overall_success, report

def main():
    """Main test runner"""
    try:
        print_header()
        
        # Phase 1: Test imports
        import_success, import_results = test_module_imports()
        
        if not import_success:
            print("\n❌ Critical: Module imports failed. Cannot proceed with functionality tests.")
            return False
        
        # Phase 2: Test functionality  
        functionality_success, functionality_results = test_module_functionality()
        
        # Phase 3: Test environment
        environment_results = test_system_environment()
        
        # Phase 4: Integration test
        integration_success = asyncio.run(run_integration_test())
        
        # Phase 5: Generate report
        overall_success, report = generate_report(
            import_results, functionality_results, environment_results, integration_success
        )
        
        print(f"\n🎯 Final Result: {'SUCCESS' if overall_success else 'PARTIAL SUCCESS'}")
        print(f"📊 Full report available in: test_framework_report.json")
        print("=" * 60)
        
        return overall_success
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
