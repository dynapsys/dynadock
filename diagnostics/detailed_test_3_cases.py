#!/usr/bin/env python3
"""
Szczegółowe testy 3 przypadków z zwiększoną ilością logów
"""

import sys
import os
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def debug_imports():
    """Debug import issues"""
    try:
        from src.dynadock.testing.network_analyzer import analyze_network_connectivity
        print("✓ network_analyzer import OK")
    except Exception as e:
        print(f"✗ network_analyzer import failed: {e}")
        return False
    
    try:
        from src.dynadock.testing.system_checker import check_system_status
        print("✓ system_checker import OK") 
    except Exception as e:
        print(f"✗ system_checker import failed: {e}")
        return False
        
    try:
        from src.dynadock.testing.browser_tester import setup_screenshots_dir, test_domain_headless
        print("✓ browser_tester import OK")
    except Exception as e:
        print(f"✗ browser_tester import failed: {e}")
        return False
        
    return True

from src.dynadock.testing.network_analyzer import analyze_network_connectivity
from src.dynadock.testing.system_checker import check_system_status
from src.dynadock.testing.browser_tester import setup_screenshots_dir, test_domain_headless

def print_header():
    print("🔍 SZCZEGÓŁOWE TESTY 3 PRZYPADKÓW Z VERBOSE LOGGING")
    print("=" * 70)
    print(f"🕒 Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📁 Katalog: {os.getcwd()}")
    print()

def detailed_system_check():
    """Szczegółowe sprawdzenie systemu"""
    print("🖥️  FAZA 1: SZCZEGÓŁOWA ANALIZA SYSTEMU")
    print("=" * 50)
    
    # System status
    print("📊 Sprawdzanie stanu systemu...")
    status = check_system_status()
    
    containers = status.get('containers', [])
    ports = status.get('ports_listening', {})
    hosts = status.get('hosts_file', {})
    processes = status.get('processes', [])
    
    print(f"   📦 Docker kontenery: {len(containers)}")
    if containers:
        for i, container in enumerate(containers[:10], 1):
            print(f"      {i}. {container}")
    
    print(f"   🌐 Porty nasłuchujące: {len(ports)}")
    if ports:
        for port, status in list(ports.items())[:10]:
            status_txt = "AKTYWNY" if status else "NIEAKTYWNY"
            print(f"      Port {port}: {status_txt}")
    
    print(f"   📝 Wpisy hosts: {len(hosts)}")
    if hosts:
        for domain, ip in list(hosts.items())[:5]:
            print(f"      {domain} → {ip}")
    
    print(f"   🔧 Procesy: {len(processes)} znalezionych")
    
    # Docker detailed check
    print("\n🐳 Szczegółowa analiza Docker...")
    try:
        docker_ps = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'], 
                                 capture_output=True, text=True, timeout=10)
        if docker_ps.returncode == 0:
            lines = docker_ps.stdout.strip().split('\n')
            print(f"   📋 Szczegóły kontenerów:")
            for line in lines:
                print(f"      {line}")
        else:
            print(f"   ❌ Docker ps failed: {docker_ps.returncode}")
    except Exception as e:
        print(f"   ⚠️  Docker check error: {e}")
    
    # Network interfaces
    print("\n🌐 Interfejsy sieciowe...")
    try:
        ip_result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
        if ip_result.returncode == 0:
            lines = ip_result.stdout.split('\n')
            interfaces = [line for line in lines if ': ' in line and 'lo:' not in line][:5]
            for interface in interfaces:
                print(f"      {interface.strip()}")
    except:
        print(f"   ⚠️  Cannot check network interfaces")
    
    print()

