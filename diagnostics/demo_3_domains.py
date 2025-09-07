#!/usr/bin/env python3
"""
Demo: Test 3 domains with network detection and screenshot proof
"""

import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from src.dynadock.testing.network_analyzer import analyze_network_connectivity
from src.dynadock.testing.system_checker import check_system_status
from src.dynadock.testing.browser_tester import setup_screenshots_dir, test_domain_headless

def print_header():
    print("🚀 DEMO: 3 Domeny z dowodami sieciowymi i zrzutami ekranu")
    print("=" * 60)
    print(f"⏰ Start: {datetime.now().strftime('%H:%M:%S')}")
    print()

def check_system_first():
    """Check system status before testing"""
    print("🖥️  Sprawdzanie stanu systemu...")
    status = check_system_status()
    containers = status.get('containers', [])
    ports = status.get('ports_listening', {})
    
    print(f"   📦 Kontenery Docker: {len(containers)}")
    print(f"   🌐 Porty nasłuchujące: {len(ports)}")
    
    if containers:
        print("   📋 Aktywne kontenery:")
        for container in containers[:5]:  # Show first 5
            print(f"      - {container}")
    
    open_ports = [p for p, status in ports.items() if status][:8]
    if open_ports:
        print(f"   📡 Otwarte porty: {open_ports}")
    
    print()

def test_network_connectivity(url, domain_name):
    """Test network connectivity for a domain"""
    print(f"🌐 Testowanie: {domain_name}")
    print(f"📍 URL: {url}")
    print("-" * 40)
    
    result = analyze_network_connectivity(url)
    
    # Basic info
    print(f"   🏷️  Hostname: {result['hostname']}")
    print(f"   🔌 Port: {result['port']}")
    print(f"   📋 Protokół: {result['scheme']}")
    
    # DNS Resolution
    dns = result.get('dns_resolution', {})
    if dns.get('success'):
        print(f"   ✅ DNS Resolution: {result['hostname']} → {dns['ip']}")
        network_detected = True
    else:
        print(f"   ❌ DNS Resolution: Błąd - {dns.get('error', 'Nieznany')}")
        network_detected = False
    
    # TCP Connection
    tcp_success = result.get('tcp_connect', False)
    if tcp_success:
        print(f"   ✅ TCP Connection: Port {result['port']} dostępny")
        network_detected = True
    else:
        print(f"   ❌ TCP Connection: Port {result['port']} niedostępny")
    
    # Port scan results
    port_scan = result.get('port_scan', {})
    open_ports = [p for p, is_open in port_scan.items() if is_open]
    if open_ports:
        print(f"   📡 Wykryte otwarte porty: {open_ports}")
    else:
        print(f"   📡 Brak wykrytych otwartych portów")
    
    # SSL Certificate info
    if result['scheme'] == 'https':
        ssl_info = result.get('ssl_cert_info')
        if ssl_info and not ssl_info.get('error'):
            subject = ssl_info.get('subject', {})
            common_name = subject.get('commonName', 'Nieznany')
            print(f"   🔒 SSL Certyfikat: {common_name}")
        elif ssl_info and ssl_info.get('error'):
            print(f"   ⚠️  SSL Problem: {ssl_info['error']}")
    
    print(f"   🎯 Status wykrywania w sieci: {'✅ WYKRYTO' if network_detected or tcp_success else '❌ NIE WYKRYTO'}")
    print()
    
    return network_detected or tcp_success, result

