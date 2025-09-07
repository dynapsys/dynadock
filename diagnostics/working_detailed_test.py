#!/usr/bin/env python3
"""
Działający szczegółowy test 3 przypadków z verbose logging
"""

import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_network_case(url, case_name):
    """Test network connectivity with verbose logging"""
    print(f"\n🌐 SZCZEGÓŁOWY TEST SIECIOWY: {case_name}")
    print(f"📍 URL: {url}")
    print("-" * 60)
    
    try:
        from src.dynadock.testing.network_analyzer import analyze_network_connectivity
        
        print("🔍 Uruchamianie analizy sieciowej z verbose logging...")
        result = analyze_network_connectivity(url, verbose=True)
        
        print(f"\n📊 WYNIKI ANALIZY:")
        print(f"   🎯 Hostname: {result['hostname']}")
        print(f"   🔌 Port: {result['port']}")
        print(f"   📋 Schemat: {result['scheme']}")
        
        # DNS results
        dns = result.get('dns_resolution', {})
        if dns.get('success'):
            print(f"   ✅ DNS: {result['hostname']} → {dns['ip']}")
        else:
            print(f"   ❌ DNS: {dns.get('error', 'Failed')}")
        
        # TCP connection
        tcp_ok = result.get('tcp_connect', False)
        print(f"   {'✅' if tcp_ok else '❌'} TCP: Port {result['port']}")
        
        # Port scan
        port_scan = result.get('port_scan', {})
        open_ports = [p for p, status in port_scan.items() if status]
        print(f"   📡 Otwarte porty: {sorted(open_ports) if open_ports else 'Brak'}")
        
        # Overall network detection
        network_detected = dns.get('success', False) or tcp_ok or bool(open_ports)
        status = "✅ WYKRYTO" if network_detected else "❌ BRAK WYKRYCIA"
        print(f"   🎯 Status sieciowy: {status}")
        
        return network_detected, result
        
    except Exception as e:
        print(f"   ❌ Błąd w teście sieciowym: {e}")
        return False, {'error': str(e)}

async def test_browser_case(url, case_name):
    """Test browser with verbose logging"""
    print(f"\n📸 SZCZEGÓŁOWY TEST PRZEGLĄDARKI: {case_name}")
    print(f"📍 URL: {url}")
    print("-" * 60)
    
    try:
        from src.dynadock.testing.browser_tester import test_domain_headless
        
        print("🔍 Uruchamianie testu przeglądarki z verbose logging...")
        result = await test_domain_headless(url, timeout=10, verbose=True)
        
        print(f"\n📊 WYNIKI TESTU PRZEGLĄDARKI:")
        if result['success']:
            print(f"   ✅ Status: SUKCES")
            print(f"   📊 HTTP Code: {result.get('status', 'N/A')}")
            print(f"   ⚡ Czas ładowania: {result.get('load_time', 0):.3f}s")
            
            # Screenshot info
            screenshot = result.get('screenshot_path')
            if screenshot and Path(screenshot).exists():
                size_kb = Path(screenshot).stat().st_size // 1024
                print(f"   📸 Zrzut ekranu: {Path(screenshot).name} ({size_kb} KB)")
            
            # Network requests
            requests = result.get('network_requests', [])
            print(f"   🌐 Żądania HTTP: {len(requests)}")
            
            # Console logs and errors
            console_logs = result.get('console_logs', [])
            errors = result.get('errors', [])
            ssl_errors = result.get('ssl_errors', [])
            
            print(f"   📝 Logi konsoli: {len(console_logs)}")
            print(f"   ⚠️  Błędy: {len(errors)}")
            print(f"   🔒 Błędy SSL: {len(ssl_errors)}")
        else:
            print(f"   ❌ Status: NIEPOWODZENIE")
            print(f"   💥 Błąd: {result.get('error', 'Unknown')}")
        
        return result['success'], result
        
    except Exception as e:
        print(f"   ❌ Błąd w teście przeglądarki: {e}")
        return False, {'error': str(e)}

def test_system_status():
    """Test system status with details"""
    print(f"\n🖥️  SZCZEGÓŁOWY TEST SYSTEMU")
    print("-" * 50)
    
    try:
        from src.dynadock.testing.system_checker import check_system_status
        
        print("🔍 Sprawdzanie stanu systemu...")
        result = check_system_status()
        
        containers = result.get('containers', [])
        ports = result.get('ports_listening', {})
        hosts = result.get('hosts_file', {})
        
        print(f"   📦 Kontenery Docker: {len(containers)}")
        for i, container in enumerate(containers[:5], 1):
            print(f"      {i}. {container}")
        
        print(f"   🌐 Porty nasłuchujące: {len(ports)}")
        active_ports = [port for port, status in ports.items() if status][:10]
        for port in active_ports:
            print(f"      ✅ Port {port}")
        
        print(f"   📝 Wpisy /etc/hosts: {len(hosts)}")
        for domain, ip in list(hosts.items())[:5]:
            print(f"      {domain} → {ip}")
        
        return len(containers) > 0 or len(active_ports) > 0
        
    except Exception as e:
        print(f"   ❌ Błąd sprawdzania systemu: {e}")
        return False