def detailed_network_test(url, case_name):
    """Szczegółowy test sieciowy z verbose logging"""
    print(f"🌐 FAZA 2: SZCZEGÓŁOWA ANALIZA SIECIOWA - {case_name}")
    print("=" * 60)
    print(f"📍 URL: {url}")
    print()
    
    # Run with verbose logging
    print("🔍 Uruchamianie szczegółowej analizy sieciowej...")
    result = analyze_network_connectivity(url, verbose=True)
    
    print(f"\n📊 PODSUMOWANIE ANALIZY SIECIOWEJ:")
    print(f"   🏷️  Hostname: {result['hostname']}")
    print(f"   🔌 Port: {result['port']}")
    print(f"   📋 Protokół: {result['scheme']}")
    
    # Timing analysis
    timing = result.get('timing', {})
    if timing:
        print(f"\n⏱️  ANALIZA CZASÓW:")
        for operation, time_val in timing.items():
            print(f"      {operation}: {time_val:.3f}s")
    
    # Detailed results
    dns = result.get('dns_resolution', {})
    if dns:
        print(f"\n🔍 DNS RESOLUTION:")
        if dns.get('success'):
            print(f"      ✅ SUCCESS: {result['hostname']} → {dns['ip']}")
            print(f"      ⏱️  Czas: {dns.get('time', 0):.3f}s")
        else:
            print(f"      ❌ FAILED: {dns.get('error', 'Unknown')}")
            print(f"      ⏱️  Czas: {dns.get('time', 0):.3f}s")
    
    tcp_success = result.get('tcp_connect', False)
    print(f"\n🔌 TCP CONNECTION:")
    print(f"      {('✅ SUCCESS' if tcp_success else '❌ FAILED')}: Port {result['port']}")
    if 'tcp' in timing:
        print(f"      ⏱️  Czas: {timing['tcp']:.3f}s")
    
    # Port scan details
    port_scan = result.get('port_scan', {})
    open_ports = [p for p, open in port_scan.items() if open]
    closed_ports = [p for p, open in port_scan.items() if not open]
    
    print(f"\n📡 PORT SCAN RESULTS:")
    print(f"      ✅ Otwarte porty ({len(open_ports)}): {sorted(open_ports)}")
    print(f"      ❌ Zamknięte porty ({len(closed_ports)}): {sorted(closed_ports)}")
    if 'port_scan' in timing:
        print(f"      ⏱️  Czas skanowania: {timing['port_scan']:.3f}s")
    
    # SSL info
    if result['scheme'] == 'https':
        ssl_info = result.get('ssl_cert_info')
        print(f"\n🔒 SSL CERTIFICATE:")
        if ssl_info and not ssl_info.get('error'):
            subject = ssl_info.get('subject', {})
            issuer = ssl_info.get('issuer', {})
            print(f"      ✅ SUCCESS")
            print(f"      📋 Subject CN: {subject.get('commonName', 'Unknown')}")
            print(f"      🏢 Issuer: {issuer.get('organizationName', 'Unknown')}")
            print(f"      📅 Expires: {ssl_info.get('notAfter', 'Unknown')}")
            if ssl_info.get('time'):
                print(f"      ⏱️  Czas: {ssl_info['time']:.3f}s")
        else:
            error = ssl_info.get('error', 'Unknown') if ssl_info else 'No SSL info'
            print(f"      ❌ FAILED: {error}")
    
    # Logs analysis
    logs = result.get('logs', [])
    print(f"\n📝 SZCZEGÓŁOWE LOGI ({len(logs)} wpisów):")
    for i, log_entry in enumerate(logs, 1):
        print(f"      {i:2d}. {log_entry}")
    
    # Summary
    network_detected = (dns.get('success', False) or tcp_success or bool(open_ports))
    status = "✅ WYKRYTO W SIECI" if network_detected else "❌ BRAK W SIECI"
    print(f"\n🎯 KOŃCOWY WYNIK: {status}")
    
    return network_detected, result