async def test_browser_with_screenshot(url, domain_name):
    """Test browser access and take screenshot"""
    print(f"📸 Test przeglądarki dla: {domain_name}")
    print("-" * 30)
    
    try:
        result = await test_domain_headless(url, timeout=15)
        
        if result['success']:
            print(f"   ✅ Test przeglądarki: SUKCES")
            print(f"   📊 Status HTTP: {result['status']}")
            print(f"   ⚡ Czas ładowania: {result['load_time']:.2f}s")
            
            screenshot_path = result.get('screenshot_path')
            if screenshot_path and Path(screenshot_path).exists():
                print(f"   📸 Zrzut ekranu: {screenshot_path}")
                print(f"   📁 Rozmiar pliku: {Path(screenshot_path).stat().st_size} bajtów")
            else:
                print(f"   ❌ Zrzut ekranu: Nie utworzono")
            
            # Network requests
            network_requests = result.get('network_requests', [])
            print(f"   🌐 Żądania sieciowe: {len(network_requests)}")
            
            # Console logs
            console_logs = result.get('console_logs', [])
            print(f"   📝 Logi konsoli: {len(console_logs)}")
            
            # Errors
            errors = result.get('errors', [])
            ssl_errors = result.get('ssl_errors', [])
            if errors:
                print(f"   ⚠️  Błędy: {len(errors)}")
                for error in errors[:2]:  # Show first 2 errors
                    print(f"      - {error}")
            if ssl_errors:
                print(f"   🔒 Błędy SSL: {len(ssl_errors)}")
            
            return True, screenshot_path
        else:
            print(f"   ❌ Test przeglądarki: NIEPOWODZENIE")
            error_msg = result.get('error', 'Nieznany błąd')
            print(f"   💥 Błąd: {error_msg}")
            
            # Check for error screenshot
            screenshot_path = result.get('screenshot_path')
            if screenshot_path and Path(screenshot_path).exists():
                print(f"   📸 Zrzut błędu: {screenshot_path}")
                return False, screenshot_path
            
            return False, None
            
    except Exception as e:
        print(f"   ❌ Wyjątek podczas testu: {e}")
        return False, None

async def main():
    """Main demo function"""
    print_header()
    
    # Setup screenshots
    screenshots_dir = setup_screenshots_dir()
    print(f"📁 Katalog zrzutów: {screenshots_dir}")
    print()
    
    # Check system first
    check_system_first()
    
    # Define test domains
    test_domains = [
        ('http://localhost:8000/', 'Localhost Direct Access'),
        ('https://frontend.dynadock.lan/', 'Frontend Local Domain'),
        ('https://mailhog.dynadock.lan/', 'MailHog Local Domain')
    ]
    
    results = []
    
    print("🧪 ROZPOCZĘCIE TESTÓW DOMEN")
    print("=" * 40)
    
    for i, (url, name) in enumerate(test_domains, 1):
        print(f"\n📋 TEST {i}/3: {name}")
        print("=" * 50)
        
        # Network connectivity test
        network_ok, network_result = test_network_connectivity(url, name)
        
        # Browser test with screenshot
        browser_ok, screenshot_path = await test_browser_with_screenshot(url, name)
        
        # Summary for this domain
        overall_status = "✅ SUKCES" if network_ok and browser_ok else "⚠️  CZĘŚCIOWO" if network_ok or browser_ok else "❌ NIEPOWODZENIE"
        print(f"🎯 WYNIK dla {name}: {overall_status}")
        
        results.append({
            'url': url,
            'name': name,
            'network_ok': network_ok,
            'browser_ok': browser_ok,
            'screenshot_path': screenshot_path,
            'overall_ok': network_ok and browser_ok
        })
        
        print()
    
    # Final summary
    print("🎉 PODSUMOWANIE TESTÓW")
    print("=" * 30)
    
    for i, result in enumerate(results, 1):
        status = "✅" if result['overall_ok'] else "⚠️" if result['network_ok'] or result['browser_ok'] else "❌"
        print(f"{i}. {result['name']}: {status}")
        print(f"   📍 URL: {result['url']}")
        print(f"   🌐 Sieć: {'✅' if result['network_ok'] else '❌'}")
        print(f"   📸 Przeglądarka: {'✅' if result['browser_ok'] else '❌'}")
        if result['screenshot_path']:
            print(f"   📁 Zrzut: {result['screenshot_path']}")
        print()
    
    # Count successes
    total_success = sum(1 for r in results if r['overall_ok'])
    network_success = sum(1 for r in results if r['network_ok'])
    browser_success = sum(1 for r in results if r['browser_ok'])
    
    print(f"📊 STATYSTYKI:")
    print(f"   Pełny sukces: {total_success}/3 domen")
    print(f"   Wykrywanie sieciowe: {network_success}/3 domen")
    print(f"   Testy przeglądarki: {browser_success}/3 domen")
    
    # Show screenshots directory
    screenshot_files = list(screenshots_dir.glob('*.png')) if screenshots_dir.exists() else []
    print(f"   Utworzone zrzuty: {len(screenshot_files)}")
    
    if screenshot_files:
        print(f"📁 Pliki zrzutów ekranu:")
        for screenshot in screenshot_files:
            size_kb = screenshot.stat().st_size // 1024
            print(f"   - {screenshot.name} ({size_kb} KB)")
    
    print(f"\n⏰ Zakończono: {datetime.now().strftime('%H:%M:%S')}")
    
    return total_success == 3

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test przerwany przez użytkownika")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Błąd krytyczny: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
