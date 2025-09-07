#!/usr/bin/env python3
"""
Prosty test sieciowy dla 3 przypadków z verbose logging
"""

import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def main():
    print("🔍 PROSTY TEST SIECIOWY 3 PRZYPADKÓW")
    print("=" * 50)
    print(f"🕒 Start: {datetime.now().strftime('%H:%M:%S')}")
    
    # Import network analyzer
    try:
        from src.dynadock.testing.network_analyzer import analyze_network_connectivity
        print("✅ Import network_analyzer - OK")
    except Exception as e:
        print(f"❌ Import network_analyzer failed: {e}")
        return False
    
    # Test cases
    test_cases = [
        ('http://localhost:8000', 'Localhost HTTP'),
        ('https://frontend.local.dev', 'Frontend HTTPS'),  
        ('https://mailhog.local.dev', 'MailHog HTTPS')
    ]
    
    results = []
    
    for i, (url, name) in enumerate(test_cases, 1):
        print(f"\n🚀 PRZYPADEK {i}: {name}")
        print(f"📍 URL: {url}")
        print("-" * 40)
        
        try:
            # Run network analysis with verbose logging
            result = analyze_network_connectivity(url, verbose=True)
            
            # Check results
            dns_ok = result.get('dns_resolution', {}).get('success', False)
            tcp_ok = result.get('tcp_connect', False)
            
            print(f"\n📊 WYNIKI:")
            print(f"   DNS: {'✅' if dns_ok else '❌'}")
            print(f"   TCP: {'✅' if tcp_ok else '❌'}")
            
            # Show logs if available
            logs = result.get('logs', [])
            if logs:
                print(f"   Logi ({len(logs)}):")
                for log in logs[:5]:  # Show first 5 logs
                    print(f"     • {log}")
            
            network_detected = dns_ok or tcp_ok
            status = "✅ WYKRYTO" if network_detected else "❌ BRAK"
            print(f"   Status: {status}")
            
            results.append({
                'name': name,
                'url': url,
                'success': network_detected,
                'dns': dns_ok,
                'tcp': tcp_ok
            })
            
        except Exception as e:
            print(f"   ❌ Błąd testu: {e}")
            results.append({
                'name': name,
                'url': url, 
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 PODSUMOWANIE")
    print(f"{'='*50}")
    
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"{i}. {result['name']}: {status}")
        if 'error' not in result:
            print(f"   DNS: {'✅' if result['dns'] else '❌'}")
            print(f"   TCP: {'✅' if result['tcp'] else '❌'}")
    
    success_count = sum(1 for r in results if r['success'])
    print(f"\n🎯 Wynik: {success_count}/{len(results)} przypadków działa")
    print(f"⏰ Koniec: {datetime.now().strftime('%H:%M:%S')}")
    
    return success_count > 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