async def detailed_browser_test(url, case_name):
    """Szczegółowy test przeglądarki z verbose logging"""
    print(f"\n📸 FAZA 3: SZCZEGÓŁOWY TEST PRZEGLĄDARKI - {case_name}")
    print("=" * 60)
    print(f"📍 URL: {url}")
    print()
    
    try:
        # Test with verbose logging
        print("🔍 Uruchamianie szczegółowego testu przeglądarki...")
        result = await test_domain_headless(url, timeout=15, verbose=True)
        
        print(f"\n📊 PODSUMOWANIE TESTU PRZEGLĄDARKI:")
        if result['success']:
            print(f"   ✅ Status: SUKCES")
            print(f"   📊 HTTP Status: {result.get('status', 'N/A')}")
            print(f"   ⚡ Czas ładowania: {result.get('load_time', 0):.3f}s")
            
            screenshot_path = result.get('screenshot_path')
            if screenshot_path and Path(screenshot_path).exists():
                size_kb = Path(screenshot_path).stat().st_size // 1024
                print(f"   📸 Zrzut ekranu: {Path(screenshot_path).name} ({size_kb} KB)")
            
            # Network requests analysis
            network_requests = result.get('network_requests', [])
            print(f"   🌐 Żądania sieciowe: {len(network_requests)}")
            for i, req in enumerate(network_requests[:5], 1):
                print(f"      {i}. {req.get('method', 'GET')} {req.get('url', 'Unknown')}")
            
            # Console logs
            console_logs = result.get('console_logs', [])
            print(f"   📝 Logi konsoli: {len(console_logs)}")
            for i, log in enumerate(console_logs[:3], 1):
                print(f"      {i}. [{log.get('type', 'log')}] {log.get('text', '')[:50]}...")
            
            # Errors
            errors = result.get('errors', [])
            ssl_errors = result.get('ssl_errors', [])
            if errors:
                print(f"   ⚠️  Błędy ({len(errors)}):")
                for i, error in enumerate(errors[:3], 1):
                    print(f"      {i}. {error[:60]}...")
            if ssl_errors:
                print(f"   🔒 Błędy SSL ({len(ssl_errors)}):")
                for i, error in enumerate(ssl_errors[:2], 1):
                    print(f"      {i}. {error[:60]}...")
            
            return True, result
        else:
            print(f"   ❌ Status: NIEPOWODZENIE")
            print(f"   💥 Błąd: {result.get('error', 'Unknown')}")
            return False, result
            
    except Exception as e:
        print(f"   ❌ WYJĄTEK: {e}")
        return False, {'error': str(e)}