async def main():
    """Main test function"""
    print("🔍 SZCZEGÓŁOWE TESTY 3 PRZYPADKÓW Z VERBOSE LOGGING")
    print("=" * 70)
    print(f"🕒 Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📁 Katalog: {os.getcwd()}")
    
    # System status
    system_ok = test_system_status()
    
    # Test cases
    test_cases = [
        ('http://localhost:8000', 'Localhost Direct Access (HTTP)'),
        ('https://frontend.local.dev', 'Frontend Local Domain (HTTPS)'),  
        ('https://mailhog.local.dev', 'MailHog Local Domain (HTTPS)')
    ]
    
    print(f"\n🧪 ROZPOCZĘCIE TESTÓW {len(test_cases)} PRZYPADKÓW")
    print("=" * 60)
    
    results = []
    
    for i, (url, case_name) in enumerate(test_cases, 1):
        print(f"\n🚀 PRZYPADEK {i}/{len(test_cases)}: {case_name}")
        print("=" * 80)
        
        # Network test
        network_ok, network_result = test_network_case(url, case_name)
        
        # Browser test  
        browser_ok, browser_result = await test_browser_case(url, case_name)
        
        # Case summary
        overall_success = network_ok and browser_ok
        print(f"\n🎯 PODSUMOWANIE PRZYPADKU {i}:")
        print(f"   🌐 Wykrywanie sieciowe: {'✅' if network_ok else '❌'}")
        print(f"   📸 Test przeglądarki: {'✅' if browser_ok else '❌'}")
        print(f"   🏆 Ogólny wynik: {'✅ SUKCES' if overall_success else '❌ NIEPOWODZENIE'}")
        
        results.append({
            'case_name': case_name,
            'url': url,
            'network_ok': network_ok,
            'browser_ok': browser_ok,
            'overall_success': overall_success
        })
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"🏆 KOŃCOWE PODSUMOWANIE WSZYSTKICH PRZYPADKÓW")
    print(f"{'='*80}")
    
    for i, result in enumerate(results, 1):
        status = "✅" if result['overall_success'] else "❌"
        print(f"{i}. {result['case_name']}: {status}")
        print(f"   📍 URL: {result['url']}")
        print(f"   🌐 Sieć: {'✅' if result['network_ok'] else '❌'}")
        print(f"   📸 Przeglądarka: {'✅' if result['browser_ok'] else '❌'}")
    
    # Statistics
    total_success = sum(1 for r in results if r['overall_success'])
    network_success = sum(1 for r in results if r['network_ok'])  
    browser_success = sum(1 for r in results if r['browser_ok'])
    
    print(f"\n📊 STATYSTYKI KOŃCOWE:")
    print(f"   🎯 Pełny sukces: {total_success}/{len(results)} ({(total_success/len(results)*100):.1f}%)")
    print(f"   🌐 Wykrywanie sieciowe: {network_success}/{len(results)} ({(network_success/len(results)*100):.1f}%)")
    print(f"   📸 Testy przeglądarki: {browser_success}/{len(results)} ({(browser_success/len(results)*100):.1f}%)")
    print(f"   🖥️  System sprawny: {'✅' if system_ok else '❌'}")
    
    print(f"\n⏰ Zakończono: {datetime.now().strftime('%H:%M:%S')}")
    
    if total_success == len(results):
        print(f"\n🎉 🎉 🎉 WSZYSTKIE PRZYPADKI ZAKOŃCZONE SUKCESEM! 🎉 🎉 🎉")
    elif total_success > 0:
        print(f"\n⚠️  CZĘŚCIOWY SUKCES - {total_success}/{len(results)} przypadków działa")
    else:
        print(f"\n❌ BRAK SUKCESÓW - sprawdź konfigurację DynaDock")
    
    return total_success == len(results)

if __name__ == "__main__":
    print("🚀 Uruchamianie szczegółowych testów DynaDock...")
    try:
        success = asyncio.run(main())
        print(f"\n✅ Test zakończony {'sukcesem' if success else 'z błędami'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test przerwany przez użytkownika")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Błąd krytyczny: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
