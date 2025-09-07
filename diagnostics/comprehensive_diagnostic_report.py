#!/usr/bin/env python3
"""
Kompleksowy raport diagnostyczny DynaDock z verbose logging
"""

import sys
import os
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

class DiagnosticReport:
    def __init__(self):
        self.report_data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {},
            'network_tests': {},
            'browser_tests': {},
            'service_status': {},
            'summary': {}
        }
        self.print_with_flush("🔍 INITIALIZING COMPREHENSIVE DYNADOCK DIAGNOSTIC REPORT")
        self.print_with_flush("=" * 70)
    
    def print_with_flush(self, message):
        """Print message with immediate flush"""
        print(message)
        sys.stdout.flush()
    
    def collect_system_info(self):
        """Collect system information"""
        self.print_with_flush("\n📊 COLLECTING SYSTEM INFORMATION")
        self.print_with_flush("-" * 50)
        
        try:
            from src.dynadock.testing.system_checker import check_system_status
            system_status = check_system_status()
            
            containers = system_status.get('containers', [])
            ports = system_status.get('ports_listening', {})
            hosts = system_status.get('hosts_file', {})
            
            self.print_with_flush(f"✅ Docker containers: {len(containers)}")
            for container in containers[:5]:
                self.print_with_flush(f"   • {container}")
            
            active_ports = [p for p, status in ports.items() if status]
            self.print_with_flush(f"✅ Active ports: {len(active_ports)}")
            for port in active_ports[:10]:
                self.print_with_flush(f"   • Port {port}")
            
            self.print_with_flush(f"✅ Hosts entries: {len(hosts)}")
            for domain, ip in list(hosts.items())[:5]:
                self.print_with_flush(f"   • {domain} → {ip}")
            
            self.report_data['system_info'] = {
                'containers': len(containers),
                'container_list': containers[:10],
                'active_ports': len(active_ports),
                'port_list': active_ports[:10],
                'hosts_entries': len(hosts),
                'hosts_sample': dict(list(hosts.items())[:5])
            }
            
            return True
            
        except Exception as e:
            self.print_with_flush(f"❌ System info collection failed: {e}")
            self.report_data['system_info']['error'] = str(e)
            return False
    
    def test_network_connectivity(self):
        """Test network connectivity for all cases"""
        self.print_with_flush("\n🌐 TESTING NETWORK CONNECTIVITY")
        self.print_with_flush("-" * 50)
        
        test_cases = [
            ('http://localhost:8000', 'Localhost Direct HTTP'),
            ('https://frontend.local.dev', 'Frontend Local Domain'),
            ('https://mailhog.local.dev', 'MailHog Local Domain')
        ]
        
        network_results = {}
        
        try:
            from src.dynadock.testing.network_analyzer import analyze_network_connectivity
            
            for i, (url, name) in enumerate(test_cases, 1):
                self.print_with_flush(f"\n🔍 Test {i}: {name}")
                self.print_with_flush(f"   URL: {url}")
                
                try:
                    result = analyze_network_connectivity(url, verbose=True)
                    
                    dns_ok = result.get('dns_resolution', {}).get('success', False)
                    tcp_ok = result.get('tcp_connect', False)
                    port_scan = result.get('port_scan', {})
                    open_ports = [p for p, status in port_scan.items() if status]
                    
                    self.print_with_flush(f"   DNS Resolution: {'✅' if dns_ok else '❌'}")
                    if dns_ok:
                        ip = result.get('dns_resolution', {}).get('ip', 'Unknown')
                        self.print_with_flush(f"      → {result['hostname']} resolves to {ip}")
                    
                    self.print_with_flush(f"   TCP Connection: {'✅' if tcp_ok else '❌'}")
                    self.print_with_flush(f"   Open Ports: {len(open_ports)} found")
                    if open_ports:
                        self.print_with_flush(f"      → {sorted(open_ports)}")
                    
                    # SSL info for HTTPS
                    if url.startswith('https'):
                        ssl_info = result.get('ssl_cert_info')
                        if ssl_info and not ssl_info.get('error'):
                            self.print_with_flush(f"   SSL Certificate: ✅")
                            subject = ssl_info.get('subject', {})
                            self.print_with_flush(f"      → CN: {subject.get('commonName', 'Unknown')}")
                        else:
                            self.print_with_flush(f"   SSL Certificate: ❌")
                    
                    # Timing information
                    timing = result.get('timing', {})
                    if timing:
                        self.print_with_flush(f"   Performance:")
                        for operation, time_val in timing.items():
                            self.print_with_flush(f"      → {operation}: {time_val:.3f}s")
                    
                    network_detected = dns_ok or tcp_ok or bool(open_ports)
                    status = "✅ NETWORK DETECTED" if network_detected else "❌ NO NETWORK"
                    self.print_with_flush(f"   Overall: {status}")
                    
                    network_results[name] = {
                        'url': url,
                        'dns_success': dns_ok,
                        'tcp_success': tcp_ok,
                        'open_ports': len(open_ports),
                        'network_detected': network_detected,
                        'timing': timing
                    }
                    
                except Exception as e:
                    self.print_with_flush(f"   ❌ Network test error: {e}")
                    network_results[name] = {
                        'url': url,
                        'error': str(e),
                        'network_detected': False
                    }
            
            self.report_data['network_tests'] = network_results
            return len([r for r in network_results.values() if r.get('network_detected', False)]) > 0
            
        except Exception as e:
            self.print_with_flush(f"❌ Network testing module error: {e}")
            self.report_data['network_tests']['module_error'] = str(e)
            return False
    
    async def test_browser_functionality(self):
        """Test browser functionality"""
        self.print_with_flush("\n📸 TESTING BROWSER FUNCTIONALITY")
        self.print_with_flush("-" * 50)
        
        test_cases = [
            ('http://localhost:8000', 'Localhost Direct HTTP'),
            ('https://frontend.local.dev', 'Frontend Local Domain'),
            ('https://mailhog.local.dev', 'MailHog Local Domain')
        ]
        
        browser_results = {}
        
        try:
            from src.dynadock.testing.browser_tester import test_domain_headless, setup_screenshots_dir
            
            # Setup screenshots directory
            screenshots_dir = setup_screenshots_dir()
            self.print_with_flush(f"📁 Screenshots directory: {screenshots_dir}")
            
            for i, (url, name) in enumerate(test_cases, 1):
                self.print_with_flush(f"\n🔍 Browser Test {i}: {name}")
                self.print_with_flush(f"   URL: {url}")
                
                try:
                    result = await test_domain_headless(url, timeout=10, verbose=True)
                    
                    if result['success']:
                        self.print_with_flush(f"   Status: ✅ SUCCESS")
                        self.print_with_flush(f"   HTTP Code: {result.get('status', 'N/A')}")
                        self.print_with_flush(f"   Load Time: {result.get('load_time', 0):.3f}s")
                        
                        # Screenshot info
                        screenshot_path = result.get('screenshot_path')
                        if screenshot_path and Path(screenshot_path).exists():
                            size_kb = Path(screenshot_path).stat().st_size // 1024
                            self.print_with_flush(f"   Screenshot: {Path(screenshot_path).name} ({size_kb} KB)")
                        
                        # Network requests and logs
                        network_requests = result.get('network_requests', [])
                        console_logs = result.get('console_logs', [])
                        errors = result.get('errors', [])
                        ssl_errors = result.get('ssl_errors', [])
                        
                        self.print_with_flush(f"   Network Requests: {len(network_requests)}")
                        self.print_with_flush(f"   Console Logs: {len(console_logs)}")
                        self.print_with_flush(f"   Errors: {len(errors)}")
                        self.print_with_flush(f"   SSL Errors: {len(ssl_errors)}")
                        
                        browser_results[name] = {
                            'url': url,
                            'success': True,
                            'http_status': result.get('status'),
                            'load_time': result.get('load_time', 0),
                            'screenshot_captured': screenshot_path is not None,
                            'network_requests': len(network_requests),
                            'console_logs': len(console_logs),
                            'errors': len(errors),
                            'ssl_errors': len(ssl_errors)
                        }
                    else:
                        self.print_with_flush(f"   Status: ❌ FAILED")
                        self.print_with_flush(f"   Error: {result.get('error', 'Unknown')}")
                        
                        browser_results[name] = {
                            'url': url,
                            'success': False,
                            'error': result.get('error', 'Unknown')
                        }
                    
                except Exception as e:
                    self.print_with_flush(f"   ❌ Browser test error: {e}")
                    browser_results[name] = {
                        'url': url,
                        'success': False,
                        'error': str(e)
                    }
            
            self.report_data['browser_tests'] = browser_results
            return len([r for r in browser_results.values() if r.get('success', False)]) > 0
            
        except Exception as e:
            self.print_with_flush(f"❌ Browser testing module error: {e}")
            self.report_data['browser_tests']['module_error'] = str(e)
            return False
    
    def test_service_availability(self):
        """Test service availability with curl"""
        self.print_with_flush("\n🌍 TESTING SERVICE AVAILABILITY")
        self.print_with_flush("-" * 50)
        
        test_urls = [
            'http://localhost:8000',
            'http://localhost:8001', 
            'http://localhost:8025',
            'https://frontend.local.dev',
            'https://mailhog.local.dev'
        ]
        
        service_results = {}
        
        for url in test_urls:
            self.print_with_flush(f"\n🔍 Testing: {url}")
            try:
                cmd = ['curl', '-s', '-w', '%{http_code}', '-o', '/dev/null', '--max-time', '5', url]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    http_code = result.stdout.strip()
                    self.print_with_flush(f"   ✅ HTTP {http_code}")
                    service_results[url] = {
                        'available': True,
                        'http_code': http_code,
                        'response_time': 'OK'
                    }
                else:
                    self.print_with_flush(f"   ❌ Connection failed")
                    service_results[url] = {
                        'available': False,
                        'error': 'Connection failed'
                    }
                    
            except Exception as e:
                self.print_with_flush(f"   ❌ Test error: {e}")
                service_results[url] = {
                    'available': False,
                    'error': str(e)
                }
        
        self.report_data['service_status'] = service_results
        return len([r for r in service_results.values() if r.get('available', False)]) > 0
    
    def generate_summary(self, system_ok, network_ok, browser_ok, services_ok):
        """Generate comprehensive summary"""
        self.print_with_flush("\n📋 COMPREHENSIVE DIAGNOSTIC SUMMARY")
        self.print_with_flush("=" * 70)
        
        # Calculate statistics
        network_tests = self.report_data.get('network_tests', {})
        browser_tests = self.report_data.get('browser_tests', {})
        service_tests = self.report_data.get('service_status', {})
        
        network_success = len([t for t in network_tests.values() if isinstance(t, dict) and t.get('network_detected', False)])
        browser_success = len([t for t in browser_tests.values() if isinstance(t, dict) and t.get('success', False)])
        service_success = len([t for t in service_tests.values() if t.get('available', False)])
        
        total_network = len([t for t in network_tests.values() if isinstance(t, dict)])
        total_browser = len([t for t in browser_tests.values() if isinstance(t, dict)])
        total_services = len(service_tests)
        
        self.print_with_flush(f"🖥️  System Status: {'✅' if system_ok else '❌'}")
        self.print_with_flush(f"🌐 Network Detection: {network_success}/{total_network} ({(network_success/max(total_network,1)*100):.1f}%)")
        self.print_with_flush(f"📸 Browser Tests: {browser_success}/{total_browser} ({(browser_success/max(total_browser,1)*100):.1f}%)")
        self.print_with_flush(f"🌍 Service Availability: {service_success}/{total_services} ({(service_success/max(total_services,1)*100):.1f}%)")
        
        # Overall health assessment
        total_checks = sum([system_ok, network_ok, browser_ok, services_ok])
        health_percentage = (total_checks / 4) * 100
        
        if health_percentage >= 75:
            health_status = "🟢 EXCELLENT"
        elif health_percentage >= 50:
            health_status = "🟡 GOOD"
        elif health_percentage >= 25:
            health_status = "🟠 PARTIAL"
        else:
            health_status = "🔴 CRITICAL"
        
        self.print_with_flush(f"\n🏆 OVERALL DYNADOCK HEALTH: {health_status} ({health_percentage:.1f}%)")
        
        # Recommendations
        self.print_with_flush(f"\n💡 RECOMMENDATIONS:")
        if not system_ok:
            self.print_with_flush(f"   • Check Docker containers and port availability")
        if not network_ok:
            self.print_with_flush(f"   • Verify DNS resolution and network connectivity")  
        if not browser_ok:
            self.print_with_flush(f"   • Check browser dependencies and screenshot capability")
        if not services_ok:
            self.print_with_flush(f"   • Verify service URLs and SSL certificates")
        
        if total_checks == 4:
            self.print_with_flush(f"   🎉 All systems operational - DynaDock is working perfectly!")
        
        self.report_data['summary'] = {
            'system_ok': system_ok,
            'network_ok': network_ok,
            'browser_ok': browser_ok,
            'services_ok': services_ok,
            'health_percentage': health_percentage,
            'health_status': health_status,
            'network_success_rate': (network_success/max(total_network,1)*100),
            'browser_success_rate': (browser_success/max(total_browser,1)*100),
            'service_success_rate': (service_success/max(total_services,1)*100)
        }
    
    def save_json_report(self):
        """Save detailed JSON report"""
        report_file = Path('dynadock_diagnostic_report.json')
        try:
            with open(report_file, 'w') as f:
                json.dump(self.report_data, f, indent=2, default=str)
            self.print_with_flush(f"\n💾 Detailed report saved: {report_file}")
            return str(report_file)
        except Exception as e:
            self.print_with_flush(f"\n❌ Failed to save report: {e}")
            return None

async def main():
    """Main diagnostic function"""
    report = DiagnosticReport()
    
    # Run all diagnostic phases
    report.print_with_flush(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    
    system_ok = report.collect_system_info()
    network_ok = report.test_network_connectivity()
    browser_ok = await report.test_browser_functionality()
    services_ok = report.test_service_availability()
    
    # Generate summary and save report
    report.generate_summary(system_ok, network_ok, browser_ok, services_ok)
    report_file = report.save_json_report()
    
    report.print_with_flush(f"⏰ Completed: {datetime.now().strftime('%H:%M:%S')}")
    
    return all([system_ok, network_ok, browser_ok, services_ok])

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n🎯 DIAGNOSTIC COMPLETE - {'SUCCESS' if success else 'ISSUES FOUND'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Diagnostic interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