def detailed_curl_verification(url, case_name):
    """Szczegółowa weryfikacja z curl"""
    print(f"\n🌐 FAZA 4: WERYFIKACJA CURL - {case_name}")
    print("=" * 50)
    
    print("🔍 Test podstawowy curl...")
    try:
        curl_cmd = ['curl', '-v', '--max-time', '10', '--head', url]
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
        
        print(f"   📊 Kod powrotu: {result.returncode}")
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            status_line = lines[0] if lines else 'Unknown'
            print(f"   ✅ Status: {status_line}")
            
            # Show headers
            headers = [line for line in lines[1:6] if line.strip()]
            print(f"   📋 Nagłówki:")
            for header in headers:
                print(f"      {header}")
        else:
            print(f"   ❌ Curl failed")
            stderr_lines = result.stderr.strip().split('\n')[:3]
            for line in stderr_lines:
                if line.strip():
                    print(f"      {line}")
        
        # Verbose output analysis
        if result.stderr:
            verbose_lines = result.stderr.split('\n')
            connect_lines = [line for line in verbose_lines if 'connect' in line.lower()][:3]
            if connect_lines:
                print(f"   🔌 Informacje o połączeniu:")
                for line in connect_lines:
                    print(f"      {line.strip()}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"   ❌ Curl error: {e}")
        return False

async def run_detailed_case_test(url, case_name):
    """Uruchom szczegółowy test dla jednego przypadku"""
    print(f"\n{'='*80}")
    print(f"🎯 SZCZEGÓŁOWY TEST PRZYPADKU: {case_name}")
    print(f"📍 URL: {url}")
    print(f"🕒 Czas: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    # Phase 1: Network analysis
    network_ok, network_result = detailed_network_test(url, case_name)
    
    # Phase 2: Browser test
    browser_ok, browser_result = await detailed_browser_test(url, case_name)
    
    # Phase 3: Curl verification
    curl_ok = detailed_curl_verification(url, case_name)
    
    # Summary for this case
    print(f"\n🎯 PODSUMOWANIE PRZYPADKU: {case_name}")
    print("=" * 50)
    print(f"   🌐 Analiza sieciowa: {'✅ SUKCES' if network_ok else '❌ NIEPOWODZENIE'}")
    print(f"   📸 Test przeglądarki: {'✅ SUKCES' if browser_ok else '❌ NIEPOWODZENIE'}")
    print(f"   🌐 Weryfikacja curl: {'✅ SUKCES' if curl_ok else '❌ NIEPOWODZENIE'}")
    
    overall_success = network_ok and browser_ok
    print(f"   🎯 OGÓLNY WYNIK: {'✅ SUKCES' if overall_success else '⚠️ CZĘŚCIOWY' if any([network_ok, browser_ok, curl_ok]) else '❌ NIEPOWODZENIE'}")
    
    return {
        'case_name': case_name,
        'url': url,
        'network_ok': network_ok,
        'browser_ok': browser_ok,
        'curl_ok': curl_ok,
        'overall_success': overall_success,
        'network_result': network_result,
        'browser_result': browser_result
    }

async def main():
    """Main detailed testing function"""
    print_header()
    
    # Debug imports first
    print("🔍 Sprawdzanie importów modułów...")
    if not debug_imports():
        print("❌ Błąd importów - sprawdź instalację modułów")
        return False
    print("✅ Wszystkie importy OK\n")
    
    # Setup
    screenshots_dir = setup_screenshots_dir()
    print(f"📁 Katalog zrzutów: {screenshots_dir}")
    print()
    
    # System check
    detailed_system_check()
    
    # Define test cases
    test_cases = [
        ('http://localhost:8000', 'Localhost Direct Access (HTTP)'),
        ('https://frontend.dynadock.lan', 'Frontend Local Domain (HTTPS)'),
        ('https://mailhog.dynadock.lan', 'MailHog Local Domain (HTTPS)')
    ]
    
    print(f"🧪 ROZPOCZĘCIE SZCZEGÓŁOWYCH TESTÓW 3 PRZYPADKÓW")
    print(f"📊 Liczba przypadków: {len(test_cases)}")
    print()
    
    results = []
    
    # Test each case
    for i, (url, case_name) in enumerate(test_cases, 1):
        print(f"\n🚀 PRZYPADEK {i}/{len(test_cases)}")
        result = await run_detailed_case_test(url, case_name)
        results.append(result)
    
    # Final comprehensive summary
    print(f"\n{'='*80}")
    print(f"🏆 KOŃCOWE PODSUMOWANIE WSZYSTKICH PRZYPADKÓW")
    print(f"{'='*80}")
    
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result['overall_success'] else "⚠️" if any([result['network_ok'], result['browser_ok'], result['curl_ok']]) else "❌"
        print(f"{i}. {result['case_name']}: {status_icon}")
        print(f"   📍 URL: {result['url']}")
        print(f"   🌐 Sieć: {'✅' if result['network_ok'] else '❌'}")
        print(f"   📸 Przeglądarka: {'✅' if result['browser_ok'] else '❌'}")
        print(f"   🌐 Curl: {'✅' if result['curl_ok'] else '❌'}")
        print()
    
    # Statistics
    total_success = sum(1 for r in results if r['overall_success'])
    network_success = sum(1 for r in results if r['network_ok'])
    browser_success = sum(1 for r in results if r['browser_ok'])
    curl_success = sum(1 for r in results if r['curl_ok'])
    
    print(f"📊 STATYSTYKI KOŃCOWE:")
    print(f"   🎯 Pełny sukces: {total_success}/{len(results)} ({(total_success/len(results)*100):.1f}%)")
    print(f"   🌐 Wykrywanie sieciowe: {network_success}/{len(results)} ({(network_success/len(results)*100):.1f}%)")
    print(f"   📸 Testy przeglądarki: {browser_success}/{len(results)} ({(browser_success/len(results)*100):.1f}%)")
    print(f"   🌐 Weryfikacja curl: {curl_success}/{len(results)} ({(curl_success/len(results)*100):.1f}%)")
    
    # Screenshot info
    screenshot_files = list(screenshots_dir.glob('*.png')) if screenshots_dir.exists() else []
    print(f"   📸 Utworzonych zrzutów: {len(screenshot_files)}")
    
    print(f"\n⏰ Zakończono: {datetime.now().strftime('%H:%M:%S')}")
    
    if total_success == len(results):
        print(f"\n🎉 🎉 🎉 WSZYSTKIE PRZYPADKI ZAKOŃCZONE SUKCESEM! 🎉 🎉 🎉")
    elif total_success > 0:
        print(f"\n⚠️  CZĘŚCIOWY SUKCES - {total_success}/{len(results)} przypadków działa poprawnie")
    else:
        print(f"\n❌ BRAK SUKCESÓW - sprawdź konfigurację systemu")
    
    return total_success == len(results)

if __name__ == "__main__":
    print("🚀 Uruchamianie skryptu testowego...")
    try:
        print("⚡ Wywołanie asyncio.run(main())...")
        success = asyncio.run(main())
        print(f"✅ Funkcja main() zakończona sukcesem: {success}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test przerwany przez użytkownika")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Błąd krytyczny w main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
